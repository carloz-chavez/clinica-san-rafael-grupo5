"""Contrato HU10 independiente de los contratos de registro de HU02/HU04."""
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints


class SolicitudAnulacion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    motivo_anulacion: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]


class AnulacionRespuesta(BaseModel):
    id_consulta: int
    anulada: bool
    motivo_anulacion: str
    fecha_anulacion: datetime
    id_usuario_anulacion: int
