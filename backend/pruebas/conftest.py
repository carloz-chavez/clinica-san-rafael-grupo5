"""Configuracion de fixtures compartidos para pruebas (A5).

Permite que cualquier integrante escriba una prueba en una sola linea:

    def probar_historia_requiere_medico(cliente, headers_admision):
        res = cliente.post("/consultas", headers=headers_admision, json={...})
        assert res.status_code == 403
"""
import os
from collections.abc import Iterator
from unittest.mock import MagicMock

import psycopg
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from psycopg import Connection
from psycopg.conninfo import conninfo_to_dict
from psycopg.rows import dict_row

from aplicacion import principal
from aplicacion.m1_hce.autenticacion.servicio import crear_token_acceso
from aplicacion.nucleo.base_datos import obtener_conexion
from aplicacion.nucleo.configuracion import obtener_configuracion
from aplicacion.nucleo.constantes import ROL_ADMINISTRADOR, ROL_ADMISION, ROL_MEDICO
from aplicacion.nucleo.dependencias import UsuarioActual, obtener_usuario_actual


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


# Fixtures C3 compartidas: destino QA explicito y rollback por prueba.
@pytest.fixture
def conexion_c3():
    destino = os.getenv("C3_BASE_DATOS_QA")
    if not destino:
        pytest.skip("C3_BASE_DATOS_QA no definida; integracion solo en PostgreSQL efimero")
    assert conninfo_to_dict(destino).get("dbname") == "clinica_c3_qa", "Se requiere base QA exclusiva"
    with psycopg.connect(destino, row_factory=dict_row, connect_timeout=3) as conexion:
        try:
            conexion.execute("""
                INSERT INTO usuarios(id_usuario,correo,contrasena_hash,rol)
                OVERRIDING SYSTEM VALUE
                VALUES(970001,'c3@example.invalid','hash-ficticio-no-login','ADMINISTRADOR')
            """)
            conexion.execute("""
                INSERT INTO pacientes(id_paciente,dni,nombres,apellidos,fecha_nacimiento)
                OVERRIDING SYSTEM VALUE
                VALUES(970001,'00970001','Paciente Ficticio','Ejemplo C3','2000-01-01')
            """)
            yield conexion
        finally:
            conexion.rollback()


@pytest.fixture
def cliente_recetas(aplicacion_prueba, conexion_c3):
    conexion_c3.execute("INSERT INTO especialidades(id_especialidad,nombre) OVERRIDING SYSTEM VALUE VALUES(970101,'Especialidad Ficticia HU04')")
    conexion_c3.execute("""INSERT INTO medicos(id_medico,nombres,apellidos,numero_colegiatura,id_especialidad)
        OVERRIDING SYSTEM VALUE VALUES(970101,'Medico Ficticio','HU04','FICTICIO-HU04',970101)""")
    conexion_c3.execute("""INSERT INTO usuarios(id_usuario,correo,contrasena_hash,rol,id_medico)
        OVERRIDING SYSTEM VALUE VALUES(970002,'medico.hu04@example.invalid','hash-ficticio-no-login','MEDICO',970101)""")
    conexion_c3.execute("""INSERT INTO consultas_medicas(id_consulta,id_paciente,id_medico,fecha_hora)
        OVERRIDING SYSTEM VALUE VALUES(970201,970001,970101,'2026-10-01 09:00')""")
    def conexion_solicitud():
        with conexion_c3.transaction():
            yield conexion_c3
    aplicacion_prueba.dependency_overrides[obtener_conexion] = conexion_solicitud
    aplicacion_prueba.dependency_overrides[obtener_usuario_actual] = lambda: UsuarioActual(
        id_usuario=970002, correo="medico.hu04@example.invalid", rol="MEDICO", id_medico=970101)
    yield TestClient(aplicacion_prueba)
    aplicacion_prueba.dependency_overrides.clear()


@pytest.fixture
def lote_recetas():
    return {"recetas": [{"medicamento": "Producto ficticio (no administrar)",
                         "dosis": "Dosis ilustrativa", "frecuencia": "Frecuencia ficticia",
                         "duracion": "Duracion ilustrativa", "indicaciones": "Solo pruebas de software"}],
            "indicaciones": [{"descripcion": "Indicacion ficticia independiente"}]}
