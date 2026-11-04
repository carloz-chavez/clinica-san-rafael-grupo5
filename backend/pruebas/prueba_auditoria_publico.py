"""Contratos C3 """
import ast
from datetime import date
from pathlib import Path

import pytest
from psycopg.errors import ForeignKeyViolation

from aplicacion.m1_hce import publico
from aplicacion.nucleo.auditoria import registrar_bitacora
from aplicacion.nucleo.constantes import ACCIONES_BITACORA
from aplicacion.nucleo.errores import ErrorNegocio


@pytest.mark.parametrize("accion", ACCIONES_BITACORA)
def probar_acciones_autorizadas_y_misma_conexion(conexion_memoria, accion):
    registrar_bitacora(conexion_memoria, 1, None, accion, "HISTORIA")
    cursor = conexion_memoria.cursor.return_value.__enter__.return_value
    consulta, parametros = cursor.execute.call_args.args
    assert "INSERT INTO public.bitacora_auditoria" in consulta
    assert parametros == (1, None, accion, "HISTORIA", None, None)
    conexion_memoria.commit.assert_not_called()
    conexion_memoria.rollback.assert_not_called()
    conexion_memoria.transaction.assert_not_called()


@pytest.mark.parametrize("opciones, esperado", [
    ({"id_registro": 7}, 7), ({"id_consulta": 7}, 7),
    ({"id_registro": 7, "id_consulta": 7}, 7),
    ({"id_registro": None, "id_consulta": None}, None),
])
def probar_identificador_y_alias_compatible(conexion_memoria, opciones, esperado):
    registrar_bitacora(conexion_memoria, 1, 2, "CREACION", "CONSULTA_MEDICA", **opciones)
    cursor = conexion_memoria.cursor.return_value.__enter__.return_value
    assert cursor.execute.call_args.args[1][4] == esperado


@pytest.mark.parametrize("opciones", [
    {"accion": "CREAR"}, {"accion": ""}, {"accion": "creacion"},
    {"entidad": "diagnostico ficticio sensible"},
    {"id_registro": 0}, {"id_registro": -1}, {"id_registro": True},
    {"id_usuario": None}, {"id_paciente": "2"},
    {"id_consulta": -1}, {"id_registro": 2, "id_consulta": 3},
])
def probar_datos_invalidos_no_escriben(conexion_memoria, opciones):
    datos = dict(id_usuario=1, id_paciente=None, accion="CREACION", entidad="CONSULTA_MEDICA")
    datos.update(opciones)
    with pytest.raises(ErrorNegocio) as error:
        registrar_bitacora(conexion_memoria, **datos)
    assert error.value.codigo == "DATOS_INVALIDOS"
    assert error.value.estado_http == 422
    conexion_memoria.cursor.assert_not_called()


def probar_rechaza_autocommit(conexion_memoria):
    conexion_memoria.autocommit = True
    with pytest.raises(ErrorNegocio):
        registrar_bitacora(conexion_memoria, 1, None, "CONSULTA", "HISTORIA")
    conexion_memoria.cursor.assert_not_called()


@pytest.mark.parametrize("detalle", [
    "Diagnostico ficticio: dato clinico", "contrasena=clave-ficticia",
    "Bearer token-ficticio", "DNI ficticio 00000000", "Registro de consulta",
])
def probar_detalle_libre_nunca_llega_a_sql(conexion_memoria, detalle):
    registrar_bitacora(conexion_memoria, 1, 2, "CREACION", "CONSULTA_MEDICA", 3, detalle)
    cursor = conexion_memoria.cursor.return_value.__enter__.return_value
    consulta, parametros = cursor.execute.call_args.args
    assert detalle not in consulta
    assert parametros[-1] == "CREACION de CONSULTA_MEDICA"
    assert detalle not in parametros


def probar_no_oculta_error_sql_ni_revierte_transaccion_ajena(conexion_memoria):
    cursor = conexion_memoria.cursor.return_value.__enter__.return_value
    cursor.execute.side_effect = ForeignKeyViolation("FK ficticia")
    with pytest.raises(ForeignKeyViolation):
        registrar_bitacora(conexion_memoria, 1, None, "CONSULTA", "HISTORIA")
    conexion_memoria.rollback.assert_not_called()
    conexion_memoria.commit.assert_not_called()


def probar_contrato_publico_devuelve_modelo_y_no_persistencia(monkeypatch, conexion_memoria):
    fila = dict(id_paciente=2, dni="00000002", nombres="Paciente Ficticio",
                apellidos="Ejemplo", fecha_nacimiento=date(2000, 1, 1),
                telefono=None, correo=None)
    def buscar(conexion, identificador):
        assert conexion is conexion_memoria
        assert identificador == 2
        return fila
    monkeypatch.setattr(publico.repositorio_publico, "buscar_paciente", buscar)
    paciente = publico.obtener_paciente(conexion_memoria, 2)
    assert isinstance(paciente, publico.PacienteSalida)
    assert paciente.model_dump() == fila


def probar_paciente_inexistente_devuelve_none(monkeypatch, conexion_memoria):
    monkeypatch.setattr(publico.repositorio_publico, "buscar_paciente", lambda *_: None)
    assert publico.obtener_paciente(conexion_memoria, 2) is None


def probar_m2_solo_importa_interfaz_publica_de_m1():
    carpeta = Path(__file__).resolve().parents[1] / "aplicacion" / "m2_agenda"
    for archivo in carpeta.rglob("*.py"):
        for nodo in ast.walk(ast.parse(archivo.read_text(encoding="utf-8"))):
            if isinstance(nodo, ast.Import):
                for alias in nodo.names:
                    if alias.name.startswith("aplicacion.m1_hce"):
                        assert alias.name == "aplicacion.m1_hce.publico", archivo
            elif isinstance(nodo, ast.ImportFrom):
                modulo = nodo.module or ""
                if modulo == "aplicacion.m1_hce":
                    assert all(a.name == "publico" for a in nodo.names), archivo
                elif modulo.startswith("aplicacion.m1_hce."):
                    assert modulo == "aplicacion.m1_hce.publico", archivo
