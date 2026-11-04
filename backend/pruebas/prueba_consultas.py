"""Pruebas unitarias de consultas medicas e historia clinica unificada (HU02 y HU03)."""
from datetime import date, datetime
from unittest.mock import MagicMock

import pytest

from aplicacion.m1_hce.consultas import servicio
from aplicacion.m1_hce.consultas.esquemas import SolicitudRegistrarConsulta
from aplicacion.nucleo.constantes import (
    ACCION_CONSULTA,
    ACCION_CREACION,
    ENTIDAD_CONSULTA_MEDICA,
    ENTIDAD_HISTORIA,
    ROL_ADMISION,
    ROL_MEDICO,
)
from aplicacion.nucleo.dependencias import UsuarioActual, requerir_roles
from aplicacion.nucleo.errores import ErrorNegocio


@pytest.fixture
def medico_autenticado() -> UsuarioActual:
    return UsuarioActual(
        id_usuario=800002,
        correo="medico1.c2@sanrafael.invalid",
        rol=ROL_MEDICO,
        id_medico=800001,
    )


@pytest.fixture
def paciente_bd() -> dict:
    return {
        "id_paciente": 800001,
        "dni": "00002001",
        "nombres": "Paciente Ficticio 1",
        "apellidos": "Ejemplo C2",
        "fecha_nacimiento": date(1989, 1, 1),
        "sexo": "M",
        "telefono": "FICTICIO-C2-1",
        "correo": "paciente1.c2@example.invalid",
        "direccion": "Direccion ficticia C2 1",
        "activo": True,
    }


def probar_registrar_consulta_exitosa_crea_registro_y_auditoria(monkeypatch, medico_autenticado, paciente_bd):
    llamadas_auditoria = []

    monkeypatch.setattr(
        "aplicacion.m1_hce.consultas.repositorio.buscar_paciente",
        lambda conexion, id_paciente: paciente_bd,
    )

    consulta_insertada = {
        "id_consulta": 900001,
        "id_paciente": 800001,
        "id_medico": 800001,
        "id_cita": None,
        "fecha_hora": datetime(2026, 10, 5, 10, 30),
        "diagnostico_cie10": "J00",
        "observaciones": "Rinofaringitis aguda, reposo.",
        "anulada": False,
        "motivo_anulacion": None,
        "fecha_anulacion": None,
        "id_usuario_anulacion": None,
    }
    monkeypatch.setattr(
        "aplicacion.m1_hce.consultas.repositorio.insertar_consulta",
        lambda *args, **kwargs: consulta_insertada,
    )
    monkeypatch.setattr(
        "aplicacion.m1_hce.consultas.servicio.registrar_bitacora",
        lambda *args, **kwargs: llamadas_auditoria.append(kwargs),
    )

    solicitud = SolicitudRegistrarConsulta(
        id_paciente=800001,
        diagnostico_cie10="J00",
        observaciones="Rinofaringitis aguda, reposo.",
    )

    resultado = servicio.registrar_consulta(
        conexion=MagicMock(),
        solicitud=solicitud,
        usuario=medico_autenticado,
    )

    assert resultado.id_consulta == 900001
    assert resultado.id_paciente == 800001
    assert resultado.id_medico == 800001
    assert resultado.diagnostico_cie10 == "J00"
    assert resultado.anulada is False

    # Verifica RNF02 y RNF04: Auditoria de creacion registrada
    assert len(llamadas_auditoria) == 1
    assert llamadas_auditoria[0]["accion"] == ACCION_CREACION
    assert llamadas_auditoria[0]["entidad"] == ENTIDAD_CONSULTA_MEDICA
    assert llamadas_auditoria[0]["id_registro"] == 900001
    assert llamadas_auditoria[0]["id_paciente"] == 800001
    assert llamadas_auditoria[0]["id_usuario"] == medico_autenticado.id_usuario


