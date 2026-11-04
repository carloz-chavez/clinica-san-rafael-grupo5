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
