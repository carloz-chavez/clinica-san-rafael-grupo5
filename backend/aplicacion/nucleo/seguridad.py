"""Funciones de seguridad para contrasenas usando Argon2id.

Carlos usa este modulo para generar los hashes de los usuarios en db/02_seed.sql.
Angel lo usa en la HU09 para verificar las credenciales al iniciar sesion.
"""
import sys
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

_hasheador = PasswordHasher()


def hash_password(password: str) -> str:
    """Genera un hash seguro Argon2id a partir de la contrasena en texto plano."""
    if not isinstance(password, str) or not password:
        raise ValueError("La contrasena debe ser un texto no vacio.")
    return _hasheador.hash(password)


def verify_password(password: str, hash_almacenado: str) -> bool:
    """Compara la contrasena contra el hash almacenado.

    Acepta los parametros en cualquier orden por si se pasan invertidos (hash, password).
    Devuelve True si coincide y False si no coincide o el hash no es valido.
    """
    if not password or not hash_almacenado:
        return False

    # Soporte por si se pasan en orden (hash, plain)
    if password.startswith("$argon2") and not hash_almacenado.startswith("$argon2"):
        hash_almacenado, password = password, hash_almacenado
    elif not hash_almacenado.startswith("$argon2"):
        return False

    try:
        return _hasheador.verify(hash_almacenado, password)
    except (VerificationError, InvalidHashError):
        return False


# Alias en espanol segun las convenciones del equipo
hashear_contrasena = hash_password
verificar_contrasena = verify_password


if __name__ == "__main__":
    # Permite generar hashes directo desde la terminal para armar el seed:
    # python -m aplicacion.nucleo.seguridad "mi_contrasena"
    if len(sys.argv) > 1:
        for valor in sys.argv[1:]:
            print(f"{valor} -> {hash_password(valor)}")
    else:
        print("Uso: python -m aplicacion.nucleo.seguridad <contrasena1> [contrasena2 ...]")
        print("Ejemplo demo:")
        print("  admin123   ->", hash_password("admin123"))
        print("  medico123  ->", hash_password("medico123"))
        print("  admision123->", hash_password("admision123"))
