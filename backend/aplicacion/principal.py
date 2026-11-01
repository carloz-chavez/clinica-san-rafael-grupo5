"""Punto de entrada de la API.

Arranque de desarrollo (desde la carpeta backend):
    uvicorn aplicacion.principal:aplicacion --reload

Angel completa este archivo en la tarea A2 (configuracion, base de datos,
CORS y registro de los enrutadores de cada modulo).
"""
from fastapi import FastAPI

from aplicacion.nucleo.errores import ErrorNegocio, manejador_error_negocio

aplicacion = FastAPI(
    title="Sistema de Gestion Clinica San Rafael",
    version="0.1.0",
)

aplicacion.add_exception_handler(ErrorNegocio, manejador_error_negocio)


@aplicacion.get("/salud")
def verificar_salud():
    return {"estado": "ok"}
