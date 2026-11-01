"""Punto de entrada de la API.

Arranque de desarrollo (desde la carpeta backend):
    uvicorn aplicacion.principal:aplicacion --reload

Registro de enrutadores: cada historia crea su archivo enrutador.py con una variable
`enrutador = APIRouter(prefix="/ruta", tags=["Nombre"])`. Las rutas de abajo en
MODULOS_ENRUTADORES ya estan reservadas: al crearse el archivo, el enrutador se registra
solo, sin editar este archivo (evita conflictos entre integrantes).
"""
import importlib
from contextlib import asynccontextmanager

from fastapi import APIRouter, Depends, FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from psycopg import Connection
from starlette.exceptions import HTTPException as ExcepcionHTTP

from aplicacion.nucleo.base_datos import abrir_pool, cerrar_pool, obtener_conexion
from aplicacion.nucleo.configuracion import obtener_configuracion
from aplicacion.nucleo.errores import (
    ErrorNegocio,
    manejador_error_interno,
    manejador_error_negocio,
    manejador_http,
    manejador_validacion,
)

MODULOS_ENRUTADORES = [
    "aplicacion.m1_hce.autenticacion.enrutador",
    "aplicacion.m1_hce.pacientes.enrutador",
    "aplicacion.m1_hce.consultas.enrutador",
    "aplicacion.m1_hce.recetas.enrutador",
    "aplicacion.m2_agenda.disponibilidad.enrutador",
    "aplicacion.m2_agenda.citas.enrutador",
]

enrutador_salud = APIRouter(tags=["Salud"])


@enrutador_salud.get("/salud")
def verificar_salud():
    return {"estado": "ok"}


@enrutador_salud.get("/salud/base-datos")
def verificar_base_datos(conexion: Connection = Depends(obtener_conexion)):
    conexion.execute("SELECT 1").fetchone()
    return {"base_datos": "ok"}


def registrar_enrutadores(instancia: FastAPI) -> None:
    """Registra los enrutadores que ya existan; ignora los que aun no se han creado."""
    for ruta_modulo in MODULOS_ENRUTADORES:
        try:
            modulo = importlib.import_module(ruta_modulo)
        except ModuleNotFoundError as error:
            if error.name == ruta_modulo:
                continue  # el archivo aun no existe
            raise
        instancia.include_router(modulo.enrutador)


@asynccontextmanager
async def ciclo_de_vida(instancia: FastAPI):
    abrir_pool()
    yield
    cerrar_pool()


def crear_aplicacion() -> FastAPI:
    configuracion = obtener_configuracion()
    instancia = FastAPI(
        title="Sistema de Gestion Clinica San Rafael",
        version="0.1.0",
        lifespan=ciclo_de_vida,
    )
    instancia.add_middleware(
        CORSMiddleware,
        allow_origins=configuracion.lista_origenes_permitidos,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    instancia.add_exception_handler(ErrorNegocio, manejador_error_negocio)
    instancia.add_exception_handler(RequestValidationError, manejador_validacion)
    instancia.add_exception_handler(ExcepcionHTTP, manejador_http)
    instancia.add_exception_handler(Exception, manejador_error_interno)
    instancia.include_router(enrutador_salud)
    registrar_enrutadores(instancia)
    return instancia


aplicacion = crear_aplicacion()
