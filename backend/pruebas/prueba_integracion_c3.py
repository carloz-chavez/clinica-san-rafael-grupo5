"""Integracion C3: solo una base QA explicita, nunca la conexion de desarrollo.

Definir C3_BASE_DATOS_QA apuntando a la base efimera clinica_c3_qa inicializada
con db/01_esquema.sql y db/02_permisos.sql. Sin esa variable se omite integracion.
"""
import os
from datetime import datetime

import psycopg
from psycopg.conninfo import conninfo_to_dict
from psycopg.errors import ForeignKeyViolation, RaiseException, UniqueViolation
from psycopg.rows import dict_row
import pytest

from aplicacion.m1_hce.publico import obtener_paciente
from aplicacion.nucleo.auditoria import registrar_bitacora
from aplicacion.nucleo.constantes import ACCIONES_BITACORA
from aplicacion.nucleo.errores import ErrorNegocio


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


@pytest.mark.parametrize("accion", ACCIONES_BITACORA)
def probar_evento_real_accion_fecha_y_opcionales(conexion_c3, accion):
    registrar_bitacora(conexion_c3, 970001, None, accion, "HISTORIA")
    fila = conexion_c3.execute("SELECT * FROM bitacora_auditoria").fetchone()
    assert fila["id_usuario"] == 970001
    assert fila["accion"] == accion
    assert fila["id_paciente"] is None and fila["id_registro"] is None
    assert fila["detalle"] is None
    assert isinstance(fila["fecha_evento"], datetime)


def probar_alias_y_detalle_seguro_en_postgres(conexion_c3):
    registrar_bitacora(conexion_c3, 970001, 970001, "CREACION", "CONSULTA_MEDICA",
                       id_consulta=970002, detalle="Diagnostico ficticio y token privado")
    fila = conexion_c3.execute("SELECT * FROM bitacora_auditoria").fetchone()
    assert fila["id_registro"] == 970002
    assert fila["id_paciente"] == 970001
    assert fila["detalle"] == "CREACION de CONSULTA_MEDICA"


def probar_accion_invalida_no_dana_transaccion(conexion_c3):
    with pytest.raises(ErrorNegocio):
        registrar_bitacora(conexion_c3, 970001, None, "CREAR", "HISTORIA")
    assert conexion_c3.execute("SELECT count(*) AS total FROM bitacora_auditoria").fetchone()["total"] == 0


def probar_rollback_operacion_principal_revierte_evento(conexion_c3):
    registrar_bitacora(conexion_c3, 970001, 970001, "CREACION", "HISTORIA")
    with pytest.raises(UniqueViolation):
        conexion_c3.execute("INSERT INTO pacientes(dni,nombres,apellidos,fecha_nacimiento) VALUES('00970001','Duplicado','Ficticio','2000-01-01')")
    conexion_c3.rollback()
    assert conexion_c3.execute("SELECT count(*) AS total FROM bitacora_auditoria").fetchone()["total"] == 0
    assert conexion_c3.execute("SELECT count(*) AS total FROM pacientes WHERE id_paciente=970001").fetchone()["total"] == 0


def probar_fallo_auditoria_revierte_escritura_principal(conexion_c3):
    with pytest.raises(ForeignKeyViolation):
        registrar_bitacora(conexion_c3, 999999, 970001, "CREACION", "HISTORIA")
    conexion_c3.rollback()
    assert obtener_paciente(conexion_c3, 970001) is None


def probar_evento_no_se_confirma_independientemente(conexion_c3):
    registrar_bitacora(conexion_c3, 970001, None, "CONSULTA", "HISTORIA")
    with psycopg.connect(os.environ["C3_BASE_DATOS_QA"], row_factory=dict_row) as observador:
        assert observador.execute("SELECT count(*) AS total FROM bitacora_auditoria").fetchone()["total"] == 0
    assert conexion_c3.execute("SELECT count(*) AS total FROM bitacora_auditoria").fetchone()["total"] == 1


@pytest.mark.parametrize("sentencia", [
    "UPDATE bitacora_auditoria SET detalle='No permitido'",
    "DELETE FROM bitacora_auditoria", "TRUNCATE bitacora_auditoria",
])
def probar_inmutabilidad_del_evento(conexion_c3, sentencia):
    registrar_bitacora(conexion_c3, 970001, None, "CONSULTA", "HISTORIA")
    with pytest.raises(RaiseException):
        conexion_c3.execute(sentencia)


def probar_publico_consulta_real_sin_exponer_campos_internos(conexion_c3):
    conexion_c3.execute("UPDATE pacientes SET activo=false, direccion='Dato no publico' WHERE id_paciente=970001")
    paciente = obtener_paciente(conexion_c3, 970001)
    assert paciente.id_paciente == 970001
    assert paciente.dni == "00970001"
    assert set(paciente.model_dump()) == {"id_paciente", "dni", "nombres", "apellidos", "fecha_nacimiento", "telefono", "correo"}
    assert obtener_paciente(conexion_c3, 999999) is None


def probar_writer_inserta_sin_select_ni_returning(conexion_c3):
    conexion_c3.execute("SET LOCAL ROLE clinica_auditoria_writer")
    registrar_bitacora(conexion_c3, 970001, 970001, "CONSULTA", "HISTORIA")
    conexion_c3.execute("RESET ROLE")
    assert conexion_c3.execute("SELECT count(*) AS total FROM bitacora_auditoria").fetchone()["total"] == 1
