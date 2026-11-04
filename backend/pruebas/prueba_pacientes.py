"""HU01 por HTTP y PostgreSQL real, dentro de la base efimera de C3."""
import pytest
from fastapi.testclient import TestClient

from prueba_integracion_c3 import conexion_c3  # Reutiliza el aislamiento QA existente.
from aplicacion.nucleo.base_datos import obtener_conexion
from aplicacion.nucleo.dependencias import obtener_usuario_actual, UsuarioActual
from aplicacion.m1_hce.pacientes import servicio
from aplicacion.m1_hce.publico import obtener_paciente


@pytest.fixture
def cliente_pacientes(aplicacion_prueba, conexion_c3):
    def conexion_solicitud():
        with conexion_c3.transaction():
            yield conexion_c3
    aplicacion_prueba.dependency_overrides[obtener_conexion] = conexion_solicitud
    aplicacion_prueba.dependency_overrides[obtener_usuario_actual] = lambda: UsuarioActual(
        id_usuario=970001, correo="c3@example.invalid", rol="ADMISION")
    yield TestClient(aplicacion_prueba)
    aplicacion_prueba.dependency_overrides.clear()


@pytest.fixture
def datos_paciente():
    return dict(dni="00980001", nombres="Paciente Ficticio", apellidos="Prueba HU01",
                fecha_nacimiento="2000-01-01", sexo="F", telefono="FICTICIO",
                correo="hu01@example.invalid", direccion="Direccion ficticia")


def probar_registro_consulta_y_auditoria(cliente_pacientes, conexion_c3, datos_paciente):
    respuesta = cliente_pacientes.post("/pacientes", json=datos_paciente)
    assert respuesta.status_code == 201, respuesta.text
    paciente = respuesta.json()
    identificador = paciente["id_paciente"]
    assert paciente["dni"] == datos_paciente["dni"]
    assert paciente["activo"] is True
    assert cliente_pacientes.get(f"/pacientes/{identificador}").json() == paciente
    assert cliente_pacientes.get("/pacientes", params={"dni": datos_paciente["dni"]}).json() == paciente
    eventos = conexion_c3.execute("SELECT accion,id_registro,detalle FROM bitacora_auditoria WHERE id_paciente=%s ORDER BY id_auditoria", (identificador,)).fetchall()
    assert [e["accion"] for e in eventos] == ["CREACION", "CONSULTA", "CONSULTA"]
    assert all(e["id_registro"] == identificador and e["detalle"] is None for e in eventos)
    assert obtener_paciente(conexion_c3, identificador).dni == datos_paciente["dni"]


def probar_dni_duplicado_conflicto_sin_segundo_evento(cliente_pacientes, conexion_c3, datos_paciente):
    assert cliente_pacientes.post("/pacientes", json=datos_paciente).status_code == 201
    respuesta = cliente_pacientes.post("/pacientes", json=datos_paciente)
    assert respuesta.status_code == 409
    assert respuesta.json()["codigo"] == "DNI_DUPLICADO"
    assert conexion_c3.execute("SELECT count(*) AS n FROM pacientes WHERE dni='00980001'").fetchone()["n"] == 1
    assert conexion_c3.execute("SELECT count(*) AS n FROM bitacora_auditoria").fetchone()["n"] == 1


@pytest.mark.parametrize("campo,valor", [
    ("dni", "123"), ("dni", "123456789"), ("dni", "abcdefgh"), ("dni", "１２３４５６７８"), ("dni", "12345678\n"),
    ("nombres", " "), ("apellidos", ""), ("correo", "correo-invalido"),
    ("sexo", "X"), ("fecha_nacimiento", "1899-01-01"),
    ("telefono", "x"*21), ("direccion", "x"*251),
])
def probar_datos_invalidos_422_con_campos(cliente_pacientes, datos_paciente, campo, valor):
    datos_paciente[campo] = valor
    respuesta = cliente_pacientes.post("/pacientes", json=datos_paciente)
    assert respuesta.status_code == 422
    assert respuesta.json()["codigo"] == "DATOS_INVALIDOS"
    assert any(c["campo"] == campo for c in respuesta.json()["campos"])


