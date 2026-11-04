"""HU04 sobre PostgreSQL efimero; reutiliza el aislamiento y convenciones C3."""
from fastapi.testclient import TestClient
import pytest

from prueba_integracion_c3 import conexion_c3
from aplicacion.nucleo.base_datos import obtener_conexion
from aplicacion.nucleo.dependencias import obtener_usuario_actual, UsuarioActual
from aplicacion.m1_hce import publico
from aplicacion.m1_hce.recetas import servicio, repositorio


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


@pytest.mark.parametrize("tipo", ["recetas", "indicaciones", "ambos"])
def probar_registrar_recetas_indicaciones_y_auditoria(cliente_recetas, conexion_c3, lote_recetas, tipo):
    if tipo != "ambos":
        lote_recetas = {tipo: lote_recetas[tipo]}
    respuesta = cliente_recetas.post("/consultas/970201/indicaciones", json=lote_recetas)
    assert respuesta.status_code == 201, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["id_consulta"] == 970201
    assert len(cuerpo["recetas"]) == len(lote_recetas.get("recetas", []))
    assert len(cuerpo["indicaciones"]) == len(lote_recetas.get("indicaciones", []))
    eventos = conexion_c3.execute("SELECT * FROM bitacora_auditoria ORDER BY id_auditoria").fetchall()
    assert len(eventos) == len(cuerpo["recetas"]) + len(cuerpo["indicaciones"])
    assert all(e["id_usuario"] == 970002 and e["id_paciente"] == 970001 and e["accion"] == "CREACION" and e["detalle"] is None for e in eventos)
    for receta in cuerpo["recetas"]:
        fila = conexion_c3.execute("SELECT * FROM recetas WHERE id_receta=%s", (receta["id_receta"],)).fetchone()
        assert fila["id_consulta"] == 970201 and fila["medicamento"] == receta["medicamento"]
        assert any(e["entidad"] == "RECETA" and e["id_registro"] == receta["id_receta"] for e in eventos)
    for indicacion in cuerpo["indicaciones"]:
        fila = conexion_c3.execute("SELECT * FROM indicaciones_medicas WHERE id_indicacion=%s", (indicacion["id_indicacion"],)).fetchone()
        assert fila["id_consulta"] == 970201 and fila["descripcion"] == indicacion["descripcion"]
        assert any(e["entidad"] == "INDICACION" and e["id_registro"] == indicacion["id_indicacion"] for e in eventos)


@pytest.mark.parametrize("datos", [
    {}, {"recetas": [], "indicaciones": []},
    {"recetas": [{"medicamento": "Ficticio"}]},
    {"recetas": [{"medicamento": " ", "dosis": "Ficticia", "frecuencia": "Ficticia"}]},
    {"recetas": [{"medicamento": "Ficticio", "dosis": " ", "frecuencia": "Ficticia"}]},
    {"recetas": [{"medicamento": "Ficticio", "dosis": "Ficticia", "frecuencia": ""}]},
    {"recetas": [{"medicamento": "x"*151, "dosis": "Ficticia", "frecuencia": "Ficticia"}]},
    {"indicaciones": [{"descripcion": " "}]}, {"indicaciones": [{}]},
    {"indicaciones": [{"descripcion": "Ficticia", "id_consulta": 999999}]},
])
def probar_datos_invalidos_no_insertan(cliente_recetas, conexion_c3, datos):
    respuesta = cliente_recetas.post("/consultas/970201/indicaciones", json=datos)
    assert respuesta.status_code == 422
    assert respuesta.json()["codigo"] == "DATOS_INVALIDOS"
    assert "campos" in respuesta.json()
    assert conexion_c3.execute("SELECT count(*) AS n FROM recetas").fetchone()["n"] == 0
    assert conexion_c3.execute("SELECT count(*) AS n FROM indicaciones_medicas").fetchone()["n"] == 0


def probar_consulta_inexistente(cliente_recetas, lote_recetas):
    respuesta = cliente_recetas.post("/consultas/999999/indicaciones", json=lote_recetas)
    assert respuesta.status_code == 404
    assert respuesta.json()["codigo"] == "CONSULTA_NO_ENCONTRADA"


def probar_consulta_anulada(cliente_recetas, conexion_c3, lote_recetas):
    conexion_c3.execute("UPDATE consultas_medicas SET anulada=true,motivo_anulacion='Prueba ficticia',fecha_anulacion='2026-10-02 09:00',id_usuario_anulacion=970001 WHERE id_consulta=970201")
    respuesta = cliente_recetas.post("/consultas/970201/indicaciones", json=lote_recetas)
    assert respuesta.status_code == 409
    assert respuesta.json()["codigo"] == "CONSULTA_ANULADA"
    assert conexion_c3.execute("SELECT count(*) AS n FROM bitacora_auditoria").fetchone()["n"] == 0


