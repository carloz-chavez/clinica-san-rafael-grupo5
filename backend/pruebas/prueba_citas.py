"""HU06-HU08: disponibilidad, registro de citas y conflicto de horario."""
from datetime import date, datetime, time, timedelta

from fastapi.testclient import TestClient
from pydantic import ValidationError
import pytest

from aplicacion.m2_agenda.citas.esquemas import SolicitudCita
from aplicacion.m2_agenda.disponibilidad import servicio as disponibilidad
from aplicacion.nucleo.base_datos import obtener_conexion
from aplicacion.nucleo.dependencias import obtener_usuario_actual, UsuarioActual

FECHA = date.today() + timedelta(days=14)
DIA_SEMANA = FECHA.isoweekday()


# ---------------------------------------------------------------------------
# Pruebas unitarias: no requieren PostgreSQL
# ---------------------------------------------------------------------------

def probar_generar_franjas_de_30_minutos():
    assert disponibilidad.generar_franjas(time(8, 0), time(10, 0)) == [
        time(8, 0), time(8, 30), time(9, 0), time(9, 30),
    ]
    assert disponibilidad.generar_franjas(time(8, 0), time(8, 30)) == [time(8, 0)]
    assert disponibilidad.generar_franjas(time(8, 0), time(9, 15)) == [time(8, 0), time(8, 30)]


def probar_franjas_marcan_ocupadas_y_pasadas():
    horarios = [{"hora_inicio": time(8, 0), "hora_fin": time(10, 0)}]
    ahora = datetime.combine(FECHA, time(7, 0))
    franjas = disponibilidad.construir_franjas(horarios, {time(9, 0)}, FECHA, ahora)
    assert [franja.hora for franja in franjas] == [time(8, 0), time(8, 30), time(9, 0), time(9, 30)]
    assert [franja.disponible for franja in franjas] == [True, True, False, True]

    ahora = datetime.combine(FECHA, time(9, 15))
    franjas = disponibilidad.construir_franjas(horarios, set(), FECHA, ahora)
    assert [franja.disponible for franja in franjas] == [False, False, False, True]


def probar_franjas_de_una_fecha_pasada_no_estan_disponibles():
    franjas = disponibilidad.construir_franjas(
        [{"hora_inicio": time(8, 0), "hora_fin": time(9, 0)}],
        set(),
        FECHA,
        datetime.combine(FECHA + timedelta(days=1), time(8, 0)),
    )
    assert all(not franja.disponible for franja in franjas)


@pytest.mark.parametrize("hora", ["09:15", "09:00:30", "09:00:00.500"])
def probar_solicitud_rechaza_horas_fuera_de_bloque(hora):
    with pytest.raises(ValidationError):
        SolicitudCita(id_paciente=1, id_medico=1, fecha=FECHA, hora=hora, motivo="Motivo ficticio")


def probar_solicitud_rechaza_campos_extra_y_motivo_vacio():
    with pytest.raises(ValidationError):
        SolicitudCita(id_paciente=1, id_medico=1, fecha=FECHA, hora="09:00", motivo=" ", estado="x")


# ---------------------------------------------------------------------------
# Pruebas de integracion sobre la base QA de C3 (se omiten sin C3_BASE_DATOS_QA)
# ---------------------------------------------------------------------------

@pytest.fixture
def cliente_citas(aplicacion_prueba, conexion_c3):
    conexion_c3.execute(
        "INSERT INTO especialidades(id_especialidad,nombre) OVERRIDING SYSTEM VALUE "
        "VALUES(970301,'Especialidad agenda ficticia')"
    )
    conexion_c3.execute(
        """INSERT INTO medicos(id_medico,nombres,apellidos,numero_colegiatura,id_especialidad)
           OVERRIDING SYSTEM VALUE VALUES
           (970301,'Medico','Agenda Uno','FICTICIO-AGENDA-1',970301),
           (970302,'Medico','Agenda Dos','FICTICIO-AGENDA-2',970301)"""
    )
    conexion_c3.execute(
        """INSERT INTO horarios_medicos(id_horario,id_medico,dia_semana,hora_inicio,hora_fin)
           OVERRIDING SYSTEM VALUE VALUES
           (970301,970301,%s,'08:00','12:00'),
           (970302,970302,%s,'08:00','12:00')""",
        (DIA_SEMANA, DIA_SEMANA),
    )

    def conexion_solicitud():
        with conexion_c3.transaction():
            yield conexion_c3

    aplicacion_prueba.dependency_overrides[obtener_conexion] = conexion_solicitud
    aplicacion_prueba.dependency_overrides[obtener_usuario_actual] = lambda: UsuarioActual(
        id_usuario=970001, correo="admision.c2@sanrafael.invalid", rol="ADMISION")
    yield TestClient(aplicacion_prueba)
    aplicacion_prueba.dependency_overrides.clear()


