"""Casos de uso HU01 y auditoria atomica de cada operacion exitosa."""
from psycopg import Connection
from psycopg.errors import UniqueViolation

from aplicacion.m1_hce.pacientes import repositorio
from aplicacion.m1_hce.pacientes.esquemas import DatosPaciente, PacienteRespuesta
from aplicacion.nucleo.auditoria import registrar_bitacora
from aplicacion.nucleo.constantes import ACCION_CONSULTA, ACCION_CREACION, ACCION_MODIFICACION, ENTIDAD_HISTORIA, ROL_MEDICO
from aplicacion.nucleo.dependencias import UsuarioActual
from aplicacion.nucleo.errores import ErrorNegocio


def _auditar(conexion: Connection, usuario: UsuarioActual, paciente: dict, accion: str) -> PacienteRespuesta:
    registrar_bitacora(conexion, usuario.id_usuario, paciente["id_paciente"], accion,
                       ENTIDAD_HISTORIA, id_registro=paciente["id_paciente"])
    return PacienteRespuesta.model_validate(paciente)


def _exigir_paciente(paciente: dict | None) -> dict:
    if paciente is None:
        raise ErrorNegocio("PACIENTE_NO_ENCONTRADO", "Paciente no encontrado.", 404)
    return paciente


def _exigir_acceso(conexion: Connection, usuario: UsuarioActual, paciente: dict) -> None:
    # Politica C4 propuesta para validacion del equipo. No amplia permisos JWT.
    if usuario.rol == ROL_MEDICO and (
        usuario.id_medico is None or not repositorio.tiene_vinculo_asistencial(
            conexion, usuario.id_medico, paciente["id_paciente"])
    ):
        raise ErrorNegocio("ROL_NO_AUTORIZADO", "No tienes una relación asistencial autorizada con este paciente.", 403)


def registrar(conexion: Connection, usuario: UsuarioActual, datos: DatosPaciente) -> PacienteRespuesta:
    try:
        paciente = repositorio.registrar(conexion, datos)
    except UniqueViolation as error:
        if error.diag.constraint_name == "pacientes_dni_key":
            raise ErrorNegocio("DNI_DUPLICADO", "El DNI ya está registrado.", 409) from error
        raise
    return _auditar(conexion, usuario, paciente, ACCION_CREACION)


def actualizar(conexion: Connection, usuario: UsuarioActual, id_paciente: int, datos: DatosPaciente) -> PacienteRespuesta:
    try:
        paciente = repositorio.actualizar(conexion, id_paciente, datos)
    except UniqueViolation as error:
        if error.diag.constraint_name == "pacientes_dni_key":
            raise ErrorNegocio("DNI_DUPLICADO", "El DNI ya está registrado.", 409) from error
        raise
    return _auditar(conexion, usuario, _exigir_paciente(paciente), ACCION_MODIFICACION)


def consultar_por_id(conexion: Connection, usuario: UsuarioActual, id_paciente: int) -> PacienteRespuesta:
    paciente = _exigir_paciente(repositorio.buscar_por_id(conexion, id_paciente))
    _exigir_acceso(conexion, usuario, paciente)
    return _auditar(conexion, usuario, paciente, ACCION_CONSULTA)


def consultar_por_dni(conexion: Connection, usuario: UsuarioActual, dni: str) -> PacienteRespuesta:
    paciente = _exigir_paciente(repositorio.buscar_por_dni(conexion, dni))
    _exigir_acceso(conexion, usuario, paciente)
    return _auditar(conexion, usuario, paciente, ACCION_CONSULTA)
