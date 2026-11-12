"""Carreras reales C5/C6 en una base creada exclusivamente por QA.

Requiere C3_BASE_DATOS_QA (clinica_c3_qa) y permiso CREATEDB en el servidor QA.
Las sesiones se coordinan observando pg_blocking_pids; no dependen de sleeps.
"""
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event
from time import monotonic
from uuid import uuid4

import psycopg
import pytest
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo
from psycopg.rows import dict_row

from aplicacion.m1_hce.recetas import anulacion_servicio, servicio
from aplicacion.m1_hce.recetas.anulacion_esquemas import SolicitudAnulacion
from aplicacion.m1_hce.recetas.esquemas import RegistroIndicaciones
from aplicacion.nucleo.dependencias import UsuarioActual
from aplicacion.nucleo.errores import ErrorNegocio


@pytest.fixture(scope="module")
def destino_concurrencia():
    origen = os.getenv("C3_BASE_DATOS_QA")
    if not origen:
        pytest.skip("Concurrencia requiere servidor QA explicito C3_BASE_DATOS_QA")
    assert conninfo_to_dict(origen).get("dbname") == "clinica_c3_qa"
    nombre = "clinica_c6_qa_" + uuid4().hex
    destino = make_conninfo(origen, dbname=nombre)
    with psycopg.connect(origen, autocommit=True) as administracion:
        administracion.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(nombre)))
        with psycopg.connect(destino, autocommit=True) as conexion:
            conexion.execute((Path(__file__).resolve().parents[2] / "db/01_esquema.sql").read_text(encoding="utf-8"))
            conexion.execute("""
                INSERT INTO especialidades(id_especialidad,nombre) OVERRIDING SYSTEM VALUE VALUES(980001,'QA HU10');
                INSERT INTO medicos(id_medico,nombres,apellidos,numero_colegiatura,id_especialidad)
                OVERRIDING SYSTEM VALUE VALUES(980001,'Medico','Ficticio','QA-HU10',980001);
                INSERT INTO usuarios(id_usuario,correo,contrasena_hash,rol,id_medico)
                OVERRIDING SYSTEM VALUE VALUES(980001,'hu10@example.invalid','no-login','MEDICO',980001);
                INSERT INTO pacientes(id_paciente,dni,nombres,apellidos,fecha_nacimiento)
                OVERRIDING SYSTEM VALUE VALUES(980001,'00980001','Paciente','Ficticio','2000-01-01');
            """)
        yield destino


@pytest.mark.parametrize("primera,segunda,codigo,recetas", [
    ("anular", "anular", "CONSULTA_ANULADA", 0),
    ("anular", "registrar", "CONSULTA_ANULADA", 0),
    ("registrar", "anular", None, 1),
])
def probar_serializacion_c5_c6(destino_concurrencia, primera, segunda, codigo, recetas):
    usuario = UsuarioActual(id_usuario=980001, correo="hu10@example.invalid", rol="MEDICO", id_medico=980001)
    with psycopg.connect(destino_concurrencia, autocommit=True, row_factory=dict_row) as observador:
        id_consulta = observador.execute("""INSERT INTO consultas_medicas(id_paciente,id_medico,fecha_hora,observaciones)
            VALUES(980001,980001,'2026-10-01','Original ficticio') RETURNING id_consulta""").fetchone()["id_consulta"]
        def operar(conexion, operacion):
            if operacion == "anular":
                return anulacion_servicio.anular(conexion, usuario, id_consulta,
                    SolicitudAnulacion(motivo_anulacion="Corrección ficticia concurrente"))
            return servicio.registrar(conexion, usuario, id_consulta, RegistroIndicaciones(
                recetas=[dict(medicamento="Producto ficticio", dosis="Ficticia", frecuencia="Ficticia")]))

        iniciada = Event()
        pid = []
        def competir():
            try:
                with psycopg.connect(destino_concurrencia, row_factory=dict_row) as conexion:
                    conexion.execute("SET LOCAL statement_timeout='10s'")
                    pid.append(conexion.info.backend_pid)
                    iniciada.set()
                    operar(conexion, segunda)
                return None
            except ErrorNegocio as error:
                return error.codigo

        with ThreadPoolExecutor(max_workers=1) as ejecutor:
            with psycopg.connect(destino_concurrencia, row_factory=dict_row) as conexion:
                conexion.execute("SET LOCAL statement_timeout='10s'")
                operar(conexion, primera)
                futuro = ejecutor.submit(competir)
                try:
                    assert iniciada.wait(5), "La segunda sesion no inicio"
                    limite = monotonic() + 5
                    while True:
                        bloqueadores = observador.execute("SELECT pg_blocking_pids(%s) AS pids", (pid[0],)).fetchone()["pids"]
                        if conexion.info.backend_pid in bloqueadores:
                            break
                        assert not futuro.done() and monotonic() < limite, "La segunda operacion no espero el bloqueo de C5/C6"
                        Event().wait(.02)
                finally:
                    # Liberar antes de esperar al trabajador incluso si falla la asercion.
                    conexion.commit()
            assert futuro.result(timeout=10) == codigo
        consulta = observador.execute("SELECT * FROM consultas_medicas WHERE id_consulta=%s", (id_consulta,)).fetchone()
        assert consulta["anulada"] and consulta["observaciones"] == "Original ficticio"
        assert observador.execute("SELECT count(*) AS n FROM recetas WHERE id_consulta=%s", (id_consulta,)).fetchone()["n"] == recetas
        assert observador.execute("SELECT count(*) AS n FROM bitacora_auditoria WHERE accion='ANULACION' AND id_registro=%s", (id_consulta,)).fetchone()["n"] == 1
        assert observador.execute("""SELECT count(*) AS n FROM bitacora_auditoria b JOIN recetas r ON b.id_registro=r.id_receta
            WHERE b.entidad='RECETA' AND b.accion='CREACION' AND r.id_consulta=%s""", (id_consulta,)).fetchone()["n"] == recetas
