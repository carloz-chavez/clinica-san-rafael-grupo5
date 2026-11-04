"""Alias de compatibilidad con importaciones en ingles."""
from aplicacion.nucleo.seguridad import (
    hash_password,
    hashear_contrasena,
    verificar_contrasena,
    verify_password,
)

__all__ = ["hash_password", "verify_password", "hashear_contrasena", "verificar_contrasena"]
