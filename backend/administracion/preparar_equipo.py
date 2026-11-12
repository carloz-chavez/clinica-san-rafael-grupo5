"""Preparacion de datos ficticios C2; no forma parte del inicio de la API."""
import argparse
import hashlib
import json
import os
import re
import secrets
from pathlib import Path

import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo
from psycopg.rows import dict_row

from administracion.configurar_usuarios import (
    CUENTAS,
    TABLAS_CONSERVADAS,
    configurar,
    validar_estado,
)
from aplicacion.nucleo.configuracion import RAIZ_PROYECTO, obtener_configuracion
from aplicacion.nucleo.seguridad import hash_password, verify_password

TABLAS = (*TABLAS_CONSERVADAS, "usuarios")


class ErrorPreparacion(ValueError):
    """Mensaje que se puede mostrar sin revelar datos de conexion."""


def cargar_claves():
    ruta = Path(os.environ.get("EQUIPO_CREDENCIALES_ARCHIVO",
                               RAIZ_PROYECTO / "db/desarrollo/cuentas_ficticias.json"))
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    if datos.get("uso") != "academico-local-C2" or set(datos["claves"]) != {c[1] for c in CUENTAS}:
        raise ErrorPreparacion("Configuracion de demostracion incompatible.")
    if not all(isinstance(c, str) and c for c in datos["claves"].values()):
        raise ErrorPreparacion("Faltan claves academicas. Preparalas con el script del equipo.")
    return {c[4]: datos["claves"][c[1]] for c in CUENTAS}


def validar_destino(configuracion):
    destino = conninfo_to_dict(configuracion.base_datos_url)
    if (configuracion.entorno != "local" or destino.get("host") not in {"localhost", "127.0.0.1"}
        or destino.get("port") != "5433" or destino.get("dbname") != "clinica_san_rafael"
        or destino.get("hostaddr") not in {None, "127.0.0.1"} or destino.get("service")):
        raise ErrorPreparacion("Destino rechazado: se requiere PostgreSQL academico local en el puerto 5433.")


