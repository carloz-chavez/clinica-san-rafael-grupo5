"""Seguridad y dependencias de autenticacion (HU09).

Uso en rutas protegidas:

    from fastapi import Depends
    from aplicacion.nucleo.constantes import ROL_MEDICO
    from aplicacion.nucleo.dependencias import UsuarioActual, requerir_roles

    @enrutador.post("/consultas")
    def registrar_consulta(usuario: UsuarioActual = Depends(requerir_roles(ROL_MEDICO))):
        ...
"""
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt
from pydantic import BaseModel

from aplicacion.nucleo.configuracion import obtener_configuracion
from aplicacion.nucleo.constantes import ROLES_VALIDOS
from aplicacion.nucleo.errores import ErrorNegocio

_esquema_token = HTTPBearer(auto_error=False)


class UsuarioActual(BaseModel):
    id_usuario: int
    correo: str
    rol: str
    id_medico: int | None = None


def obtener_usuario_actual(
    credenciales: HTTPAuthorizationCredentials | None = Depends(_esquema_token),
) -> UsuarioActual:
    """Valida el token Bearer JWT del encabezado Authorization y devuelve el usuario autenticado.

    Si no se envia token y AUTENTICACION_SIMULADA=true esta activo, entrega el usuario
    simulado de desarrollo.
    """
    configuracion = obtener_configuracion()

    if credenciales is None:
        if configuracion.autenticacion_simulada:
            return UsuarioActual(
                id_usuario=1,
                correo="simulado@sanrafael.test",
                rol=configuracion.rol_simulado.upper(),
            )
        raise ErrorNegocio("NO_AUTENTICADO", "Se requiere iniciar sesion.", 401)

    token = credenciales.credentials
    try:
        payload = jwt.decode(
            token,
            configuracion.clave_secreta_jwt,
            algorithms=[configuracion.algoritmo_jwt],
        )
    except jwt.ExpiredSignatureError:
        raise ErrorNegocio("TOKEN_EXPIRADO", "La sesion ha expirado.", 401)
    except jwt.PyJWTError:
        raise ErrorNegocio("TOKEN_INVALIDO", "Token de sesion no valido.", 401)

    id_usuario = payload.get("id_usuario")
    correo = payload.get("correo")
    rol = payload.get("rol")

    if not id_usuario or not correo or not rol or rol not in ROLES_VALIDOS:
        raise ErrorNegocio("TOKEN_INVALIDO", "El token no contiene informacion valida de usuario.", 401)

    return UsuarioActual(
        id_usuario=int(id_usuario),
        correo=str(correo),
        rol=str(rol),
        id_medico=payload.get("id_medico"),
    )


def requerir_roles(*roles_permitidos: str):
    """Exige que el usuario tenga uno de los roles autorizados.

    Devuelve 403 (ROL_NO_AUTORIZADO) si no cuenta con el rol requerido (RNF02).
    """
    for rol in roles_permitidos:
        if rol not in ROLES_VALIDOS:
            raise ValueError(f"Rol desconocido: {rol}")

    def verificar(usuario: UsuarioActual = Depends(obtener_usuario_actual)) -> UsuarioActual:
        if usuario.rol not in roles_permitidos:
            raise ErrorNegocio(
                "ROL_NO_AUTORIZADO",
                "No tiene permiso para realizar esta accion.",
                403,
            )
        return usuario

    return verificar
