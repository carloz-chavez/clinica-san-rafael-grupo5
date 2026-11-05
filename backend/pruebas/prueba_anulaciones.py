"""HU10: contratos, permisos, conservacion y rollback de auditoria."""
from datetime import datetime
from unittest.mock import patch

import pytest

from prueba_recetas import cliente_recetas, conexion_c3, lote_recetas
from aplicacion.m1_hce import publico
from aplicacion.m1_hce.recetas import anulacion_servicio as servicio
from aplicacion.m1_hce.recetas.anulacion_esquemas import SolicitudAnulacion
from aplicacion.nucleo.dependencias import UsuarioActual, obtener_usuario_actual
from aplicacion.nucleo.errores import ErrorNegocio

RUTA = "/consultas/970201/anular"
DATOS = {"motivo_anulacion": "Corrección ficticia HU10"}


def probar_anulacion_conserva_registro_y_relaciones(cliente_recetas, conexion_c3, lote_recetas):
    conexion_c3.execute("UPDATE consultas_medicas SET diagnostico_cie10='FICTICIO',observaciones='Solo QA' WHERE id_consulta=970201")
    assert cliente_recetas.post("/consultas/970201/indicaciones", json=lote_recetas).status_code == 201
    original = conexion_c3.execute("SELECT * FROM consultas_medicas WHERE id_consulta=970201").fetchone()
    recetas = conexion_c3.execute("SELECT * FROM recetas").fetchall()
    indicaciones = conexion_c3.execute("SELECT * FROM indicaciones_medicas").fetchall()
    respuesta = cliente_recetas.post(RUTA, json={"motivo_anulacion": "  Corrección ficticia HU10  "})
    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["anulada"] is True
    assert cuerpo["motivo_anulacion"] == DATOS["motivo_anulacion"]
    assert cuerpo["id_usuario_anulacion"] == 970002
    assert datetime.fromisoformat(cuerpo["fecha_anulacion"]) >= original["fecha_hora"]
    actual = conexion_c3.execute("SELECT * FROM consultas_medicas WHERE id_consulta=970201").fetchone()
    campos_anulacion = {"anulada", "motivo_anulacion", "fecha_anulacion", "id_usuario_anulacion"}
    assert {k: v for k, v in actual.items() if k not in campos_anulacion} == {k: v for k, v in original.items() if k not in campos_anulacion}
    assert conexion_c3.execute("SELECT * FROM recetas").fetchall() == recetas
    assert conexion_c3.execute("SELECT * FROM indicaciones_medicas").fetchall() == indicaciones
    eventos = conexion_c3.execute("SELECT * FROM bitacora_auditoria WHERE accion='ANULACION'").fetchall()
    assert len(eventos) == 1
    assert (eventos[0]["entidad"], eventos[0]["id_registro"], eventos[0]["id_usuario"], eventos[0]["id_paciente"]) == ("CONSULTA_MEDICA", 970201, 970002, 970001)
    assert eventos[0]["detalle"] is None
    assert cliente_recetas.post(RUTA, json={"motivo_anulacion": "Otro motivo ficticio"}).status_code == 409
    assert conexion_c3.execute("SELECT * FROM consultas_medicas WHERE id_consulta=970201").fetchone() == actual
    assert cliente_recetas.post("/consultas/970201/indicaciones", json=lote_recetas).status_code == 409
    assert conexion_c3.execute("SELECT count(*) AS n FROM bitacora_auditoria WHERE accion='ANULACION'").fetchone()["n"] == 1


@pytest.mark.parametrize("datos", [{}, {"motivo_anulacion": ""}, {"motivo_anulacion": " \t\n"},
    {"motivo_anulacion": None}, {"motivo_anulacion": "x" * 201}, {"motivo_anulacion": 3},
    {**DATOS, "id_usuario_anulacion": 970001}])
def probar_motivo_invalido_no_modifica(cliente_recetas, conexion_c3, datos):
    respuesta = cliente_recetas.post(RUTA, json=datos)
    assert respuesta.status_code == 422
    assert respuesta.json()["codigo"] == "DATOS_INVALIDOS" and respuesta.json()["campos"]
    assert not conexion_c3.execute("SELECT anulada FROM consultas_medicas WHERE id_consulta=970201").fetchone()["anulada"]
    assert conexion_c3.execute("SELECT count(*) AS n FROM bitacora_auditoria").fetchone()["n"] == 0


