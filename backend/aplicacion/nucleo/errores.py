"""Formato unico de errores de la API.

Toda respuesta de error tiene la forma:
    {"detalle": "mensaje legible", "codigo": "CODIGO_EN_MAYUSCULAS"}

Los errores de validacion (422) agregan la lista "campos" con el detalle por campo.

Estados HTTP acordados: 401 sin sesion, 403 rol no autorizado, 404 no existe,
409 conflicto (por ejemplo, horario ocupado), 422 datos invalidos, 503 base de datos
no disponible, 500 error interno.
"""
import logging

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as ExcepcionHTTP

registro = logging.getLogger(__name__)


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


async def manejador_validacion(solicitud: Request, error: RequestValidationError) -> JSONResponse:
    """Convierte los errores de validacion de FastAPI (422) al formato del equipo."""
    campos = []
    for detalle in error.errors():
        ubicacion = [str(parte) for parte in detalle["loc"] if parte not in ("body", "query", "path")]
        campos.append({"campo": ".".join(ubicacion), "mensaje": detalle["msg"]})
    return JSONResponse(
        status_code=422,
        content={
            "detalle": "Los datos enviados no son validos.",
            "codigo": "DATOS_INVALIDOS",
            "campos": campos,
        },
    )


CODIGOS_HTTP = {
    401: "NO_AUTENTICADO",
    403: "PROHIBIDO",
    404: "NO_ENCONTRADO",
    405: "METODO_NO_PERMITIDO",
}


async def manejador_http(solicitud: Request, error: ExcepcionHTTP) -> JSONResponse:
    """Unifica los errores HTTP generados por FastAPI (ruta inexistente, metodo no permitido)."""
    return JSONResponse(
        status_code=error.status_code,
        content={
            "detalle": str(error.detail),
            "codigo": CODIGOS_HTTP.get(error.status_code, "ERROR_HTTP"),
        },
    )


async def manejador_error_interno(solicitud: Request, error: Exception) -> JSONResponse:
    """Ultimo recurso: no expone detalles internos al cliente."""
    registro.exception("Error no controlado en %s %s", solicitud.method, solicitud.url.path)
    return JSONResponse(
        status_code=500,
        content={"detalle": "Ocurrio un error interno del servidor.", "codigo": "ERROR_INTERNO"},
    )
