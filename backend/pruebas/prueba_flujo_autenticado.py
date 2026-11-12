"""Login real, pool ASGI y persistencia; exclusivamente en PostgreSQL QA explicito."""
import os
import secrets
from datetime import date, timedelta

import psycopg
import pytest
from fastapi.testclient import TestClient
from psycopg.conninfo import conninfo_to_dict
from psycopg.rows import dict_row

from administracion.configurar_usuarios import CUENTAS
from aplicacion import principal
from aplicacion.nucleo.configuracion import obtener_configuracion
from aplicacion.nucleo.seguridad import hash_password


@pytest.fixture
def flujo_real(monkeypatch):
    destino = os.getenv("FLUJO_BASE_DATOS_QA")
    if not destino:
        pytest.skip("Requiere FLUJO_BASE_DATOS_QA aislada")
    assert conninfo_to_dict(destino).get("dbname") == "clinica_flujo_qa"
    claves = {c[1]: secrets.token_urlsafe(24) for c in CUENTAS}
    fecha = date.today() + timedelta(days=14)
    with psycopg.connect(destino) as db:
        assert db.execute("SELECT count(*) FROM usuarios").fetchone()[0] == 0
        db.execute("INSERT INTO especialidades(id_especialidad,nombre) OVERRIDING SYSTEM VALUE VALUES(800001,'Ficticia C')")
        for n in range(1, 6):
            db.execute("""INSERT INTO medicos(id_medico,nombres,apellidos,numero_colegiatura,id_especialidad)
                OVERRIDING SYSTEM VALUE VALUES(%s,'Medico','Ficticio',%s,800001)""", (800000+n, f"QA-C-{n}"))
        for identificador, correo, rol, medico, _ in CUENTAS:
            db.execute("""INSERT INTO usuarios(id_usuario,correo,rol,id_medico,contrasena_hash)
                OVERRIDING SYSTEM VALUE VALUES(%s,%s,%s,%s,%s)""",
                (identificador, correo, rol, medico, hash_password(claves[correo])))
        db.execute("""INSERT INTO horarios_medicos(id_medico,dia_semana,hora_inicio,hora_fin)
            VALUES(800001,%s,'08:00','12:00')""", (fecha.isoweekday(),))
    monkeypatch.setenv("BASE_DATOS_URL", destino)
    monkeypatch.setenv("AUTENTICACION_SIMULADA", "false")
    obtener_configuracion.cache_clear()
    with TestClient(principal.crear_aplicacion()) as http:
        yield http, destino, claves, fecha


