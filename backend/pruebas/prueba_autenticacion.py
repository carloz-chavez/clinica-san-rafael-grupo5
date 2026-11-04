"""Pruebas unitarias de autenticacion, tokens JWT y control de acceso (HU09 / A4)."""
from unittest.mock import MagicMock

from fastapi.security import HTTPAuthorizationCredentials
import pytest

from aplicacion.m1_hce.autenticacion.esquemas import SolicitudLogin
from aplicacion.m1_hce.autenticacion import servicio
from aplicacion.nucleo.constantes import ROL_ADMINISTRADOR, ROL_ADMISION, ROL_MEDICO
from aplicacion.nucleo.dependencias import UsuarioActual, obtener_usuario_actual, requerir_roles
from aplicacion.nucleo.errores import ErrorNegocio
from aplicacion.nucleo.seguridad import hash_password


def probar_crear_token_acceso_genera_jwt_valido(fabrica_tokens):
    token = fabrica_tokens(id_usuario=800001, correo="admision@sanrafael.invalid", rol=ROL_ADMISION)
    assert isinstance(token, str)
    assert len(token.split(".")) == 3  # Formato encabezado.payload.firma


def probar_login_exitoso_entrega_token_y_usuario(monkeypatch):
    clave_plana = "medico2026*"
    usuario_bd = {
        "id_usuario": 800002,
        "correo": "medico1.c2@sanrafael.invalid",
        "contrasena_hash": hash_password(clave_plana),
        "rol": ROL_MEDICO,
        "id_medico": 800001,
        "activo": True,
    }
    monkeypatch.setattr(
        "aplicacion.m1_hce.autenticacion.repositorio.buscar_usuario_por_correo",
        lambda _con, _correo: usuario_bd,
    )

    respuesta = servicio.iniciar_sesion(
        conexion=MagicMock(),
        datos=SolicitudLogin(correo="medico1.c2@sanrafael.invalid", contrasena=clave_plana),
    )
    assert respuesta.token_acceso is not None
    assert respuesta.tipo_token == "bearer"
    assert respuesta.usuario.id_usuario == 800002
    assert respuesta.usuario.correo == "medico1.c2@sanrafael.invalid"
    assert respuesta.usuario.rol == ROL_MEDICO
    assert respuesta.usuario.id_medico == 800001


def probar_login_correo_inexistente_rechaza_401(monkeypatch):
    monkeypatch.setattr(
        "aplicacion.m1_hce.autenticacion.repositorio.buscar_usuario_por_correo",
        lambda _con, _correo: None,
    )
    with pytest.raises(ErrorNegocio) as error:
        servicio.iniciar_sesion(
            conexion=MagicMock(),
            datos=SolicitudLogin(correo="noexiste@sanrafael.invalid", contrasena="cualquiera"),
        )
    assert error.value.estado_http == 401
    assert error.value.codigo == "CREDENCIALES_INVALIDAS"


def probar_login_contrasena_incorrecta_rechaza_401(monkeypatch):
    usuario_bd = {
        "id_usuario": 800001,
        "correo": "admision.c2@sanrafael.invalid",
        "contrasena_hash": hash_password("clave_correcta"),
        "rol": ROL_ADMISION,
        "id_medico": None,
        "activo": True,
    }
    monkeypatch.setattr(
        "aplicacion.m1_hce.autenticacion.repositorio.buscar_usuario_por_correo",
        lambda _con, _correo: usuario_bd,
    )
    with pytest.raises(ErrorNegocio) as error:
        servicio.iniciar_sesion(
            conexion=MagicMock(),
            datos=SolicitudLogin(correo="admision.c2@sanrafael.invalid", contrasena="clave_equivocada"),
        )
    assert error.value.estado_http == 401
    assert error.value.codigo == "CREDENCIALES_INVALIDAS"


def probar_login_usuario_inactivo_rechaza_401(monkeypatch):
    usuario_bd = {
        "id_usuario": 800003,
        "correo": "bloqueado@sanrafael.invalid",
        "contrasena_hash": hash_password("clave"),
        "rol": ROL_MEDICO,
        "id_medico": None,
        "activo": False,
    }
    monkeypatch.setattr(
        "aplicacion.m1_hce.autenticacion.repositorio.buscar_usuario_por_correo",
        lambda _con, _correo: usuario_bd,
    )
    with pytest.raises(ErrorNegocio) as error:
        servicio.iniciar_sesion(
            conexion=MagicMock(),
            datos=SolicitudLogin(correo="bloqueado@sanrafael.invalid", contrasena="clave"),
        )
    assert error.value.estado_http == 401
    assert error.value.codigo == "CREDENCIALES_INVALIDAS"


def probar_obtener_usuario_actual_con_token_valido(token_medico):
    credenciales = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token_medico)
    usuario = obtener_usuario_actual(credenciales)
    assert isinstance(usuario, UsuarioActual)
    assert usuario.rol == ROL_MEDICO
    assert usuario.id_usuario == 800002
    assert usuario.id_medico == 800001


def probar_obtener_usuario_actual_sin_token_rechaza_401(monkeypatch):
    monkeypatch.setenv("AUTENTICACION_SIMULADA", "false")
    with pytest.raises(ErrorNegocio) as error:
        obtener_usuario_actual(None)
    assert error.value.estado_http == 401
    assert error.value.codigo == "NO_AUTENTICADO"


def probar_obtener_usuario_actual_token_expirado_rechaza_401(fabrica_tokens):
    # Genera token con expiracion en el pasado (-5 minutos)
    token_vencido = fabrica_tokens(expiracion_minutos=-5)
    credenciales = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token_vencido)
    with pytest.raises(ErrorNegocio) as error:
        obtener_usuario_actual(credenciales)
    assert error.value.estado_http == 401
    assert error.value.codigo == "TOKEN_EXPIRADO"


def probar_obtener_usuario_actual_token_invalido_rechaza_401():
    credenciales = HTTPAuthorizationCredentials(scheme="Bearer", credentials="token.falso.invalido")
    with pytest.raises(ErrorNegocio) as error:
        obtener_usuario_actual(credenciales)
    assert error.value.estado_http == 401
    assert error.value.codigo == "TOKEN_INVALIDO"


def probar_requerir_roles_permite_rol_autorizado(usuario_medico):
    verificador = requerir_roles(ROL_MEDICO)
    resultado = verificador(usuario=usuario_medico)
    assert resultado == usuario_medico


def probar_requerir_roles_rechaza_403_si_rol_no_coincide(usuario_admision):
    verificador = requerir_roles(ROL_MEDICO)
    with pytest.raises(ErrorNegocio) as error:
        verificador(usuario=usuario_admision)
    assert error.value.estado_http == 403
    assert error.value.codigo == "ROL_NO_AUTORIZADO"


def probar_requerir_roles_varios_roles_permitidos(usuario_admision):
    verificador = requerir_roles(ROL_MEDICO, ROL_ADMISION, ROL_ADMINISTRADOR)
    resultado = verificador(usuario=usuario_admision)
    assert resultado.rol == ROL_ADMISION
