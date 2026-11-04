"""Pruebas del nucleo: configuracion, errores unificados, CORS, seguridad y registro de enrutadores."""
import sys
import types

import pytest
from fastapi import APIRouter, Depends
from fastapi.testclient import TestClient
from pydantic import BaseModel

from aplicacion import principal
from aplicacion.nucleo.configuracion import obtener_configuracion
from aplicacion.nucleo.constantes import ROL_MEDICO
from aplicacion.nucleo.dependencias import UsuarioActual, requerir_roles
from aplicacion.nucleo.errores import ErrorNegocio


class DatosPrueba(BaseModel):
    dni: str


def crear_cliente(**opciones) -> TestClient:
    """Crea una aplicacion nueva con rutas de apoyo solo para estas pruebas."""
    instancia = principal.crear_aplicacion()
    enrutador = APIRouter()

    @enrutador.get("/_conflicto")
    def _conflicto():
        raise ErrorNegocio("HORARIO_OCUPADO", "El horario ya no esta disponible.", 409)

    @enrutador.post("/_validar")
    def _validar(datos: DatosPrueba):
        return datos

    @enrutador.get("/_falla")
    def _falla():
        raise RuntimeError("detalle interno que no debe filtrarse")

    @enrutador.get("/_solo_medico")
    def _solo_medico(usuario: UsuarioActual = Depends(requerir_roles(ROL_MEDICO))):
        return {"rol": usuario.rol}

    instancia.include_router(enrutador)
    return TestClient(instancia, **opciones)


@pytest.fixture(autouse=True)
def limpiar_configuracion():
    obtener_configuracion.cache_clear()
    yield
    obtener_configuracion.cache_clear()


def probar_salud():
    assert crear_cliente().get("/salud").json() == {"estado": "ok"}


def probar_base_datos_no_disponible_sin_pool():
    respuesta = crear_cliente().get("/salud/base-datos")
    assert respuesta.status_code == 503
    assert respuesta.json()["codigo"] == "BASE_DATOS_NO_DISPONIBLE"


def probar_configuracion_valores_por_defecto(monkeypatch):
    monkeypatch.delenv("AUTENTICACION_SIMULADA", raising=False)
    configuracion = obtener_configuracion()
    assert configuracion.autenticacion_simulada is False
    assert configuracion.lista_origenes_permitidos == ["http://localhost:5173"]


def probar_configuracion_varios_origenes(monkeypatch):
    monkeypatch.setenv("ORIGENES_PERMITIDOS", "http://a.test, http://b.test")
    assert obtener_configuracion().lista_origenes_permitidos == ["http://a.test", "http://b.test"]


def probar_error_negocio_usa_formato_del_equipo():
    respuesta = crear_cliente().get("/_conflicto")
    assert respuesta.status_code == 409
    assert respuesta.json() == {"detalle": "El horario ya no esta disponible.", "codigo": "HORARIO_OCUPADO"}


def probar_error_422_usa_formato_del_equipo():
    respuesta = crear_cliente().post("/_validar", json={})
    cuerpo = respuesta.json()
    assert respuesta.status_code == 422
    assert cuerpo["codigo"] == "DATOS_INVALIDOS"
    assert cuerpo["campos"][0]["campo"] == "dni"


def probar_ruta_inexistente_usa_formato_del_equipo():
    respuesta = crear_cliente().get("/no-existe")
    assert respuesta.status_code == 404
    assert respuesta.json()["codigo"] == "NO_ENCONTRADO"


def probar_error_interno_no_filtra_detalles():
    respuesta = crear_cliente(raise_server_exceptions=False).get("/_falla")
    assert respuesta.status_code == 500
    assert respuesta.json()["codigo"] == "ERROR_INTERNO"
    assert "detalle interno" not in respuesta.text


def probar_cors_permite_el_origen_del_frontend():
    respuesta = crear_cliente().get("/salud", headers={"Origin": "http://localhost:5173"})
    assert respuesta.headers["access-control-allow-origin"] == "http://localhost:5173"


def probar_autenticacion_simulada_medico_accede(monkeypatch):
    monkeypatch.setenv("AUTENTICACION_SIMULADA", "true")
    monkeypatch.setenv("ROL_SIMULADO", "MEDICO")
    assert crear_cliente().get("/_solo_medico").status_code == 200


def probar_autenticacion_simulada_admision_recibe_403(monkeypatch):
    monkeypatch.setenv("AUTENTICACION_SIMULADA", "true")
    monkeypatch.setenv("ROL_SIMULADO", "ADMISION")
    respuesta = crear_cliente().get("/_solo_medico")
    assert respuesta.status_code == 403
    assert respuesta.json()["codigo"] == "ROL_NO_AUTORIZADO"


def probar_sin_autenticacion_simulada_devuelve_401(monkeypatch):
    monkeypatch.setenv("AUTENTICACION_SIMULADA", "false")
    respuesta = crear_cliente().get("/_solo_medico")
    assert respuesta.status_code == 401


def probar_registro_ignora_enrutadores_inexistentes():
    # Ningun enrutador.py existe todavia: la aplicacion debe arrancar igual
    assert crear_cliente().get("/salud").status_code == 200


def probar_registro_incluye_enrutadores_existentes(monkeypatch):
    nombre = "aplicacion.m1_hce.pacientes.enrutador"
    modulo = types.ModuleType(nombre)
    modulo.enrutador = APIRouter(prefix="/pacientes")

    @modulo.enrutador.get("/_ping")
    def _ping():
        return {"ok": True}

    monkeypatch.setitem(sys.modules, nombre, modulo)
    assert crear_cliente().get("/pacientes/_ping").json() == {"ok": True}
