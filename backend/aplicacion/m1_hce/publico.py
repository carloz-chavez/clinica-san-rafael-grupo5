"""INTERFAZ PUBLICA de M1 (Historia Clinica Electronica).

Es lo UNICO de M1 que otros modulos pueden importar. M2 (Agenda y Citas)
valida al paciente con obtener_paciente y nunca consulta la tabla pacientes
ni importa el repositorio de M1 (decision de arquitectura, ADR 4 y ADR 5).

Responsable de la implementacion: Carlos (tarea C3).
"""
from datetime import date

from pydantic import BaseModel


class PacienteSalida(BaseModel):
    id_paciente: int
    dni: str
    nombres: str
    apellidos: str
    fecha_nacimiento: date
    telefono: str | None = None
    correo: str | None = None


def obtener_paciente(conexion, id_paciente: int) -> PacienteSalida | None:
    """Devuelve el paciente o None si no existe."""
    raise NotImplementedError("Pendiente: Carlos (tarea C3)")
