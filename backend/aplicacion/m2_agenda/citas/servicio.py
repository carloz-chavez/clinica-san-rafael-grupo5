"""Reglas de registro y listado de citas (HU07 y HU08)."""
from datetime import date

from psycopg import Connection
from psycopg.errors import RaiseException, UniqueViolation

from aplicacion.m1_hce import publico
from aplicacion.m2_agenda.citas import repositorio
from aplicacion.m2_agenda.citas.esquemas import CitaDetalle, SolicitudCita
from aplicacion.nucleo.dependencias import UsuarioActual
from aplicacion.nucleo.errores import ErrorNegocio


def _traducir_conflicto(error: UniqueViolation) -> ErrorNegocio:
    restriccion = getattr(error.diag, "constraint_name", None)
    if restriccion == "uq_cita_paciente_fecha_hora":
        return ErrorNegocio(
            "HORARIO_OCUPADO",
            "El paciente ya tiene una cita en ese horario.",
            409,
        )
    if restriccion == "uq_cita_medico_fecha_hora":
        return ErrorNegocio(
            "HORARIO_OCUPADO",
            "El horario seleccionado acaba de ocuparse. Elige otro turno.",
            409,
        )
    return ErrorNegocio(
        "HORARIO_OCUPADO",
        "El horario seleccionado no esta disponible.",
        409,
    )


def _traducir_trigger(error: RaiseException) -> ErrorNegocio:
    mensaje = (getattr(error.diag, "message_primary", None) or "").lower()
    if "turno no esta dentro" in mensaje:
        return ErrorNegocio(
            "FUERA_DE_HORARIO",
            "El horario elegido no esta dentro de la atencion del medico.",
            422,
        )
    if "medico no existe" in mensaje:
        return ErrorNegocio("MEDICO_NO_ENCONTRADO", "Medico no encontrado o inactivo.", 404)
    if "paciente no existe" in mensaje:
        return ErrorNegocio("PACIENTE_NO_ENCONTRADO", "Paciente no encontrado o inactivo.", 404)
    return ErrorNegocio("DATOS_INVALIDOS", "No se pudo registrar la cita.", 422)


def _detalle_con_paciente(conexion: Connection, fila: dict, paciente=None) -> CitaDetalle:
    if paciente is None:
        paciente = publico.obtener_paciente(conexion, fila["id_paciente"])
    if paciente is None:
        raise ErrorNegocio("PACIENTE_NO_ENCONTRADO", "Paciente de la cita no encontrado.", 404)
    datos = dict(fila)
    datos.update(
        nombres_paciente=paciente.nombres,
        apellidos_paciente=paciente.apellidos,
    )
    return CitaDetalle.model_validate(datos)


def registrar(conexion: Connection, usuario: UsuarioActual, datos: SolicitudCita) -> CitaDetalle:
    if datos.fecha < date.today():
        raise ErrorNegocio("FECHA_INVALIDA", "La fecha de la cita no puede ser anterior a hoy.", 422)
    paciente = publico.obtener_paciente(conexion, datos.id_paciente)
    if paciente is None:
        raise ErrorNegocio("PACIENTE_NO_ENCONTRADO", "Paciente no encontrado.", 404)
    if repositorio.obtener_medico_activo(conexion, datos.id_medico) is None:
        raise ErrorNegocio("MEDICO_NO_ENCONTRADO", "Medico no encontrado o inactivo.", 404)

    try:
        # Savepoint: un conflicto de unicidad no invalida la transaccion de la solicitud.
        with conexion.transaction():
            id_cita = repositorio.registrar(conexion, datos)
    except UniqueViolation as error:
        raise _traducir_conflicto(error) from error
    except RaiseException as error:
        raise _traducir_trigger(error) from error

    detalle = repositorio.buscar_detalle(conexion, id_cita)
    if detalle is None:  # Defensa: la cita se acaba de insertar en esta transaccion.
        raise ErrorNegocio("CITA_NO_ENCONTRADA", "No se pudo recuperar la cita registrada.", 404)
    return _detalle_con_paciente(conexion, detalle, paciente)


def listar_por_fecha(conexion: Connection, fecha: date) -> list[CitaDetalle]:
    return [
        _detalle_con_paciente(conexion, fila)
        for fila in repositorio.listar_por_fecha(conexion, fecha)
    ]
