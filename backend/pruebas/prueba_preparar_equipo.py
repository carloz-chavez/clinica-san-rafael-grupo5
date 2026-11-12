"""Instalacion compartida C2 en bases nuevas de un servidor QA exclusivo."""
import json
import os
from types import SimpleNamespace
from uuid import uuid4

import psycopg
import pytest
from fastapi.testclient import TestClient
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo
from psycopg.rows import dict_row

from administracion import preparar_equipo as equipo
from aplicacion import principal
from aplicacion.nucleo.configuracion import RAIZ_PROYECTO, obtener_configuracion
from aplicacion.nucleo.seguridad import hash_password, verify_password


@pytest.fixture
def conexion_equipo():
    origen = os.getenv("EQUIPO_BASE_DATOS_QA")
    if not origen:
        pytest.skip("Requiere EQUIPO_BASE_DATOS_QA en un servidor aislado")
    assert conninfo_to_dict(origen).get("dbname") == "clinica_equipo_qa"
    nombre = "clinica_equipo_" + uuid4().hex
    with psycopg.connect(origen, autocommit=True) as admin:
        admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(nombre)))
    destino = make_conninfo(origen, dbname=nombre)
    with psycopg.connect(destino, autocommit=True, row_factory=dict_row) as conexion:
        for archivo in ("01_esquema.sql", "02_permisos.sql"):
            texto = (RAIZ_PROYECTO / "db" / archivo).read_text(encoding="utf-8")
            conexion.execute("\n".join(linea for linea in texto.splitlines() if not linea.startswith("\\")), prepare=False)
        yield conexion, destino
    # El servidor QA temporal conserva estas bases hasta que termina el ejecutor.


def fotografiar(conexion):
    return {t: conexion.execute(sql.SQL("SELECT row_to_json(t)::text AS fila FROM public.{} t ORDER BY 1").format(
        sql.Identifier(t))).fetchall() for t in equipo.TABLAS}


def probar_primera_instalacion_repeticion_y_login_real(conexion_equipo, monkeypatch):
    conexion, destino = conexion_equipo
    claves = equipo.cargar_claves()
    assert equipo.inspeccionar(conexion, claves) == "vacia"
    assert equipo.preparar(conexion, claves)["cambios"]
    filas = conexion.execute("SELECT * FROM usuarios ORDER BY id_usuario").fetchall()
    assert len(filas) == 7 and all(f["activo"] for f in filas)
    assert len({f["contrasena_hash"] for f in filas}) == 7
    assert {f["id_medico"] for f in filas if f["rol"] == "MEDICO"} == set(range(800001, 800006))
    for fila, cuenta in zip(filas, equipo.CUENTAS, strict=True):
        assert fila["contrasena_hash"].startswith("$argon2id$")
        assert verify_password(claves[cuenta[4]], fila["contrasena_hash"])
    antes = fotografiar(conexion)
    assert equipo.preparar(conexion, claves) == {"estado": "configurada", "cambios": False, "cuentas_activas": 7}
    assert fotografiar(conexion) == antes
    conteos = {t: len(f) for t, f in antes.items()}
    assert conteos == dict(especialidades=4, medicos=5, usuarios=7, pacientes=8,
                          horarios_medicos=25, citas=10, consultas_medicas=6,
                          recetas=6, indicaciones_medicas=6, bitacora_auditoria=8)
    monkeypatch.setenv("BASE_DATOS_URL", destino)
    monkeypatch.setenv("AUTENTICACION_SIMULADA", "false")
    obtener_configuracion.cache_clear()
    with TestClient(principal.crear_aplicacion()) as http:
        for identificador, correo, rol, medico, variable in equipo.CUENTAS:
            respuesta = http.post("/auth/login", json={"correo": correo, "contrasena": claves[variable]})
            assert respuesta.status_code == 200
            assert respuesta.json()["usuario"] == dict(id_usuario=identificador, correo=correo, rol=rol, id_medico=medico)
    assert fotografiar(conexion) == antes