def probar_registrar_consulta_con_cita_actualiza_estado_atendida(monkeypatch, medico_autenticado, paciente_bd):
    citas_marcadas = []

    monkeypatch.setattr(
        "aplicacion.m1_hce.consultas.repositorio.buscar_paciente",
        lambda *args, **kwargs: paciente_bd,
    )
    cita_bd = {
        "id_cita": 800001,
        "id_paciente": 800001,
        "id_medico": 800001,
        "fecha": date(2026, 10, 5),
        "hora": "08:00",
        "estado": "confirmada",
        "motivo": "Control rutinario",
    }
    monkeypatch.setattr(
        "aplicacion.m1_hce.consultas.repositorio.buscar_cita",
        lambda *args, **kwargs: cita_bd,
    )
    monkeypatch.setattr(
        "aplicacion.m1_hce.consultas.repositorio.marcar_cita_atendida",
        lambda conexion, id_cita: citas_marcadas.append(id_cita),
    )
    monkeypatch.setattr(
        "aplicacion.m1_hce.consultas.repositorio.insertar_consulta",
        lambda *args, **kwargs: {
            "id_consulta": 900002,
            "id_paciente": 800001,
            "id_medico": 800001,
            "id_cita": kwargs.get("id_cita"),
            "fecha_hora": datetime.now(),
            "diagnostico_cie10": "K29",
            "observaciones": "Gastritis",
            "anulada": False,
            "motivo_anulacion": None,
            "fecha_anulacion": None,
            "id_usuario_anulacion": None,
        },
    )
    monkeypatch.setattr(
        "aplicacion.m1_hce.consultas.servicio.registrar_bitacora",
        lambda *args, **kwargs: None,
    )

    solicitud = SolicitudRegistrarConsulta(
        id_paciente=800001,
        id_cita=800001,
        diagnostico_cie10="K29",
        observaciones="Gastritis",
    )

    res = servicio.registrar_consulta(MagicMock(), solicitud, medico_autenticado)
    assert res.id_cita == 800001
    assert citas_marcadas == [800001]


def probar_registrar_consulta_cita_otro_paciente_rechaza_409(monkeypatch, medico_autenticado, paciente_bd):
    monkeypatch.setattr(
        "aplicacion.m1_hce.consultas.repositorio.buscar_paciente",
        lambda *args, **kwargs: paciente_bd,
    )
    monkeypatch.setattr(
        "aplicacion.m1_hce.consultas.repositorio.buscar_cita",
        lambda *args, **kwargs: {
            "id_cita": 800002,
            "id_paciente": 800002,  # diferente paciente
            "id_medico": 800001,
            "estado": "confirmada",
        },
    )

    solicitud = SolicitudRegistrarConsulta(id_paciente=800001, id_cita=800002)

    with pytest.raises(ErrorNegocio) as error:
        servicio.registrar_consulta(MagicMock(), solicitud, medico_autenticado)
    assert error.value.estado_http == 409
    assert error.value.codigo == "CITA_INVALIDA"


def probar_registrar_consulta_cita_otro_medico_rechaza_409(monkeypatch, medico_autenticado, paciente_bd):
    monkeypatch.setattr(
        "aplicacion.m1_hce.consultas.repositorio.buscar_paciente",
        lambda *args, **kwargs: paciente_bd,
    )
    monkeypatch.setattr(
        "aplicacion.m1_hce.consultas.repositorio.buscar_cita",
        lambda *args, **kwargs: {
            "id_cita": 800001,
            "id_paciente": 800001,
            "id_medico": 800002,  # diferente medico
            "estado": "confirmada",
        },
    )

    solicitud = SolicitudRegistrarConsulta(id_paciente=800001, id_cita=800001)

    with pytest.raises(ErrorNegocio) as error:
        servicio.registrar_consulta(MagicMock(), solicitud, medico_autenticado)
    assert error.value.estado_http == 409
    assert error.value.codigo == "CITA_INVALIDA"


def probar_registrar_consulta_cita_cancelada_rechaza_409(monkeypatch, medico_autenticado, paciente_bd):
    monkeypatch.setattr(
        "aplicacion.m1_hce.consultas.repositorio.buscar_paciente",
        lambda *args, **kwargs: paciente_bd,
    )
    monkeypatch.setattr(
        "aplicacion.m1_hce.consultas.repositorio.buscar_cita",
        lambda *args, **kwargs: {
            "id_cita": 800001,
            "id_paciente": 800001,
            "id_medico": 800001,
            "estado": "cancelada",
        },
    )

    solicitud = SolicitudRegistrarConsulta(id_paciente=800001, id_cita=800001)

    with pytest.raises(ErrorNegocio) as error:
        servicio.registrar_consulta(MagicMock(), solicitud, medico_autenticado)
    assert error.value.estado_http == 409
    assert error.value.codigo == "CITA_CANCELADA"


