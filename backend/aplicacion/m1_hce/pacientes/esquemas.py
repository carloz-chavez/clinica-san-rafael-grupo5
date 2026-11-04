"""Contratos HU01, alineados con las restricciones de pacientes en C1."""
from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

Dni = Annotated[str, StringConstraints(min_length=8, max_length=8, pattern=r"^[0-9]{8}$")]
Nombre = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]


class DatosPaciente(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dni: Dni
    nombres: Nombre
    apellidos: Nombre
    fecha_nacimiento: date = Field(ge=date(1900, 1, 1), le=date(2100, 12, 31))
    sexo: Literal["M", "F"] | None = None
    telefono: str | None = Field(default=None, max_length=20)
    correo: str | None = Field(default=None, max_length=150, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
    direccion: str | None = Field(default=None, max_length=250)

    @field_validator("sexo", "telefono", "correo", "direccion", mode="before")
    @classmethod
    def normalizar_opcionales(cls, valor):
        return (valor.strip() or None) if isinstance(valor, str) else valor


class PacienteRespuesta(DatosPaciente):
    id_paciente: int
    fecha_registro: datetime
    activo: bool