@pytest.mark.parametrize("rol,medico", [("ADMISION", None), ("ADMINISTRADOR", None), ("MEDICO", None), ("MEDICO", 970102)])
def probar_permiso_anulacion(cliente_recetas, aplicacion_prueba, conexion_c3, rol, medico):
    aplicacion_prueba.dependency_overrides[obtener_usuario_actual] = lambda: UsuarioActual(
        id_usuario=970002, correo="qa@example.invalid", rol=rol, id_medico=medico)
    respuesta = cliente_recetas.post(RUTA, json=DATOS)
    assert respuesta.status_code == 403
    assert respuesta.json()["codigo"] == "ROL_NO_AUTORIZADO"
    assert not conexion_c3.execute("SELECT anulada FROM consultas_medicas WHERE id_consulta=970201").fetchone()["anulada"]
    assert conexion_c3.execute("SELECT count(*) AS n FROM bitacora_auditoria").fetchone()["n"] == 0


def probar_sin_sesion(cliente_recetas, aplicacion_prueba):
    del aplicacion_prueba.dependency_overrides[obtener_usuario_actual]
    assert cliente_recetas.post(RUTA, json=DATOS).status_code == 401


def probar_anulacion_inexistente(cliente_recetas):
    respuesta = cliente_recetas.post("/consultas/999999/anular", json=DATOS)
    assert respuesta.status_code == 404
    assert respuesta.json()["codigo"] == "CONSULTA_NO_ENCONTRADA"


@pytest.mark.parametrize("identificador", ["0", "-1", "texto"])
def probar_id_invalido(cliente_recetas, identificador):
    assert cliente_recetas.post(f"/consultas/{identificador}/anular", json=DATOS).status_code == 422


def probar_fallo_auditoria_revierte_anulacion(cliente_recetas, conexion_c3, monkeypatch):
    original = conexion_c3.execute("SELECT * FROM consultas_medicas WHERE id_consulta=970201").fetchone()
    auditar = servicio.registrar_bitacora
    def fallar(*args, **kwargs):
        auditar(*args, **kwargs)
        raise RuntimeError("Fallo ficticio HU10")
    monkeypatch.setattr(servicio, "registrar_bitacora", fallar)
    with pytest.raises(RuntimeError, match="Fallo ficticio HU10"):
        cliente_recetas.post(RUTA, json=DATOS)
    assert conexion_c3.execute("SELECT * FROM consultas_medicas WHERE id_consulta=970201").fetchone() == original
    assert conexion_c3.execute("SELECT count(*) AS n FROM bitacora_auditoria").fetchone()["n"] == 0


@pytest.mark.parametrize("estado,medico,codigo", [(None, 9, "CONSULTA_NO_ENCONTRADA"),
    (False, 10, "ROL_NO_AUTORIZADO"), (True, 9, "CONSULTA_ANULADA")])
def probar_reglas_sin_escritura(conexion_memoria, estado, medico, codigo):
    usuario = UsuarioActual(id_usuario=8, correo="qa@example.invalid", rol="MEDICO", id_medico=9)
    contexto = None if estado is None else publico.ContextoConsulta(id_consulta=7, id_paciente=6, id_medico=medico, anulada=estado)
    with patch.object(publico, "obtener_contexto_consulta", return_value=contexto), patch.object(servicio.repositorio, "marcar_anulada") as escribir:
        with pytest.raises(ErrorNegocio) as error:
            servicio.anular(conexion_memoria, usuario, 7, SolicitudAnulacion(**DATOS))
        assert error.value.codigo == codigo
        escribir.assert_not_called()


@pytest.mark.parametrize("motivo", ["x", "x" * 200, "  Ejemplo ficticio  "])
def probar_limites_motivo(motivo):
    assert SolicitudAnulacion(motivo_anulacion=motivo).motivo_anulacion == motivo.strip()
