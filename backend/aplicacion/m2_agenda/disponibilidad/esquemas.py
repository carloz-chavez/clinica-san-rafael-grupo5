"""Contratos de catalogos y disponibilidad de la agenda (HU06)."""
from datetime import date, time

from pydantic import BaseModel


class EspecialidadItem(BaseModel):
    id_especialidad: int
    nombre: str


class MedicoItem(BaseModel):
    id_medico: int
    nombres: str
    apellidos: str
    id_especialidad: int
    especialidad: str


class FranjaDisponibilidad(BaseModel):
    hora: time
    disponible: bool


class MedicoDisponibilidad(MedicoItem):
    franjas: list[FranjaDisponibilidad]


class RespuestaDisponibilidad(BaseModel):
    fecha: date
    medicos: list[MedicoDisponibilidad]


class RespuestaCatalogos(BaseModel):
    especialidades: list[EspecialidadItem]
    medicos: list[MedicoItem]
