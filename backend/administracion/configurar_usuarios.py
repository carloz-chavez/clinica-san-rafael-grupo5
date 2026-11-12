"""Configura exclusivamente las siete cuentas C2, con claves recibidas fuera de Git."""
import argparse
import hashlib
import os
from getpass import getpass

import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict
from psycopg.rows import dict_row

from aplicacion.nucleo.configuracion import obtener_configuracion
from aplicacion.nucleo.seguridad import hash_password, verify_password

# Los primeros cuatro IDs pertenecen al seed; los tres siguientes estan reservados C2.
CUENTAS = (
    (800001, "admision.c2@sanrafael.invalid", "ADMISION", None, "CLAVE_C2_ADMISION"),
    (800002, "medico1.c2@sanrafael.invalid", "MEDICO", 800001, "CLAVE_C2_MEDICO1"),
    (800003, "medico2.c2@sanrafael.invalid", "MEDICO", 800002, "CLAVE_C2_MEDICO2"),
    (800004, "admin.c2@sanrafael.invalid", "ADMINISTRADOR", None, "CLAVE_C2_ADMIN"),
    (800005, "medico3.c2@sanrafael.invalid", "MEDICO", 800003, "CLAVE_C2_MEDICO3"),
    (800006, "medico4.c2@sanrafael.invalid", "MEDICO", 800004, "CLAVE_C2_MEDICO4"),
    (800007, "medico5.c2@sanrafael.invalid", "MEDICO", 800005, "CLAVE_C2_MEDICO5"),
)
TABLAS_CONSERVADAS = (
    "especialidades", "medicos", "pacientes", "horarios_medicos", "citas",
    "consultas_medicas", "recetas", "indicaciones_medicas", "bitacora_auditoria",
)


def huellas(conexion):
    """Compara todas las filas sin registrar datos clinicos ni depender de su orden fisico."""
    resultado = {}
    for tabla in TABLAS_CONSERVADAS:
        filas = conexion.execute(sql.SQL(
            "SELECT row_to_json(t)::text AS fila FROM public.{} t ORDER BY 1"
        ).format(sql.Identifier(tabla)))
        resumen = hashlib.sha256()
        for fila in filas:
            resumen.update(fila["fila"].encode("utf-8") + b"\n")
        resultado[tabla] = resumen.hexdigest()
    return resultado


def validar_estado(filas, completo=False):
    esperadas = {cuenta[0]: cuenta for cuenta in CUENTAS}
    presentes = set()
    for fila in filas:
        cuenta = esperadas.get(fila["id_usuario"])
        if cuenta is None or (
            fila["correo"].lower(), fila["rol"], fila["id_medico"]
        ) != cuenta[1:4]:
            raise ValueError("Estado de usuarios incompatible con C2; no se cambiaron cuentas.")
        presentes.add(fila["id_usuario"])
        if completo and not fila["activo"]:
            raise ValueError("Una cuenta configurada no esta activa.")
    obligatorios = set(esperadas) if completo else {800001, 800002, 800003, 800004}
    if not obligatorios <= presentes or len(presentes) != len(filas):
        raise ValueError("Faltan cuentas originales o hay identificadores duplicados.")


def configurar(conexion, claves):
    """Transaccion propia; exige conexion sin transaccion previa (autocommit=True)."""
    if not conexion.autocommit:
        raise ValueError("Se requiere una conexion autocommit sin transaccion previa.")
    if set(claves) != {c[4] for c in CUENTAS} or any(
        not isinstance(c, str) or not c for c in claves.values()
    ):
        raise ValueError("Se requieren las siete claves no vacias.")
    hashes = {nombre: hash_password(clave) for nombre, clave in claves.items()}
    with conexion.transaction():
        conexion.execute("SET LOCAL lock_timeout = '5s'")
        # Bloquea escrituras concurrentes incluso desde otros scripts administrativos.
        conexion.execute(sql.SQL("LOCK TABLE {} IN SHARE MODE").format(
            sql.SQL(", ").join(sql.Identifier("public", t) for t in TABLAS_CONSERVADAS)
        ))
        conexion.execute("LOCK TABLE public.usuarios IN SHARE ROW EXCLUSIVE MODE")
        medicos = conexion.execute("SELECT id_medico FROM public.medicos").fetchall()
        if {m["id_medico"] for m in medicos} != set(range(800001, 800006)):
            raise ValueError("Se requieren exactamente los cinco medicos C2 existentes.")
        validar_estado(conexion.execute("SELECT * FROM public.usuarios").fetchall())
        antes = huellas(conexion)
        for identificador, correo, rol, medico, variable in CUENTAS:
            conexion.execute(
                """INSERT INTO public.usuarios
                   (id_usuario, correo, contrasena_hash, rol, id_medico, activo)
                   OVERRIDING SYSTEM VALUE VALUES (%s, %s, %s, %s, %s, true)
                   ON CONFLICT (id_usuario) DO UPDATE
                   SET contrasena_hash = EXCLUDED.contrasena_hash, activo = true""",
                (identificador, correo, hashes[variable], rol, medico),
            )
        filas = conexion.execute("SELECT * FROM public.usuarios ORDER BY id_usuario").fetchall()
        validar_estado(filas, completo=True)
        for fila, cuenta in zip(filas, CUENTAS, strict=True):
            if not fila["contrasena_hash"].startswith("$argon2id$") or not verify_password(
                claves[cuenta[4]], fila["contrasena_hash"]
            ):
                raise ValueError("No se pudo verificar una credencial; se revierte la operacion.")
        if huellas(conexion) != antes:
            raise ValueError("Cambios inesperados fuera de usuarios; se revierte la operacion.")
    return [{k: f[k] for k in ("id_usuario", "correo", "rol", "id_medico", "activo")}
            for f in filas]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--aplicar-local", action="store_true",
                        help="Aplicar solo despues de autorizacion y respaldo verificado")
    opciones = parser.parse_args()
    if not opciones.aplicar_local:
        parser.error("Requiere --aplicar-local, autorizacion y respaldo previo.")
    configuracion = obtener_configuracion()
    destino = conninfo_to_dict(configuracion.base_datos_url)
    if configuracion.entorno != "local" or (
        destino.get("host") not in {"localhost", "127.0.0.1"}
        or destino.get("hostaddr") not in {None, "127.0.0.1"}
        or destino.get("port") != "5433"
        or destino.get("dbname") != "clinica_san_rafael"
        or destino.get("service") is not None
    ):
        parser.error("Herramienta restringida al entorno academico local, puerto 5433.")
    claves = {}
    try:
        for _, correo, _, _, variable in CUENTAS:
            clave = os.environ.get(variable)
            if clave is None:
                clave = getpass(f"Clave de {correo}: ")
                if clave != getpass("Repetir clave: "):
                    raise ValueError("Las claves no coinciden.")
            claves[variable] = clave
        with psycopg.connect(configuracion.base_datos_url, autocommit=True,
                              row_factory=dict_row, connect_timeout=3) as conexion:
            filas = configurar(conexion, claves)
    except (ValueError, psycopg.Error, EOFError, KeyboardInterrupt):
        # Los errores de PostgreSQL pueden incluir parametros y hashes: no imprimirlos.
        parser.exit(1, "Configuracion no aplicada. Revisar destino, precondiciones y entradas.\n")
    finally:
        claves.clear()
    for fila in filas:
        print(fila)
    print("Siete cuentas activas verificadas; datos ajenos a usuarios intactos.")


if __name__ == "__main__":
    main()
