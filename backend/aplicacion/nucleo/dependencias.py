"""CONTRATO de seguridad compartido por todos los routers.

Uso en cualquier ruta protegida:

    from fastapi import Depends
    from aplicacion.nucleo.constantes import ROL_MEDICO
    from aplicacion.nucleo.dependencias import UsuarioActual, requerir_roles

    @enrutador.post("/consultas")
    def registrar_consulta(usuario: UsuarioActual = Depends(requerir_roles(ROL_MEDICO))):
        ...

Responsable: Angel (HU09, tarea A4). Hasta entonces funciona la autenticacion
SIMULADA: se activa con AUTENTICACION_SIMULADA=true en el archivo .env.
"""
import os

from fastapi import Depends
from pydantic import BaseModel

from aplicacion.nucleo.constantes import ROLES_VALIDOS
from aplicacion.nucleo.errores import ErrorNegocio


class UsuarioActual(BaseModel):
    id_usuario: int
    correo: str
    rol: str


def obtener_usuario_actual() -> UsuarioActual:
    """Devuelve el usuario autenticado de la solicitud.

    TEMPORAL: Angel reemplaza este cuerpo en la tarea A4 para leer y validar
    el token JWT del encabezado Authorization. La firma NO debe cambiar.
    """
    if os.getenv("AUTENTICACION_SIMULADA", "false").lower() == "true":
        return UsuarioActual(
            id_usuario=1,
            correo="simulado@sanrafael.test",
            rol=os.getenv("ROL_SIMULADO", "MEDICO").upper(),
        )
    raise ErrorNegocio(
        "AUTENTICACION_NO_DISPONIBLE",
        "El inicio de sesion aun no esta implementado (HU09).",
        401,
    )


def requerir_roles(*roles_permitidos: str):
    """Crea una dependencia que exige que el usuario tenga uno de los roles dados.

    Responde 403 (ROL_NO_AUTORIZADO) si el rol no esta permitido (RNF02).
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
