"""Logica de negocio para autenticacion y generacion de tokens JWT (HU09)."""
from datetime import datetime, timedelta, timezone

import jwt
from psycopg import Connection

from aplicacion.m1_hce.autenticacion import repositorio
from aplicacion.m1_hce.autenticacion.esquemas import RespuestaLogin, SolicitudLogin, UsuarioSesion
from aplicacion.nucleo.configuracion import obtener_configuracion
from aplicacion.nucleo.errores import ErrorNegocio
from aplicacion.nucleo.seguridad import verify_password


def crear_token_acceso(datos: dict, expiracion_minutos: int | None = None) -> str:
    """Genera un token JWT firmado con el tiempo de expiracion configurado."""
    configuracion = obtener_configuracion()
    minutos = expiracion_minutos or configuracion.expiracion_token_minutos
    vencimiento = datetime.now(timezone.utc) + timedelta(minutes=minutos)

    payload = datos.copy()
    payload.update({"exp": vencimiento})
    return jwt.encode(
        payload,
        configuracion.clave_secreta_jwt,
        algorithm=configuracion.algoritmo_jwt,
    )


def iniciar_sesion(conexion: Connection, datos: SolicitudLogin) -> RespuestaLogin:
    """Valida credenciales y devuelve el token de sesion.

    Criterio INVEST HU09: si el usuario no existe o la clave no coincide,
    rechaza con 401 sin indicar cual dato es incorrecto.
    """
    usuario = repositorio.buscar_usuario_por_correo(conexion, str(datos.correo))
    if not usuario or not usuario.get("activo", True):
        raise ErrorNegocio("CREDENCIALES_INVALIDAS", "Correo o contrasena incorrectos.", 401)

    if not verify_password(datos.contrasena, usuario["contrasena_hash"]):
        raise ErrorNegocio("CREDENCIALES_INVALIDAS", "Correo o contrasena incorrectos.", 401)

    payload = {
        "sub": str(usuario["id_usuario"]),
        "id_usuario": usuario["id_usuario"],
        "correo": usuario["correo"],
        "rol": usuario["rol"],
        "id_medico": usuario.get("id_medico"),
    }
    token = crear_token_acceso(payload)
    return RespuestaLogin(
        token_acceso=token,
        usuario=UsuarioSesion(
            id_usuario=usuario["id_usuario"],
            correo=usuario["correo"],
            rol=usuario["rol"],
            id_medico=usuario.get("id_medico"),
        ),
    )
