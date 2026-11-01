"""Formato unico de errores de la API.

Toda respuesta de error tiene la forma:
    {"detalle": "mensaje legible", "codigo": "CODIGO_EN_MAYUSCULAS"}

Estados HTTP acordados: 401 sin sesion, 403 rol no autorizado, 404 no existe,
409 conflicto (por ejemplo, horario ocupado), 422 datos invalidos.
"""
from fastapi import Request
from fastapi.responses import JSONResponse


class ErrorNegocio(Exception):
    """Error esperado de una regla de negocio o de seguridad.

    Ejemplo:
        raise ErrorNegocio("HORARIO_OCUPADO", "El horario ya no esta disponible.", 409)
    """

    def __init__(self, codigo: str, mensaje: str, estado_http: int = 400):
        super().__init__(mensaje)
        self.codigo = codigo
        self.mensaje = mensaje
        self.estado_http = estado_http


async def manejador_error_negocio(solicitud: Request, error: ErrorNegocio) -> JSONResponse:
    return JSONResponse(
        status_code=error.estado_http,
        content={"detalle": error.mensaje, "codigo": error.codigo},
    )