@pytest.mark.parametrize("campo", ["dni", "nombres", "apellidos", "fecha_nacimiento"])
def probar_campos_obligatorios(cliente_pacientes, datos_paciente, campo):
    del datos_paciente[campo]
    respuesta = cliente_pacientes.post("/pacientes", json=datos_paciente)
    assert respuesta.status_code == 422
    assert any(c["campo"] == campo for c in respuesta.json()["campos"])


def probar_actualizacion_y_auditoria(cliente_pacientes, conexion_c3, datos_paciente):
    identificador = cliente_pacientes.post("/pacientes", json=datos_paciente).json()["id_paciente"]
    datos_paciente.update(nombres="Nombre Ficticio Editado", correo=None, dni="00980002")
    respuesta = cliente_pacientes.put(f"/pacientes/{identificador}", json=datos_paciente)
    assert respuesta.status_code == 200
    assert respuesta.json()["nombres"] == datos_paciente["nombres"]
    assert respuesta.json()["correo"] is None
    assert cliente_pacientes.get("/pacientes", params={"dni": "00980001"}).status_code == 404
    assert cliente_pacientes.get("/pacientes", params={"dni": "00980002"}).status_code == 200
    acciones = conexion_c3.execute("SELECT accion FROM bitacora_auditoria WHERE id_paciente=%s ORDER BY id_auditoria", (identificador,)).fetchall()
    assert [a["accion"] for a in acciones] == ["CREACION", "MODIFICACION", "CONSULTA"]


def probar_actualizar_dni_ocupado_revierte_cambios(cliente_pacientes, conexion_c3, datos_paciente):
    identificador = cliente_pacientes.post("/pacientes", json=datos_paciente).json()["id_paciente"]
    datos_paciente.update(dni="00970001", nombres="Cambio que debe revertirse")
    respuesta = cliente_pacientes.put(f"/pacientes/{identificador}", json=datos_paciente)
    assert respuesta.status_code == 409
    assert respuesta.json()["codigo"] == "DNI_DUPLICADO"
    fila = conexion_c3.execute("SELECT dni,nombres FROM pacientes WHERE id_paciente=%s", (identificador,)).fetchone()
    assert fila == {"dni": "00980001", "nombres": "Paciente Ficticio"}


@pytest.mark.parametrize("metodo,ruta", [("get", "/pacientes/999999"), ("get", "/pacientes?dni=99999999"), ("put", "/pacientes/999999")])
def probar_paciente_inexistente(cliente_pacientes, datos_paciente, metodo, ruta):
    opciones = {"json": datos_paciente} if metodo == "put" else {}
    respuesta = getattr(cliente_pacientes, metodo)(ruta, **opciones)
    assert respuesta.status_code == 404
    assert respuesta.json()["codigo"] == "PACIENTE_NO_ENCONTRADO"


@pytest.mark.parametrize("metodo,ruta", [("post", "/pacientes"), ("put", "/pacientes/970001")])
def probar_medico_no_puede_escribir(cliente_pacientes, aplicacion_prueba, datos_paciente, metodo, ruta):
    aplicacion_prueba.dependency_overrides[obtener_usuario_actual] = lambda: UsuarioActual(id_usuario=970001, correo="c3@example.invalid", rol="MEDICO", id_medico=970001)
    respuesta = getattr(cliente_pacientes, metodo)(ruta, json=datos_paciente)
    assert respuesta.status_code == 403
    assert respuesta.json()["codigo"] == "ROL_NO_AUTORIZADO"


def probar_administrador_gestiona(cliente_pacientes, aplicacion_prueba, datos_paciente):
    aplicacion_prueba.dependency_overrides[obtener_usuario_actual] = lambda: UsuarioActual(id_usuario=970001, correo="c3@example.invalid", rol="ADMINISTRADOR")
    assert cliente_pacientes.post("/pacientes", json=datos_paciente).status_code == 201


def probar_fallo_auditoria_revierte_alta(cliente_pacientes, conexion_c3, datos_paciente, monkeypatch):
    def fallar(*args, **kwargs):
        raise RuntimeError("Fallo ficticio de auditoria")
    monkeypatch.setattr(servicio, "registrar_bitacora", fallar)
    with pytest.raises(RuntimeError):
        cliente_pacientes.post("/pacientes", json=datos_paciente)
    assert conexion_c3.execute("SELECT count(*) AS n FROM pacientes WHERE dni='00980001'").fetchone()["n"] == 0
    assert conexion_c3.execute("SELECT count(*) AS n FROM bitacora_auditoria").fetchone()["n"] == 0


