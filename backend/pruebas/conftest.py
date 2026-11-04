"""Configuracion de fixtures compartidos para pruebas (A5).

Permite que cualquier integrante escriba una prueba en una sola linea:

    def probar_historia_requiere_medico(cliente, headers_admision):
        res = cliente.post("/consultas", headers=headers_admision, json={...})
        assert res.status_code == 403
"""
from collections.abc import Iterator
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from psycopg import Connection
from psycopg.rows import dict_row

from aplicacion import principal
from aplicacion.m1_hce.autenticacion.servicio import crear_token_acceso
from aplicacion.nucleo.base_datos import obtener_conexion
from aplicacion.nucleo.configuracion import obtener_configuracion
from aplicacion.nucleo.constantes import ROL_ADMINISTRADOR, ROL_ADMISION, ROL_MEDICO
from aplicacion.nucleo.dependencias import UsuarioActual


@pytest.fixture(autouse=True)
def limpiar_cache_configuracion():
    """Limpia la configuracion en cache antes y despues de cada prueba."""
    obtener_configuracion.cache_clear()
    yield
    obtener_configuracion.cache_clear()


@pytest.fixture
def aplicacion_prueba() -> FastAPI:
    """Instancia de la aplicacion configurada para el entorno de pruebas."""
    return principal.crear_aplicacion()


@pytest.fixture
def cliente(aplicacion_prueba: FastAPI) -> TestClient:
    """Cliente de prueba sincronico para endpoints HTTP."""
    return TestClient(aplicacion_prueba)


# ---------------------------------------------------------------------------
# Fixtures de tokens y encabezados de autenticacion (HU09 / A4)
# ---------------------------------------------------------------------------

@pytest.fixture
def fabrica_tokens():
    """Generador de tokens JWT para cualquier rol de usuario."""
    def _crear(
        id_usuario: int = 800001,
        correo: str = "usuario.prueba@sanrafael.invalid",
        rol: str = ROL_MEDICO,
        id_medico: int | None = None,
        expiracion_minutos: int = 60,
    ) -> str:
        datos = {
            "sub": str(id_usuario),
            "id_usuario": id_usuario,
            "correo": correo,
            "rol": rol,
            "id_medico": id_medico,
        }
        return crear_token_acceso(datos, expiracion_minutos=expiracion_minutos)
    return _crear


@pytest.fixture
def token_medico(fabrica_tokens) -> str:
    return fabrica_tokens(
        id_usuario=800002,
        correo="medico1.c2@sanrafael.invalid",
        rol=ROL_MEDICO,
        id_medico=800001,
    )


@pytest.fixture
def token_admision(fabrica_tokens) -> str:
    return fabrica_tokens(
        id_usuario=800001,
        correo="admision.c2@sanrafael.invalid",
        rol=ROL_ADMISION,
        id_medico=None,
    )


@pytest.fixture
def token_admin(fabrica_tokens) -> str:
    return fabrica_tokens(
        id_usuario=800004,
        correo="admin.c2@sanrafael.invalid",
        rol=ROL_ADMINISTRADOR,
        id_medico=None,
    )


@pytest.fixture
def headers_medico(token_medico: str) -> dict[str, str]:
    """Encabezado de autorizacion para peticiones como Medico."""
    return {"Authorization": f"Bearer {token_medico}"}


@pytest.fixture
def headers_admision(token_admision: str) -> dict[str, str]:
    """Encabezado de autorizacion para peticiones como personal de Admision."""
    return {"Authorization": f"Bearer {token_admision}"}


@pytest.fixture
def headers_admin(token_admin: str) -> dict[str, str]:
    """Encabezado de autorizacion para peticiones como Administrador."""
    return {"Authorization": f"Bearer {token_admin}"}


@pytest.fixture
def usuario_medico() -> UsuarioActual:
    return UsuarioActual(
        id_usuario=800002,
        correo="medico1.c2@sanrafael.invalid",
        rol=ROL_MEDICO,
        id_medico=800001,
    )


@pytest.fixture
def usuario_admision() -> UsuarioActual:
    return UsuarioActual(
        id_usuario=800001,
        correo="admision.c2@sanrafael.invalid",
        rol=ROL_ADMISION,
        id_medico=None,
    )


# ---------------------------------------------------------------------------
# Fixture de conexion a base de datos (con rollback automatico)
# ---------------------------------------------------------------------------

@pytest.fixture
def conexion_memoria():
    """Conexion simulada para pruebas unitarias sin levantar PostgreSQL."""
    conexion = MagicMock(spec=Connection)
    cursor = MagicMock()
    conexion.cursor.return_value.__enter__.return_value = cursor
    return conexion


@pytest.fixture
def conexion_bd() -> Iterator[Connection]:
    """Entrega una conexion real a PostgreSQL revirtiendo la transaccion al finalizar.

    Garantiza que ninguna prueba contamine los datos de desarrollo ni del seed.
    Si la base de datos no esta disponible, la prueba se omite de forma limpia.
    """
    import psycopg

    configuracion = obtener_configuracion()
    try:
        conexion = psycopg.connect(
            configuracion.base_datos_url,
            row_factory=dict_row,
            autocommit=False,
            connect_timeout=2,
        )
    except psycopg.OperationalError:
        pytest.skip("Base de datos PostgreSQL (puerto 5433) no disponible para pruebas de integracion.")

    try:
        yield conexion
    finally:
        conexion.rollback()
        conexion.close()
