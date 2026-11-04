"""INTERFAZ PUBLICA de M1 (Historia Clinica Electronica).

Es lo UNICO de M1 que otros modulos pueden importar. M2 (Agenda y Citas)
valida al paciente con obtener_paciente y nunca consulta la tabla pacientes
ni importa el repositorio de M1 (decision de arquitectura, ADR 4 y ADR 5).

La consulta devuelve el paciente existente, incluso inactivo, segun el contrato
original. No agrega reglas de disponibilidad ni operaciones de HU01.
"""
from datetime import date

from pydantic import BaseModel
from psycopg import Connection

from aplicacion.m1_hce import repositorio_publico
from aplicacion.nucleo.errores import ErrorNegocio


class PacienteSalida(BaseModel):
    id_paciente: int
    dni: str
    nombres: str
    apellidos: str
    fecha_nacimiento: date
    telefono: str | None = None
    correo: str | None = None


def obtener_paciente(conexion: Connection, id_paciente: int) -> PacienteSalida | None:
    """Devuelve el paciente o None si no existe."""
    fila = repositorio_publico.buscar_paciente(conexion, id_paciente)
    return PacienteSalida.model_validate(fila) if fila is not None else None


class ContextoConsulta(BaseModel):
    """Solo identidad y estado necesarios para registrar HU04, sin informacion clinica."""
    id_consulta: int
    id_paciente: int
    id_medico: int
    anulada: bool


def obtener_contexto_consulta(conexion: Connection, id_consulta: int) -> ContextoConsulta | None:
    """Ampliacion minima C3 para C5: bloquea la consulta en la misma transaccion.

    No confirma ni abre conexiones. El consumidor verifica permisos/estado antes
    de escribir y mantiene el bloqueo hasta commit/rollback de su operacion.
    """
    if conexion.autocommit is True:
        raise ErrorNegocio("DATOS_INVALIDOS", "Se requiere una conexión transaccional.", 422)
    fila = repositorio_publico.buscar_contexto_consulta(conexion, id_consulta)
    return ContextoConsulta.model_validate(fila) if fila is not None else None
