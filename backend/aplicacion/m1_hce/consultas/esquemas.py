"""Esquemas de datos para consultas medicas e historia clinica (HU02 y HU03)."""
from datetime import date, datetime

from pydantic import BaseModel, Field


class SolicitudRegistrarConsulta(BaseModel):
    """Datos de entrada para registrar una atencion medica (HU02)."""

    id_paciente: int = Field(..., gt=0, description="Identificador del paciente atendido")
    diagnostico_cie10: str | None = Field(
        default=None,
        max_length=100,
        description="Codigo o clasificacion diagnostica CIE-10",
    )
    observaciones: str | None = Field(
        default=None,
        description="Observaciones y notas clinicas de la atencion",
    )
    id_cita: int | None = Field(
        default=None,
        gt=0,
        description="Identificador de la cita agendada, si la atencion proviene de una",
    )


class RespuestaConsulta(BaseModel):
    """Datos de salida de una consulta medica registrada (HU02)."""

    id_consulta: int
    id_paciente: int
    id_medico: int
    id_cita: int | None = None
    fecha_hora: datetime
    diagnostico_cie10: str | None = None
    observaciones: str | None = None
    anulada: bool = False
    motivo_anulacion: str | None = None
    fecha_anulacion: datetime | None = None
    id_usuario_anulacion: int | None = None


class PacienteHistoria(BaseModel):
    """Resumen de filiacion del paciente en la historia clinica."""

    id_paciente: int
    dni: str
    nombres: str
    apellidos: str
    fecha_nacimiento: date
    sexo: str | None = None
    telefono: str | None = None
    correo: str | None = None
    direccion: str | None = None


class RecetaItemHistoria(BaseModel):
    """Detalle de una receta prescrita en la atencion medica."""

    id_receta: int
    medicamento: str
    dosis: str
    frecuencia: str
    duracion: str | None = None
    indicaciones: str | None = None
    fecha_registro: datetime


class IndicacionItemHistoria(BaseModel):
    """Indicacion o recomendacion medica emitida en la atencion."""

    id_indicacion: int
    descripcion: str
    fecha_registro: datetime


class ConsultaItemHistoria(BaseModel):
    """Evento clinico individual dentro de la historia clinica unificada (HU03)."""

    id_consulta: int
    id_paciente: int
    id_medico: int
    medico_nombre_completo: str
    medico_colegiatura: str
    medico_especialidad: str | None = None
    id_cita: int | None = None
    fecha_hora: datetime
    diagnostico_cie10: str | None = None
    observaciones: str | None = None
    anulada: bool = False
    motivo_anulacion: str | None = None
    fecha_anulacion: datetime | None = None
    id_usuario_anulacion: int | None = None
    recetas: list[RecetaItemHistoria] = []
    indicaciones: list[IndicacionItemHistoria] = []


class RespuestaHistoriaClinica(BaseModel):
    """Historia clinica electronica unificada y cronologica de un paciente (HU03)."""

    paciente: PacienteHistoria
    total_consultas: int
    consultas: list[ConsultaItemHistoria]
