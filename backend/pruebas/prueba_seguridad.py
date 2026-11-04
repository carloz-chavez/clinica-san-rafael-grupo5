"""Pruebas unitarias de las funciones de seguridad y hashing de contrasenas."""
import pytest

from aplicacion.nucleo.seguridad import (
    hash_password,
    hashear_contrasena,
    verificar_contrasena,
    verify_password,
)


def probar_hash_password_genera_hash_valido():
    hash_generado = hash_password("secreto123")
    assert isinstance(hash_generado, str)
    assert hash_generado.startswith("$argon2id$")


def probar_hash_password_genera_salts_distintos():
    hash1 = hash_password("misma_clave")
    hash2 = hash_password("misma_clave")
    assert hash1 != hash2


def probar_verify_password_coincide():
    clave = "admin2026*"
    hash_almacenado = hash_password(clave)
    assert verify_password(clave, hash_almacenado) is True


def probar_verify_password_rechaza_incorrecta():
    hash_almacenado = hash_password("clave_correcta")
    assert verify_password("clave_incorrecta", hash_almacenado) is False


def probar_verify_password_soporta_orden_invertido():
    clave = "medico_pass"
    hash_almacenado = hash_password(clave)
    # Por si se invoca como verify_password(hash, clave)
    assert verify_password(hash_almacenado, clave) is True


def probar_verify_password_con_valores_invalidos():
    assert verify_password("", "$argon2id$fake") is False
    assert verify_password("clave", "") is False
    assert verify_password("clave", "hash_no_argon2") is False
    assert verify_password("clave", "$argon2id$invalido$corrupto") is False


def probar_hash_password_rechaza_vacio_o_no_string():
    with pytest.raises(ValueError):
        hash_password("")

    with pytest.raises(ValueError):
        hash_password(None)  # type: ignore


def probar_alias_en_espanol():
    clave = "paciente123"
    hash_almacenado = hashear_contrasena(clave)
    assert verificar_contrasena(clave, hash_almacenado) is True
    assert verificar_contrasena("otra", hash_almacenado) is False
