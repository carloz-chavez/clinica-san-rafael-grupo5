"""Modelos de datos para el inicio de sesion (HU09)."""
from pydantic import BaseModel, Field


class SolicitudLogin(BaseModel):
    correo: str = Field(..., min_length=3, description="Correo del usuario")
    contrasena: str = Field(..., min_length=1, description="Contrasena en texto plano")


class UsuarioSesion(BaseModel):
    id_usuario: int
    correo: str
    rol: str
    id_medico: int | None = None


class RespuestaLogin(BaseModel):
    token_acceso: str
    tipo_token: str = "bearer"
    usuario: UsuarioSesion
