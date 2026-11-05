"""Contratos de registro y listado de citas (HU07)."""
from datetime import date, datetime, time
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

Motivo = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]


class SolicitudCita(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id_paciente: int = Field(gt=0)
    id_medico: int = Field(gt=0)
    fecha: date
    hora: time
    motivo: Motivo

    @field_validator("hora")
    @classmethod
    def validar_bloque_de_30_minutos(cls, valor: time) -> time:
        if valor.tzinfo is not None:
            raise ValueError("La hora no debe incluir zona horaria.")
        if valor.minute not in (0, 30) or valor.second or valor.microsecond:
            raise ValueError("La hora debe estar en bloques completos de 30 minutos.")
        return valor


class CitaDetalle(BaseModel):
    id_cita: int
    id_paciente: int
    nombres_paciente: str
    apellidos_paciente: str
    id_medico: int
    nombres_medico: str
    apellidos_medico: str
    especialidad: str
    fecha: date
    hora: time
    estado: str
    motivo: str
    fecha_registro: datetime