def verificar_esquema(conexion):
    tablas = conexion.execute("SELECT tablename FROM pg_tables WHERE schemaname='public'").fetchall()
    if {f["tablename"] for f in tablas} != set(TABLAS):
        raise ErrorPreparacion("Esquema incompatible: se requieren las diez tablas del proyecto.")
    esquema = (RAIZ_PROYECTO / "db/01_esquema.sql").read_text(encoding="utf-8")
    restricciones = conexion.execute("""SELECT conname, convalidated, contype FROM pg_constraint
        WHERE connamespace='public'::regnamespace""").fetchall()
    if (not set(re.findall(r"CONSTRAINT\s+(\w+)", esquema)) <= {r["conname"] for r in restricciones}
        or any(not r["convalidated"] for r in restricciones)
        or sum(r["contype"] == "p" for r in restricciones) != 10
        or sum(r["contype"] == "f" for r in restricciones) != 13):
        raise ErrorPreparacion("Restricciones incompletas o sin validar; no se modifico la base.")
    indices = conexion.execute("""SELECT c.relname, i.indisvalid FROM pg_index i
        JOIN pg_class c ON c.oid=i.indexrelid WHERE c.relnamespace='public'::regnamespace""").fetchall()
    if (not set(re.findall(r"CREATE (?:UNIQUE )?INDEX\s+(\w+)", esquema)) <= {i["relname"] for i in indices}
        or any(not i["indisvalid"] for i in indices)):
        raise ErrorPreparacion("Indices incompletos o invalidos.")
    triggers = conexion.execute("""SELECT tgname,tgenabled FROM pg_trigger
        WHERE tgrelid IN (SELECT oid FROM pg_class WHERE relnamespace='public'::regnamespace)
        AND NOT tgisinternal""").fetchall()
    if not set(re.findall(r"CREATE TRIGGER\s+(\w+)", esquema)) <= {
        t["tgname"] for t in triggers if t["tgenabled"] == "O"
    }:
        raise ErrorPreparacion("Faltan protecciones activas del esquema.")
    for rol in ("clinica_auditoria_writer", "clinica_auditoria_reader"):
        fila = conexion.execute("""SELECT oid,rolcanlogin,rolsuper,rolcreatedb,rolcreaterole,
            rolreplication,rolbypassrls FROM pg_roles WHERE rolname=%s""", (rol,)).fetchone()
        if not fila or any(fila[k] for k in fila if k != "oid"):
            raise ErrorPreparacion("Roles tecnicos de auditoria incompatibles.")
        if conexion.execute("SELECT 1 FROM pg_auth_members WHERE member=%s", (fila["oid"],)).fetchone():
            raise ErrorPreparacion("Revisar las membresias de auditoria.")
        if not conexion.execute("SELECT has_schema_privilege(%s,'public','USAGE') AS acceso",
                                (rol,)).fetchone()["acceso"]:
            raise ErrorPreparacion("Falta acceso al esquema para los roles de auditoria.")
        for permiso in ("UPDATE", "DELETE", "TRUNCATE", "REFERENCES", "TRIGGER"):
            if conexion.execute("SELECT has_table_privilege(%s,'public.bitacora_auditoria',%s) AS acceso",
                                (rol, permiso)).fetchone()["acceso"]:
                raise ErrorPreparacion("Permisos de auditoria excesivos.")
        for permiso in ("SELECT", "USAGE", "UPDATE"):
            if conexion.execute("SELECT has_sequence_privilege(%s,'public.bitacora_auditoria_id_auditoria_seq',%s) AS acceso",
                                (rol, permiso)).fetchone()["acceso"]:
                raise ErrorPreparacion("La secuencia de auditoria tiene permisos inesperados.")
        columnas = conexion.execute("""SELECT attname,
            has_column_privilege(%s,attrelid,attnum,'INSERT') AS insertar,
            has_column_privilege(%s,attrelid,attnum,'SELECT') AS leer,
            has_column_privilege(%s,attrelid,attnum,'UPDATE') AS actualizar
            FROM pg_attribute WHERE attrelid='public.bitacora_auditoria'::regclass
            AND attnum>0 AND NOT attisdropped""", (rol, rol, rol)).fetchall()
        permitidas = {"id_usuario", "id_paciente", "accion", "entidad", "id_registro", "detalle"}
        for columna in columnas:
            if (columna["actualizar"] or columna["leer"] != (rol.endswith("reader"))
                or columna["insertar"] != (rol.endswith("writer") and columna["attname"] in permitidas)):
                raise ErrorPreparacion("Los permisos de columnas de auditoria no coinciden.")


def inspeccionar(conexion, claves):
    verificar_esquema(conexion)
    conteos = {t: conexion.execute(sql.SQL("SELECT count(*) AS n FROM public.{}").format(
        sql.Identifier(t))).fetchone()["n"] for t in TABLAS}
    if not any(conteos.values()):
        return "vacia"
    filas = conexion.execute("SELECT * FROM public.usuarios ORDER BY id_usuario").fetchall()
    medicos = conexion.execute("SELECT id_medico,activo FROM public.medicos").fetchall()
    if len(filas) not in {4, 7} or {m["id_medico"] for m in medicos} != set(range(800001, 800006)):
        raise ErrorPreparacion("Datos incompatibles: no corresponden al estado C2 de cuatro o siete cuentas.")
    if not all(m["activo"] for m in medicos):
        raise ErrorPreparacion("Hay medicos C2 inactivos; revisar antes de continuar.")
    try:
        validar_estado(filas)
    except ValueError as error:
        raise ErrorPreparacion("Las identidades C2 no coinciden; no se reasignaron cuentas.") from error
    if len(filas) == 4:
        return "cuatro_cuentas"
    coinciden = all(f["activo"] and f["contrasena_hash"].startswith("$argon2id$")
        and verify_password(claves[c[4]], f["contrasena_hash"])
        for f, c in zip(filas, CUENTAS, strict=True))
    return "configurada" if coinciden and len({f["contrasena_hash"] for f in filas}) == 7 else "requiere_restablecer"