def _datos_cita(**cambios):
    datos = {
        "id_paciente": 970001,
        "id_medico": 970301,
        "fecha": FECHA.isoformat(),
        "hora": "09:00",
        "motivo": "Motivo ficticio de prueba",
    }
    datos.update(cambios)
    return datos


def probar_catalogos_y_disponibilidad(cliente_citas):
    catalogos = cliente_citas.get("/citas/catalogos")
    assert catalogos.status_code == 200, catalogos.text
    assert any(e["id_especialidad"] == 970301 for e in catalogos.json()["especialidades"])

    respuesta = cliente_citas.get(
        "/citas/disponibilidad",
        params={"fecha": FECHA.isoformat(), "id_especialidad": 970301},
    )
    assert respuesta.status_code == 200, respuesta.text
    medico = next(m for m in respuesta.json()["medicos"] if m["id_medico"] == 970301)
    franja = next(f for f in medico["franjas"] if f["hora"].startswith("09:00"))
    assert franja["disponible"] is True


def probar_registrar_cita_y_listar_del_dia(cliente_citas):
    respuesta = cliente_citas.post("/citas", json=_datos_cita())
    assert respuesta.status_code == 201, respuesta.text
    cita = respuesta.json()
    assert cita["estado"] == "registrada"
    assert cita["nombres_paciente"]

    listado = cliente_citas.get("/citas", params={"fecha": FECHA.isoformat()})
    assert listado.status_code == 200, listado.text
    assert any(fila["id_cita"] == cita["id_cita"] for fila in listado.json())


def probar_disponibilidad_marca_el_turno_registrado(cliente_citas):
    antes = cliente_citas.get("/citas/disponibilidad", params={"fecha": FECHA.isoformat()}).json()
    medico_antes = next(m for m in antes["medicos"] if m["id_medico"] == 970301)
    assert next(f for f in medico_antes["franjas"] if f["hora"].startswith("09:00"))["disponible"] is True

    assert cliente_citas.post("/citas", json=_datos_cita()).status_code == 201

    despues = cliente_citas.get("/citas/disponibilidad", params={"fecha": FECHA.isoformat()}).json()
    medico_despues = next(m for m in despues["medicos"] if m["id_medico"] == 970301)
    assert next(f for f in medico_despues["franjas"] if f["hora"].startswith("09:00"))["disponible"] is False


def probar_horario_ocupado_por_el_mismo_medico(cliente_citas):
    assert cliente_citas.post("/citas", json=_datos_cita()).status_code == 201
    respuesta = cliente_citas.post("/citas", json=_datos_cita())
    assert respuesta.status_code == 409
    assert respuesta.json()["codigo"] == "HORARIO_OCUPADO"


def probar_paciente_no_puede_tener_dos_citas_a_la_misma_hora(cliente_citas):
    assert cliente_citas.post("/citas", json=_datos_cita()).status_code == 201
    respuesta = cliente_citas.post("/citas", json=_datos_cita(id_medico=970302))
    assert respuesta.status_code == 409
    assert respuesta.json()["codigo"] == "HORARIO_OCUPADO"


def probar_turno_fuera_del_horario_del_medico(cliente_citas):
    respuesta = cliente_citas.post("/citas", json=_datos_cita(hora="12:00"))
    assert respuesta.status_code == 422
    assert respuesta.json()["codigo"] == "FUERA_DE_HORARIO"


def probar_paciente_inexistente(cliente_citas):
    respuesta = cliente_citas.post("/citas", json=_datos_cita(id_paciente=999999))
    assert respuesta.status_code == 404
    assert respuesta.json()["codigo"] == "PACIENTE_NO_ENCONTRADO"


def probar_fecha_pasada(cliente_citas):
    respuesta = cliente_citas.post(
        "/citas",
        json=_datos_cita(fecha=(date.today() - timedelta(days=1)).isoformat()),
    )
    assert respuesta.status_code == 422
    assert respuesta.json()["codigo"] == "FECHA_INVALIDA"


@pytest.mark.parametrize("metodo,ruta", [("post", "/citas"), ("get", "/citas/disponibilidad")])
def probar_rol_no_autorizado(cliente_citas, aplicacion_prueba, metodo, ruta):
    aplicacion_prueba.dependency_overrides[obtener_usuario_actual] = lambda: UsuarioActual(
        id_usuario=970002, correo="medico.ficticio@example.invalid", rol="MEDICO", id_medico=970301)
    kwargs = {"json": _datos_cita()} if metodo == "post" else {"params": {"fecha": FECHA.isoformat()}}
    respuesta = getattr(cliente_citas, metodo)(ruta, **kwargs)
    assert respuesta.status_code == 403
    assert respuesta.json()["codigo"] == "ROL_NO_AUTORIZADO"