def probar_registrar_consulta_cita_ya_atendida_rechaza_409(monkeypatch, medico_autenticado, paciente_bd):
    monkeypatch.setattr(
        "aplicacion.m1_hce.consultas.repositorio.buscar_paciente",
        lambda *args, **kwargs: paciente_bd,
    )
    monkeypatch.setattr(
        "aplicacion.m1_hce.consultas.repositorio.buscar_cita",
        lambda *args, **kwargs: {
            "id_cita": 800001,
            "id_paciente": 800001,
            "id_medico": 800001,
            "estado": "atendida",
        },
    )

    solicitud = SolicitudRegistrarConsulta(id_paciente=800001, id_cita=800001)

    with pytest.raises(ErrorNegocio) as error:
        servicio.registrar_consulta(MagicMock(), solicitud, medico_autenticado)
    assert error.value.estado_http == 409
    assert error.value.codigo == "CITA_YA_ATENDIDA"


def probar_registrar_consulta_paciente_inexistente_rechaza_404(monkeypatch, medico_autenticado):
    monkeypatch.setattr(
        "aplicacion.m1_hce.consultas.repositorio.buscar_paciente",
        lambda *args, **kwargs: None,
    )

    solicitud = SolicitudRegistrarConsulta(id_paciente=999999)

    with pytest.raises(ErrorNegocio) as error:
        servicio.registrar_consulta(MagicMock(), solicitud, medico_autenticado)
    assert error.value.estado_http == 404
    assert error.value.codigo == "PACIENTE_NO_ENCONTRADO"


def probar_registrar_consulta_sin_medico_asociado_rechaza_403(paciente_bd):
    usuario_invalido = UsuarioActual(
        id_usuario=800009,
        correo="sinmedico@sanrafael.invalid",
        rol=ROL_MEDICO,
        id_medico=None,
    )
    solicitud = SolicitudRegistrarConsulta(id_paciente=800001)

    with pytest.raises(ErrorNegocio) as error:
        servicio.registrar_consulta(MagicMock(), solicitud, usuario_invalido)
    assert error.value.estado_http == 403
    assert error.value.codigo == "MEDICO_NO_ASOCIADO"


def probar_requerir_rol_medico_rechaza_admision_403():
    verificar = requerir_roles(ROL_MEDICO)
    usuario_admision = UsuarioActual(
        id_usuario=800001,
        correo="admision@sanrafael.invalid",
        rol=ROL_ADMISION,
        id_medico=None,
    )

    with pytest.raises(ErrorNegocio) as error:
        verificar(usuario=usuario_admision)
    assert error.value.estado_http == 403
    assert error.value.codigo == "ROL_NO_AUTORIZADO"


def probar_obtener_historia_clinica_exitosa_auditoria_y_anidadas(monkeypatch, medico_autenticado, paciente_bd):
    llamadas_auditoria = []

    monkeypatch.setattr(
        "aplicacion.m1_hce.consultas.repositorio.buscar_paciente",
        lambda *args, **kwargs: paciente_bd,
    )
    monkeypatch.setattr(
        "aplicacion.m1_hce.consultas.servicio.registrar_bitacora",
        lambda *args, **kwargs: llamadas_auditoria.append(kwargs),
    )

    consultas_bd = [
        {
            "id_consulta": 800001,
            "id_paciente": 800001,
            "id_medico": 800001,
            "id_cita": 800001,
            "fecha_hora": datetime(2026, 10, 5, 8, 30),
            "diagnostico_cie10": "J00",
            "observaciones": "Atencion 1",
            "anulada": False,
            "motivo_anulacion": None,
            "fecha_anulacion": None,
            "id_usuario_anulacion": None,
            "medico_nombre_completo": "Alba Ficticia Ejemplo Uno",
            "medico_colegiatura": "FICTICIO-C2-001",
            "medico_especialidad": "Medicina general C2",
        }
    ]
    recetas_bd = [
        {
            "id_receta": 800001,
            "id_consulta": 800001,
            "medicamento": "Paracetamol 500mg",
            "dosis": "1 tableta",
            "frecuencia": "cada 8 horas",
            "duracion": "3 dias",
            "indicaciones": "Tomar con alimentos",
            "fecha_registro": datetime(2026, 10, 5, 8, 45),
        }
    ]
    indicaciones_bd = [
        {
            "id_indicacion": 800001,
            "id_consulta": 800001,
            "descripcion": "Reposo absoluto por 48 horas",
            "fecha_registro": datetime(2026, 10, 5, 8, 45),
        }
    ]

    monkeypatch.setattr(
        "aplicacion.m1_hce.consultas.repositorio.listar_consultas_paciente",
        lambda *args, **kwargs: consultas_bd,
    )
    monkeypatch.setattr(
        "aplicacion.m1_hce.consultas.repositorio.listar_recetas_por_consultas",
        lambda *args, **kwargs: recetas_bd,
    )
    monkeypatch.setattr(
        "aplicacion.m1_hce.consultas.repositorio.listar_indicaciones_por_consultas",
        lambda *args, **kwargs: indicaciones_bd,
    )

    historia = servicio.obtener_historia_clinica(
        conexion=MagicMock(),
        id_paciente=800001,
        usuario=medico_autenticado,
    )

    assert historia.paciente.id_paciente == 800001
    assert historia.total_consultas == 1
    assert len(historia.consultas) == 1

    cons = historia.consultas[0]
    assert cons.id_consulta == 800001
    assert cons.medico_nombre_completo == "Alba Ficticia Ejemplo Uno"
    assert len(cons.recetas) == 1
    assert cons.recetas[0].medicamento == "Paracetamol 500mg"
    assert len(cons.indicaciones) == 1
    assert cons.indicaciones[0].descripcion == "Reposo absoluto por 48 horas"

    # Verifica RNF04: Auditoria de lectura de historia clinica registrada
    assert len(llamadas_auditoria) == 1
    assert llamadas_auditoria[0]["accion"] == ACCION_CONSULTA
    assert llamadas_auditoria[0]["entidad"] == ENTIDAD_HISTORIA
    assert llamadas_auditoria[0]["id_registro"] is None


