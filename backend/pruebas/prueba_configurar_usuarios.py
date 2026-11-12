"""Pruebas de cuentas C2; PostgreSQL solo con destino QA explicito y aislado."""
import os
import secrets
import sys
from datetime import UTC, datetime
from unittest.mock import MagicMock

import jwt
import psycopg
import pytest
from fastapi.security import HTTPAuthorizationCredentials
from psycopg.conninfo import conninfo_to_dict
from psycopg.rows import dict_row
from pydantic import ValidationError

from administracion import configurar_usuarios as herramienta
from aplicacion.m1_hce.autenticacion import servicio
from aplicacion.m1_hce.autenticacion.esquemas import SolicitudLogin
from aplicacion.nucleo.configuracion import Configuracion, obtener_configuracion
from aplicacion.nucleo.dependencias import obtener_usuario_actual
from aplicacion.nucleo.errores import ErrorNegocio
from aplicacion.nucleo.seguridad import hash_password, verify_password


def probar_produccion_prohibe_simulacion():
    with pytest.raises(ValidationError):
        Configuracion(_env_file=None, entorno="produccion", autenticacion_simulada=True)
    assert not Configuracion(_env_file=None, entorno="produccion").autenticacion_simulada


@pytest.mark.parametrize("cuenta", herramienta.CUENTAS)
def probar_siete_logins_identidad_y_expiracion(cuenta, monkeypatch):
    identificador, correo, rol, medico, _ = cuenta
    clave = secrets.token_urlsafe(24)
    fila = dict(id_usuario=identificador, correo=correo, rol=rol, id_medico=medico,
                activo=True, contrasena_hash=hash_password(clave))
    monkeypatch.setattr(servicio.repositorio, "buscar_usuario_por_correo", lambda *_: fila)
    monkeypatch.setenv("EXPIRACION_TOKEN_MINUTOS", "17")
    inicio = datetime.now(UTC).timestamp()
    respuesta = servicio.iniciar_sesion(MagicMock(), SolicitudLogin(correo=correo, contrasena=clave))
    usuario = obtener_usuario_actual(HTTPAuthorizationCredentials(
        scheme="Bearer", credentials=respuesta.token_acceso))
    assert (usuario.id_usuario, usuario.rol, usuario.id_medico) == (identificador, rol, medico)
    config = obtener_configuracion()
    datos = jwt.decode(respuesta.token_acceso, config.clave_secreta_jwt,
                       algorithms=[config.algoritmo_jwt])
    assert datos["sub"] == str(identificador)
    assert 1018 <= datos["exp"] - inicio <= 1021


@pytest.mark.parametrize("cambio", [
    {"exp": None}, {"sub": "otro"}, {"id_usuario": "texto"},
    {"id_medico": None}, {"rol": "ADMINISTRADOR", "id_medico": 800001},
])
def probar_token_identidad_invalida(cambio):
    datos = dict(sub="800002", id_usuario=800002, correo="test@example.invalid",
                 rol="MEDICO", id_medico=800001, exp=4102444800)
    datos.update(cambio)
    if datos["exp"] is None:
        del datos["exp"]
    config = obtener_configuracion()
    token = jwt.encode(datos, config.clave_secreta_jwt, algorithm=config.algoritmo_jwt)
    with pytest.raises(ErrorNegocio) as error:
        obtener_usuario_actual(HTTPAuthorizationCredentials(scheme="Bearer", credentials=token))
    assert error.value.estado_http == 401


def probar_expiracion_cero_no_usa_defecto():
    config = obtener_configuracion()
    token = servicio.crear_token_acceso({}, expiracion_minutos=0)
    with pytest.raises(jwt.ExpiredSignatureError):
        jwt.decode(token, config.clave_secreta_jwt, algorithms=[config.algoritmo_jwt])


def probar_cli_exige_aplicacion_explicita(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["configurar_usuarios"])
    with pytest.raises(SystemExit) as error:
        herramienta.main()
    assert error.value.code == 2


def probar_cli_rechaza_destino_no_local(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["configurar_usuarios", "--aplicar-local"])
    monkeypatch.setenv("BASE_DATOS_URL", "postgresql://test@servidor.invalid:5433/clinica_san_rafael")
    with pytest.raises(SystemExit) as error:
        herramienta.main()
    assert error.value.code == 2


def probar_configuracion_transaccional_postgres(monkeypatch):
    destino = os.getenv("USUARIOS_BASE_DATOS_QA")
    if not destino:
        pytest.skip("Requiere USUARIOS_BASE_DATOS_QA en contenedor efimero con seed C2")
    assert conninfo_to_dict(destino).get("dbname") == "clinica_usuarios_qa"
    claves = {c[4]: secrets.token_urlsafe(24) for c in herramienta.CUENTAS}
    with psycopg.connect(destino, autocommit=True, row_factory=dict_row) as conexion:
        antes = herramienta.huellas(conexion)
        originales = conexion.execute("SELECT * FROM public.usuarios ORDER BY id_usuario").fetchall()
        assert len(originales) == 4
        # Fallo despues de todas las escrituras: debe restaurar hashes y quitar inserciones.
        with monkeypatch.context() as parche:
            parche.setattr(herramienta, "verify_password", lambda *_: False)
            with pytest.raises(ValueError):
                herramienta.configurar(conexion, claves)
        assert conexion.execute("SELECT * FROM public.usuarios ORDER BY id_usuario").fetchall() == originales
        primera = herramienta.configurar(conexion, claves)
        segunda = herramienta.configurar(conexion, claves)
        assert primera == segunda
        filas = conexion.execute("SELECT * FROM public.usuarios ORDER BY id_usuario").fetchall()
        assert len(filas) == 7
        assert all(f["activo"] for f in filas)
        assert len({f["correo"].lower() for f in filas}) == 7
        assert len({f["contrasena_hash"] for f in filas}) == 7
        assert {f["id_medico"] for f in filas if f["rol"] == "MEDICO"} == set(range(800001, 800006))
        for fila, cuenta in zip(filas, herramienta.CUENTAS, strict=True):
            assert fila["rol"] == cuenta[2]
            assert fila["contrasena_hash"].startswith("$argon2id$")
            assert verify_password(claves[cuenta[4]], fila["contrasena_hash"])
            respuesta = servicio.iniciar_sesion(conexion, SolicitudLogin(
                correo=cuenta[1].upper(), contrasena=claves[cuenta[4]]))
            assert respuesta.usuario.id_usuario == cuenta[0]
            with pytest.raises(ErrorNegocio):
                servicio.iniciar_sesion(conexion, SolicitudLogin(correo=cuenta[1], contrasena="incorrecta"))
        with conexion.transaction(force_rollback=True):
            conexion.execute("UPDATE public.usuarios SET activo=false WHERE id_usuario=800001")
            with pytest.raises(ErrorNegocio):
                servicio.iniciar_sesion(conexion, SolicitudLogin(
                    correo=herramienta.CUENTAS[0][1], contrasena=claves[herramienta.CUENTAS[0][4]]))
        assert herramienta.huellas(conexion) == antes
        # Conflicto previo: el procedimiento debe detenerse sin sustituir identidades.
        with conexion.transaction(force_rollback=True):
            conexion.execute("UPDATE public.usuarios SET correo='otro@example.invalid' WHERE id_usuario=800001")
            with pytest.raises(ValueError):
                herramienta.configurar(conexion, claves)