def probar_cuatro_cuentas_exigen_respaldo_y_confirmacion(conexion_equipo):
    conexion, _ = conexion_equipo
    claves = equipo.cargar_claves()
    with conexion.transaction():
        equipo.cargar_seed(conexion)
    assert equipo.inspeccionar(conexion, claves) == "cuatro_cuentas"
    antes = fotografiar(conexion)
    for opciones in ({}, {"restablecer": True}, {"respaldo_verificado": True}):
        with pytest.raises(equipo.ErrorPreparacion):
            equipo.preparar(conexion, claves, **opciones)
        assert fotografiar(conexion) == antes
    equipo.preparar(conexion, claves, restablecer=True, respaldo_verificado=True)
    despues = fotografiar(conexion)
    assert {t: f for t, f in antes.items() if t != "usuarios"} == {t: f for t, f in despues.items() if t != "usuarios"}
    assert equipo.inspeccionar(conexion, claves) == "configurada"


def probar_siete_cuentas_distintas_no_se_restauran_sin_permiso(conexion_equipo):
    conexion, _ = conexion_equipo
    claves = equipo.cargar_claves()
    equipo.preparar(conexion, claves)
    conexion.execute("UPDATE usuarios SET contrasena_hash=%s WHERE id_usuario=800001", (hash_password("otra-clave-qa"),))
    assert equipo.inspeccionar(conexion, claves) == "requiere_restablecer"
    antes = fotografiar(conexion)
    with pytest.raises(equipo.ErrorPreparacion):
        equipo.preparar(conexion, claves)
    assert fotografiar(conexion) == antes
    equipo.preparar(conexion, claves, restablecer=True, respaldo_verificado=True)
    assert equipo.inspeccionar(conexion, claves) == "configurada"


def probar_sin_usuarios_no_significa_vacia(conexion_equipo):
    conexion, _ = conexion_equipo
    conexion.execute("INSERT INTO pacientes(dni,nombres,apellidos,fecha_nacimiento) VALUES('00998877','Paciente','QA','2000-01-01')")
    antes = fotografiar(conexion)
    with pytest.raises(equipo.ErrorPreparacion):
        equipo.preparar(conexion, equipo.cargar_claves())
    assert fotografiar(conexion) == antes


def probar_fallo_final_revierte_semilla_y_cuentas(conexion_equipo, monkeypatch):
    conexion, _ = conexion_equipo
    original = equipo.configurar
    def fallar_despues(*args):
        original(*args)
        raise RuntimeError("Fallo controlado QA")
    monkeypatch.setattr(equipo, "configurar", fallar_despues)
    with pytest.raises(RuntimeError):
        equipo.preparar(conexion, equipo.cargar_claves())
    assert equipo.inspeccionar(conexion, equipo.cargar_claves()) == "vacia"
    monkeypatch.setattr(equipo, "configurar", original)
    assert equipo.preparar(conexion, equipo.cargar_claves())["cambios"]


@pytest.mark.parametrize("url,entorno", [
    ("postgresql://test@remoto.invalid:5433/clinica_san_rafael", "local"),
    ("postgresql://test@localhost:5432/clinica_san_rafael", "local"),
    ("postgresql://test@localhost:5433/otra", "local"),
    ("postgresql://test@localhost:5433/clinica_san_rafael", "produccion"),
])
def probar_destinos_rechazados(url, entorno):
    with pytest.raises(equipo.ErrorPreparacion):
        equipo.validar_destino(SimpleNamespace(base_datos_url=url, entorno=entorno))


def probar_claves_ficticias_fuera_del_contexto_de_produccion():
    assert "db/desarrollo/" in (RAIZ_PROYECTO / ".dockerignore").read_text()
    assert not (RAIZ_PROYECTO / "backend/db/desarrollo").exists()
    assert "/db/desarrollo/cuentas_ficticias.json" in (RAIZ_PROYECTO / ".gitignore").read_text()
    plantilla = json.loads((RAIZ_PROYECTO / "db/desarrollo/cuentas_ficticias.example.json").read_text())
    assert len(plantilla["claves"]) == 7 and not any(plantilla["claves"].values())
