"""Contratos HU04. Recetas e indicaciones independientes conservan sus tablas C1."""
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator, model_validator

TextoObligatorio = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class DatosReceta(BaseModel):
    model_config = ConfigDict(extra="forbid")
    medicamento: TextoObligatorio = Field(max_length=150)
    dosis: TextoObligatorio = Field(max_length=100)
    frecuencia: TextoObligatorio = Field(max_length=100)
    duracion: str | None = Field(default=None, max_length=100)
    indicaciones: str | None = None

    @field_validator("duracion", "indicaciones", mode="before")
    @classmethod
    def normalizar_opcionales(cls, valor):
        return (valor.strip() or None) if isinstance(valor, str) else valor


class DatosIndicacion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    descripcion: TextoObligatorio


class RegistroIndicaciones(BaseModel):
    model_config = ConfigDict(extra="forbid")
    recetas: list[DatosReceta] = Field(default_factory=list)
    indicaciones: list[DatosIndicacion] = Field(default_factory=list)

    @model_validator(mode="after")
    def exigir_contenido(self):
        if not self.recetas and not self.indicaciones:
            raise ValueError("Incluye al menos una receta o indicación independiente.")
        return self


class RecetaRespuesta(DatosReceta):
    id_receta: int
    id_consulta: int
    fecha_registro: datetime


class IndicacionRespuesta(DatosIndicacion):
    id_indicacion: int
    id_consulta: int
    fecha_registro: datetime


class RegistroRespuesta(BaseModel):
    id_consulta: int
    recetas: list[RecetaRespuesta]
    indicaciones: list[IndicacionRespuesta]
