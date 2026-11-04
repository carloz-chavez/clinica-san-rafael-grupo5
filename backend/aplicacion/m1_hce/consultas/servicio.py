"""Logica de negocio para atenciones medicas e historia clinica (HU02 y HU03)."""
from collections import defaultdict
from datetime import datetime

from psycopg import Connection

from aplicacion.m1_hce.consultas import repositorio
from aplicacion.m1_hce.consultas.esquemas import (
    ConsultaItemHistoria,
    IndicacionItemHistoria,
    PacienteHistoria,
    RecetaItemHistoria,
    RespuestaConsulta,
    RespuestaHistoriaClinica,
    SolicitudRegistrarConsulta,
)
from aplicacion.nucleo.auditoria import registrar_bitacora
from aplicacion.nucleo.constantes import (
    ACCION_CONSULTA,
    ACCION_CREACION,
    ENTIDAD_CONSULTA_MEDICA,
    ENTIDAD_HISTORIA,
)
from aplicacion.nucleo.dependencias import UsuarioActual
from aplicacion.nucleo.errores import ErrorNegocio


def registrar_consulta(
    conexion: Connection,
    solicitud: SolicitudRegistrarConsulta,
    usuario: UsuarioActual,
) -> RespuestaConsulta:
    """Registra una nueva atencion medica realizada por el medico autenticado (HU02).

    Valida la existencia del paciente, la correspondencia de la cita si fue indicada,
    actualiza el estado de la cita a 'atendida' y registra el evento en la bitacora
    de auditoria dentro de la misma transaccion.
    """
    if not usuario.id_medico:
        raise ErrorNegocio(
            "MEDICO_NO_ASOCIADO",
            "El usuario autenticado no tiene un medico asociado.",
            403,
        )

    paciente = repositorio.buscar_paciente(conexion, solicitud.id_paciente)
    if not paciente or not paciente.get("activo", True):
        raise ErrorNegocio(
            "PACIENTE_NO_ENCONTRADO",
            "El paciente especificado no existe o no se encuentra activo.",
            404,
        )

    if solicitud.id_cita is not None:
        cita = repositorio.buscar_cita(conexion, solicitud.id_cita)
        if not cita:
            raise ErrorNegocio(
                "CITA_NO_ENCONTRADA",
                "La cita indicada no existe.",
                404,
            )

        if cita["id_paciente"] != solicitud.id_paciente:
            raise ErrorNegocio(
                "CITA_INVALIDA",
                "La cita indicada no corresponde al paciente atendido.",
                409,
            )

        if cita["id_medico"] != usuario.id_medico:
            raise ErrorNegocio(
                "CITA_INVALIDA",
                "La cita indicada no corresponde al medico autenticado.",
                409,
            )

        if cita["estado"] == "cancelada":
            raise ErrorNegocio(
                "CITA_CANCELADA",
                "No se puede registrar atencion sobre una cita cancelada.",
                409,
            )

        if cita["estado"] == "atendida":
            raise ErrorNegocio(
                "CITA_YA_ATENDIDA",
                "La cita ya cuenta con una consulta medica registrada.",
                409,
            )

        repositorio.marcar_cita_atendida(conexion, solicitud.id_cita)

    fecha_hora = datetime.now()
    fila_consulta = repositorio.insertar_consulta(
        conexion=conexion,
        id_paciente=solicitud.id_paciente,
        id_medico=usuario.id_medico,
        id_cita=solicitud.id_cita,
        fecha_hora=fecha_hora,
        diagnostico_cie10=solicitud.diagnostico_cie10,
        observaciones=solicitud.observaciones,
    )

    # RNF02 y RNF04: Registro inmutable en la bitacora dentro de la misma transaccion
    registrar_bitacora(
        conexion=conexion,
        id_usuario=usuario.id_usuario,
        id_paciente=solicitud.id_paciente,
        accion=ACCION_CREACION,
        entidad=ENTIDAD_CONSULTA_MEDICA,
        id_registro=fila_consulta["id_consulta"],
        detalle="Registro de atencion medica",
    )

    return RespuestaConsulta(**fila_consulta)


def obtener_consulta_por_id(
    conexion: Connection,
    id_consulta: int,
    usuario: UsuarioActual,
) -> RespuestaConsulta:
    """Obtiene el detalle de una consulta medica por su identificador."""
    fila = repositorio.buscar_consulta_por_id(conexion, id_consulta)
    if not fila:
        raise ErrorNegocio(
            "CONSULTA_NO_ENCONTRADA",
            "La consulta medica especificada no existe.",
            404,
        )
    return RespuestaConsulta(**fila)


def obtener_historia_clinica(
    conexion: Connection,
    id_paciente: int,
    usuario: UsuarioActual,
) -> RespuestaHistoriaClinica:
    """Obtiene la historia clinica unificada de un paciente en orden cronologico inverso (HU03).

    Registra el acceso a informacion clinica en la bitacora de auditoria (RNF04)
    e integra consultas medicas, recetas prescritas, indicaciones y consultas anuladas.
    """
    paciente = repositorio.buscar_paciente(conexion, id_paciente)
    if not paciente:
        raise ErrorNegocio(
            "PACIENTE_NO_ENCONTRADO",
            "El paciente especificado no existe.",
            404,
        )

    # RNF04: Auditoria de lectura de historia clinica (id_registro es NULL para la entidad HISTORIA)
    registrar_bitacora(
        conexion=conexion,
        id_usuario=usuario.id_usuario,
        id_paciente=id_paciente,
        accion=ACCION_CONSULTA,
        entidad=ENTIDAD_HISTORIA,
        id_registro=None,
        detalle="Consulta de historia clinica unificada",
    )

    filas_consultas = repositorio.listar_consultas_paciente(conexion, id_paciente)
    ids_consultas = [f["id_consulta"] for f in filas_consultas]

    filas_recetas = repositorio.listar_recetas_por_consultas(conexion, ids_consultas)
    filas_indicaciones = repositorio.listar_indicaciones_por_consultas(
        conexion, ids_consultas
    )

    recetas_por_consulta: dict[int, list[RecetaItemHistoria]] = defaultdict(list)
    for r in filas_recetas:
        recetas_por_consulta[r["id_consulta"]].append(RecetaItemHistoria(**r))

    indicaciones_por_consulta: dict[int, list[IndicacionItemHistoria]] = defaultdict(list)
    for ind in filas_indicaciones:
        indicaciones_por_consulta[ind["id_consulta"]].append(
            IndicacionItemHistoria(**ind)
        )

    consultas_unificadas: list[ConsultaItemHistoria] = []
    for c in filas_consultas:
        id_cons = c["id_consulta"]
        consultas_unificadas.append(
            ConsultaItemHistoria(
                **c,
                recetas=recetas_por_consulta.get(id_cons, []),
                indicaciones=indicaciones_por_consulta.get(id_cons, []),
            )
        )

    paciente_historia = PacienteHistoria(
        id_paciente=paciente["id_paciente"],
        dni=paciente["dni"],
        nombres=paciente["nombres"],
        apellidos=paciente["apellidos"],
        fecha_nacimiento=paciente["fecha_nacimiento"],
        sexo=paciente.get("sexo"),
        telefono=paciente.get("telefono"),
        correo=paciente.get("correo"),
        direccion=paciente.get("direccion"),
    )

    return RespuestaHistoriaClinica(
        paciente=paciente_historia,
        total_consultas=len(consultas_unificadas),
        consultas=consultas_unificadas,
    )