def probar_flujo_real_persistencia_identidad_roles_y_auditoria(flujo_real):
    http, destino, claves, fecha = flujo_real
    cabeceras = {}
    for identificador, correo, rol, medico, _ in CUENTAS:
        r = http.post("/auth/login", json={"correo": correo, "contrasena": claves[correo]})
        assert r.status_code == 200
        assert r.json()["usuario"] == dict(id_usuario=identificador, correo=correo, rol=rol, id_medico=medico)
        cabeceras[correo.split(".")[0]] = {"Authorization": "Bearer " + r.json()["token_acceso"]}
    admision, medico, otro, admin = [cabeceras[c] for c in ("admision", "medico1", "medico2", "admin")]
    paciente = dict(dni="00990001", nombres="Paciente", apellidos="Ficticio Etapa C", fecha_nacimiento="2000-01-01")
    assert http.post("/pacientes", json=paciente).status_code == 401
    assert http.post("/pacientes", headers=medico, json=paciente).status_code == 403
    r = http.post("/pacientes", headers=admision, json=paciente)
    assert r.status_code == 201
    identificador = r.json()["id_paciente"]
    assert http.post("/pacientes", headers=admision, json=paciente).status_code == 409
    assert http.put(f"/pacientes/{identificador}", headers=admin, json=paciente).status_code == 200
    assert http.get(f"/pacientes/{identificador}", headers=otro).status_code == 403
    cita = dict(id_paciente=identificador, id_medico=800001, fecha=fecha.isoformat(), hora="09:00", motivo="Prueba ficticia C")
    assert http.post("/citas", headers=medico, json=cita).status_code == 403
    r = http.post("/citas", headers=admision, json=cita)
    assert r.status_code == 201
    id_cita = r.json()["id_cita"]
    assert http.post("/citas", headers=admin, json=cita).status_code == 409
    for h in (admision, admin):
        assert http.get("/citas", headers=h, params={"fecha": fecha.isoformat()}).status_code == 200
        assert http.post("/consultas", headers=h, json={"id_paciente": identificador}).status_code == 403
    assert http.get("/citas", headers=medico, params={"fecha": fecha.isoformat()}).status_code == 403
    consulta = dict(id_paciente=identificador, id_cita=id_cita, observaciones="Ficticia C")
    assert http.post("/consultas", headers=otro, json=consulta).status_code == 409
    # El campo extra no controla identidad: el servicio utiliza el medico del JWT.
    r = http.post("/consultas", headers=medico, json=dict(consulta, id_medico=800002))
    assert r.status_code == 201
    assert r.json()["id_medico"] == 800001
    id_consulta = r.json()["id_consulta"]
    assert http.get(f"/pacientes/{identificador}", headers=medico).status_code == 200
    contenido = dict(recetas=[dict(medicamento="Producto ficticio", dosis="Ficticia", frecuencia="Ficticia")],
                     indicaciones=[dict(descripcion="Indicacion ficticia C")])
    for h in (admision, admin, otro):
        assert http.post(f"/consultas/{id_consulta}/indicaciones", headers=h, json=contenido).status_code == 403
        assert http.post(f"/consultas/{id_consulta}/anular", headers=h,
                         json={"motivo_anulacion": "Correccion ficticia"}).status_code == 403
    assert http.post(f"/consultas/{id_consulta}/indicaciones", headers=medico, json=contenido).status_code == 201
    for h in (admision, admin):
        assert http.get(f"/consultas/{id_consulta}", headers=h).status_code == 403
        assert http.get(f"/pacientes/{identificador}/historia", headers=h).status_code == 403
    # Caracterizacion de HU03 actual: lectura por rol, sin exigir vinculo asistencial.
    assert http.get(f"/consultas/{id_consulta}", headers=otro).status_code == 200
    assert http.get(f"/pacientes/{identificador}/historia", headers=otro).status_code == 200
    assert http.post(f"/consultas/{id_consulta}/anular", headers=medico,
                     json={"motivo_anulacion": "Correccion ficticia C"}).status_code == 200
    assert http.post(f"/consultas/{id_consulta}/indicaciones", headers=medico, json=contenido).status_code == 409
    # Cada conexion nueva observa commits de solicitudes ya finalizadas.
    with psycopg.connect(destino, row_factory=dict_row) as db:
        assert db.execute("SELECT count(*) AS n FROM pacientes WHERE dni='00990001'").fetchone()["n"] == 1
        assert db.execute("SELECT estado FROM citas WHERE id_cita=%s", (id_cita,)).fetchone()["estado"] == "atendida"
        assert db.execute("SELECT anulada FROM consultas_medicas WHERE id_consulta=%s", (id_consulta,)).fetchone()["anulada"]
        assert db.execute("SELECT count(*) AS n FROM recetas").fetchone()["n"] == 1
        assert db.execute("SELECT count(*) AS n FROM indicaciones_medicas").fetchone()["n"] == 1
        eventos = db.execute("SELECT accion,entidad,id_usuario FROM bitacora_auditoria").fetchall()
        assert any(e["accion"] == "ANULACION" and e["id_usuario"] == 800002 for e in eventos)
        assert any(e["entidad"] == "RECETA" for e in eventos)
        # El catalogo de auditoria actual no incluye CITA; comprobar entidades clinicas reales.
        assert any(e["entidad"] == "INDICACION" for e in eventos)
        assert any(e["entidad"] == "CONSULTA_MEDICA" for e in eventos)
        assert any(e["entidad"] == "HISTORIA" and e["accion"] == "CREACION" for e in eventos)
        assert not db.execute("SELECT FROM pg_constraint WHERE connamespace='public'::regnamespace AND NOT convalidated").fetchall()
    with psycopg.connect(destino) as db:
        db.execute("UPDATE usuarios SET activo=false WHERE id_usuario=800007")
    assert http.post("/auth/login", json={"correo": CUENTAS[6][1], "contrasena": claves[CUENTAS[6][1]]}).status_code == 401