@pytest.mark.parametrize("ruta", ["/pacientes/970001", "/pacientes?dni=00970001"])
@pytest.mark.parametrize("relacion,permitido", [("cita", True), ("consulta", True), ("cancelada", False), ("anulada", False), ("ninguna", False), ("otro_medico", False)])
def probar_medico_solo_consulta_pacientes_vinculados(cliente_pacientes, aplicacion_prueba, conexion_c3, ruta, relacion, permitido):
    conexion_c3.execute("INSERT INTO especialidades(id_especialidad,nombre) OVERRIDING SYSTEM VALUE VALUES(970101,'Especialidad Ficticia HU01')")
    conexion_c3.execute("INSERT INTO medicos(id_medico,nombres,apellidos,numero_colegiatura,id_especialidad) OVERRIDING SYSTEM VALUE VALUES(970101,'Medico Ficticio','HU01','FICTICIO-HU01',970101)")
    if relacion in ("cita", "cancelada", "otro_medico"):
        conexion_c3.execute("INSERT INTO horarios_medicos(id_medico,dia_semana,hora_inicio,hora_fin) VALUES(970101,extract(isodow FROM current_date+14),'08:00','12:00')")
        conexion_c3.execute("INSERT INTO citas(id_paciente,id_medico,fecha,hora,estado,motivo) VALUES(970001,970101,current_date+14,'09:00',%s,'Prueba ficticia HU01')", ("cancelada" if relacion == "cancelada" else "registrada",))
    if relacion in ("consulta", "anulada"):
        conexion_c3.execute("""INSERT INTO consultas_medicas(id_paciente,id_medico,fecha_hora,anulada,motivo_anulacion,fecha_anulacion,id_usuario_anulacion)
            VALUES(970001,970101,'2026-10-01 09:00',%s,%s,%s,%s)""",
            (relacion == "anulada", "Anulacion ficticia" if relacion == "anulada" else None,
             "2026-10-02 09:00" if relacion == "anulada" else None, 970001 if relacion == "anulada" else None))
    aplicacion_prueba.dependency_overrides[obtener_usuario_actual] = lambda: UsuarioActual(
        id_usuario=970001, correo="c3@example.invalid", rol="MEDICO", id_medico=970102 if relacion == "otro_medico" else 970101)
    respuesta = cliente_pacientes.get(ruta)
    assert respuesta.status_code == (200 if permitido else 403), respuesta.text
    eventos = conexion_c3.execute("SELECT count(*) AS n FROM bitacora_auditoria").fetchone()["n"]
    assert eventos == (1 if permitido else 0)
    if not permitido:
        assert respuesta.json()["codigo"] == "ROL_NO_AUTORIZADO"


def probar_consulta_sin_sesion_401(cliente_pacientes, aplicacion_prueba, monkeypatch):
    aplicacion_prueba.dependency_overrides.pop(obtener_usuario_actual)
    monkeypatch.setenv("AUTENTICACION_SIMULADA", "false")
    assert cliente_pacientes.get("/pacientes/970001").status_code == 401


def probar_fallo_auditoria_revierte_actualizacion(cliente_pacientes, conexion_c3, datos_paciente, monkeypatch):
    identificador = cliente_pacientes.post("/pacientes", json=datos_paciente).json()["id_paciente"]
    def fallar(*args, **kwargs):
        raise RuntimeError("Fallo ficticio de auditoria")
    monkeypatch.setattr(servicio, "registrar_bitacora", fallar)
    datos_paciente["nombres"] = "Cambio que no debe persistir"
    with pytest.raises(RuntimeError):
        cliente_pacientes.put(f"/pacientes/{identificador}", json=datos_paciente)
    assert conexion_c3.execute("SELECT nombres FROM pacientes WHERE id_paciente=%s", (identificador,)).fetchone()["nombres"] == "Paciente Ficticio"
