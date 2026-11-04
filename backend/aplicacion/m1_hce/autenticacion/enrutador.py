"""Rutas HTTP para autenticacion (HU09)."""
from fastapi import APIRouter, Depends
from psycopg import Connection

from aplicacion.m1_hce.autenticacion import servicio
from aplicacion.m1_hce.autenticacion.esquemas import RespuestaLogin, SolicitudLogin
from aplicacion.nucleo.base_datos import obtener_conexion

enrutador = APIRouter(prefix="/auth", tags=["Autenticacion"])


@enrutador.post("/login", response_model=RespuestaLogin)
def iniciar_sesion(
    solicitud: SolicitudLogin,
    conexion: Connection = Depends(obtener_conexion),
):
    """Inicia sesion con correo y contrasena, entregando el token de acceso JWT."""
    return servicio.iniciar_sesion(conexion, solicitud)