def probar_obtener_historia_clinica_incluye_consulta_anulada_con_motivo(monkeypatch, medico_autenticado, paciente_bd):
    monkeypatch.setattr(
        "aplicacion.m1_hce.consultas.repositorio.buscar_paciente",
        lambda *args, **kwargs: paciente_bd,
    )
    monkeypatch.setattr(
        "aplicacion.m1_hce.consultas.servicio.registrar_bitacora",
        lambda *args, **kwargs: None,
    )

    consultas_bd = [
        {
            "id_consulta": 800006,
            "id_paciente": 800001,
            "id_medico": 800002,
            "id_cita": None,
            "fecha_hora": datetime(2026, 10, 5, 11, 0),
            "diagnostico_cie10": None,
            "observaciones": "Consulta anulada",
            "anulada": True,
            "motivo_anulacion": "Error en digitacion",
            "fecha_anulacion": datetime(2026, 10, 6, 9, 0),
            "id_usuario_anulacion": 800004,
            "medico_nombre_completo": "Bruno Ficticio Ejemplo Dos",
            "medico_colegiatura": "FICTICIO-C2-002",
            "medico_especialidad": "Pediatria C2",
        }
    ]
    monkeypatch.setattr(
        "aplicacion.m1_hce.consultas.repositorio.listar_consultas_paciente",
        lambda *args, **kwargs: consultas_bd,
    )
    monkeypatch.setattr(
        "aplicacion.m1_hce.consultas.repositorio.listar_recetas_por_consultas",
        lambda *args, **kwargs: [],
    )
    monkeypatch.setattr(
        "aplicacion.m1_hce.consultas.repositorio.listar_indicaciones_por_consultas",
        lambda *args, **kwargs: [],
    )

    historia = servicio.obtener_historia_clinica(
        conexion=MagicMock(),
        id_paciente=800001,
        usuario=medico_autenticado,
    )

    assert historia.total_consultas == 1
    anulada = historia.consultas[0]
    assert anulada.anulada is True
    assert anulada.motivo_anulacion == "Error en digitacion"
    assert anulada.id_usuario_anulacion == 800004


def probar_obtener_historia_paciente_inexistente_rechaza_404(monkeypatch, medico_autenticado):
    monkeypatch.setattr(
        "aplicacion.m1_hce.consultas.repositorio.buscar_paciente",
        lambda *args, **kwargs: None,
    )

    with pytest.raises(ErrorNegocio) as error:
        servicio.obtener_historia_clinica(MagicMock(), 999999, medico_autenticado)
    assert error.value.estado_http == 404
    assert error.value.codigo == "PACIENTE_NO_ENCONTRADO"