@pytest.mark.parametrize("rol,medico", [("ADMISION", None), ("ADMINISTRADOR", None), ("MEDICO", None), ("MEDICO", 970102)])
def probar_usuario_no_autorizado(cliente_recetas, aplicacion_prueba, conexion_c3, lote_recetas, rol, medico):
    aplicacion_prueba.dependency_overrides[obtener_usuario_actual] = lambda: UsuarioActual(
        id_usuario=970002, correo="medico.hu04@example.invalid", rol=rol, id_medico=medico)
    respuesta = cliente_recetas.post("/consultas/970201/indicaciones", json=lote_recetas)
    assert respuesta.status_code == 403
    assert respuesta.json()["codigo"] == "ROL_NO_AUTORIZADO"
    assert conexion_c3.execute("SELECT count(*) AS n FROM recetas").fetchone()["n"] == 0


def probar_registro_no_sobrescribe_historial(cliente_recetas, conexion_c3, lote_recetas):
    primera = cliente_recetas.post("/consultas/970201/indicaciones", json=lote_recetas).json()
    lote_recetas["recetas"][0]["medicamento"] = "Otro producto ficticio"
    segunda = cliente_recetas.post("/consultas/970201/indicaciones", json=lote_recetas)
    assert segunda.status_code == 201
    fila = conexion_c3.execute("SELECT medicamento FROM recetas WHERE id_receta=%s", (primera["recetas"][0]["id_receta"],)).fetchone()
    assert fila["medicamento"] == "Producto ficticio (no administrar)"
    assert conexion_c3.execute("SELECT count(*) AS n FROM recetas").fetchone()["n"] == 2


def probar_contexto_publico_minimo_con_misma_conexion(conexion_memoria):
    cursor = conexion_memoria.cursor.return_value.__enter__.return_value
    cursor.fetchone.return_value = dict(id_consulta=7, id_paciente=8, id_medico=9, anulada=False)
    contexto = publico.obtener_contexto_consulta(conexion_memoria, 7)
    assert contexto.model_dump() == dict(id_consulta=7, id_paciente=8, id_medico=9, anulada=False)
    consulta, parametros = cursor.execute.call_args.args
    assert "FOR UPDATE" in consulta and parametros == (7,)
    assert "diagnostico" not in consulta and "observaciones" not in consulta
    conexion_memoria.commit.assert_not_called()
    conexion_memoria.rollback.assert_not_called()


def probar_contexto_publico_inexistente(conexion_memoria):
    conexion_memoria.cursor.return_value.__enter__.return_value.fetchone.return_value = None
    assert publico.obtener_contexto_consulta(conexion_memoria, 999999) is None


def probar_contexto_publico_rechaza_autocommit(conexion_memoria):
    from aplicacion.nucleo.errores import ErrorNegocio
    conexion_memoria.autocommit = True
    with pytest.raises(ErrorNegocio):
        publico.obtener_contexto_consulta(conexion_memoria, 7)
    conexion_memoria.cursor.assert_not_called()


def probar_fallo_de_segundo_registro_revierte_lote(cliente_recetas, conexion_c3, lote_recetas, monkeypatch):
    def fallar(*args, **kwargs):
        raise RuntimeError("Fallo ficticio de persistencia")
    monkeypatch.setattr(repositorio, "registrar_indicacion", fallar)
    with pytest.raises(RuntimeError):
        cliente_recetas.post("/consultas/970201/indicaciones", json=lote_recetas)
    assert conexion_c3.execute("SELECT count(*) AS n FROM recetas").fetchone()["n"] == 0
    assert conexion_c3.execute("SELECT count(*) AS n FROM indicaciones_medicas").fetchone()["n"] == 0
    assert conexion_c3.execute("SELECT count(*) AS n FROM bitacora_auditoria").fetchone()["n"] == 0


def probar_fallo_de_segunda_auditoria_revierte_todo(cliente_recetas, conexion_c3, lote_recetas, monkeypatch):
    original = servicio.registrar_bitacora
    llamadas = 0
    def auditar(*args, **kwargs):
        nonlocal llamadas
        llamadas += 1
        if llamadas == 2:
            raise RuntimeError("Fallo ficticio de auditoria")
        return original(*args, **kwargs)
    monkeypatch.setattr(servicio, "registrar_bitacora", auditar)
    with pytest.raises(RuntimeError):
        cliente_recetas.post("/consultas/970201/indicaciones", json=lote_recetas)
    assert llamadas == 2
    assert conexion_c3.execute("SELECT count(*) AS n FROM recetas").fetchone()["n"] == 0
    assert conexion_c3.execute("SELECT count(*) AS n FROM indicaciones_medicas").fetchone()["n"] == 0
    assert conexion_c3.execute("SELECT count(*) AS n FROM bitacora_auditoria").fetchone()["n"] == 0


def probar_lote_multiple_asociado_a_una_consulta(cliente_recetas, conexion_c3, lote_recetas):
    lote_recetas["recetas"] *= 2
    lote_recetas["indicaciones"] *= 2
    respuesta = cliente_recetas.post("/consultas/970201/indicaciones", json=lote_recetas)
    assert respuesta.status_code == 201
    assert len(respuesta.json()["recetas"]) == len(respuesta.json()["indicaciones"]) == 2
    assert conexion_c3.execute("SELECT count(*) AS n FROM bitacora_auditoria").fetchone()["n"] == 4