def cargar_seed(conexion):
    # Reutiliza el SQL C2; solo sustituye la entrada de psql, sin copiar sus datos.
    texto = (RAIZ_PROYECTO / "db/02_seed.sql").read_text(encoding="utf-8")
    cuerpo = texto.split("BEGIN;", 1)[1].rsplit("COMMIT;", 1)[0]
    valor = sql.Literal(hash_password(secrets.token_urlsafe(32))).as_string(conexion)
    conexion.execute(cuerpo.replace(":'seed_hash'", valor), prepare=False)


def preparar(conexion, claves, *, restablecer=False, respaldo_verificado=False):
    if not conexion.autocommit:
        raise ErrorPreparacion("Se requiere una conexion autocommit sin transaccion previa.")
    with conexion.transaction():
        conexion.execute("SET LOCAL lock_timeout='5s'")
        conexion.execute(sql.SQL("LOCK TABLE {} IN SHARE ROW EXCLUSIVE MODE").format(
            sql.SQL(", ").join(sql.Identifier("public", t) for t in sorted(TABLAS))))
        estado = inspeccionar(conexion, claves)
        if estado == "configurada":
            return {"estado": estado, "cambios": False, "cuentas_activas": 7}
        if estado != "vacia" and not (restablecer and respaldo_verificado):
            raise ErrorPreparacion("Se requiere respaldo verificado y confirmacion de restablecimiento.")
        if estado == "vacia":
            cargar_seed(conexion)
        configurar(conexion, claves)
        if inspeccionar(conexion, claves) != "configurada":
            raise ErrorPreparacion("La verificacion final fallo; se revierte la operacion.")
    return {"estado": "configurada", "cambios": True, "cuentas_activas": 7}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("accion", choices=("inspeccionar", "aplicar"))
    parser.add_argument("--puerto-contenedor", action="store_true")
    parser.add_argument("--restablecer", action="store_true")
    parser.add_argument("--respaldo", type=Path)
    opciones = parser.parse_args()
    try:
        configuracion = obtener_configuracion()
        validar_destino(configuracion)
        claves = cargar_claves()
        url = configuracion.base_datos_url
        if opciones.puerto_contenedor:
            url = make_conninfo(url, port=5432)
        with psycopg.connect(url, autocommit=True, row_factory=dict_row, connect_timeout=3) as conexion:
            if opciones.accion == "inspeccionar":
                with conexion.transaction():
                    conexion.execute("SET TRANSACTION READ ONLY")
                    resultado = {"estado": inspeccionar(conexion, claves),
                                 "simulacion": configuracion.autenticacion_simulada}
            else:
                respaldo = False
                if opciones.respaldo:
                    ruta = opciones.respaldo.resolve()
                    contenido = ruta.read_bytes()
                    respaldo = (contenido.startswith(b"PGDMP") and hashlib.sha256(contenido).hexdigest().upper()
                                == ruta.with_suffix(".sha256").read_text(encoding="utf-8-sig").strip().upper())
                    if not respaldo:
                        raise ErrorPreparacion("El respaldo no coincide con su checksum.")
                resultado = preparar(conexion, claves, restablecer=opciones.restablecer,
                                     respaldo_verificado=respaldo)
        print(json.dumps(resultado))
    except ErrorPreparacion as error:
        parser.exit(1, f"{error}\n")
    except (ValueError, KeyError, OSError, psycopg.Error):
        parser.exit(1, "No se pudo preparar el entorno. Revisar conexion, esquema y archivos; no se muestran secretos.\n")


if __name__ == "__main__":
    main()
