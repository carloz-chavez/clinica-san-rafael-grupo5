"""Acceso a PostgreSQL: pool de conexiones y una transaccion por solicitud.

Uso en un enrutador:

    from fastapi import Depends
    from psycopg import Connection
    from aplicacion.nucleo.base_datos import obtener_conexion

    @enrutador.get("/pacientes/{id_paciente}")
    def ver_paciente(id_paciente: int, conexion: Connection = Depends(obtener_conexion)):
        ...

Reglas:
  - Cada solicitud recibe UNA conexion y UNA transaccion: se confirma (commit) si la
    ruta termina bien y se revierte (rollback) si lanza cualquier error.
  - La misma conexion se pasa al servicio, al repositorio y a registrar_bitacora,
    para que la bitacora quede dentro de la misma transaccion (RNF02).
  - Las filas llegan como diccionarios: fila["id_paciente"].
"""
from collections.abc import Iterator

from psycopg import Connection
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool, PoolTimeout

from aplicacion.nucleo.configuracion import obtener_configuracion
from aplicacion.nucleo.errores import ErrorNegocio

_pool: ConnectionPool | None = None


def abrir_pool() -> None:
    """Abre el pool al arrancar la API. No falla si la base de datos aun no esta lista."""
    global _pool
    if _pool is not None:
        return
    configuracion = obtener_configuracion()
    _pool = ConnectionPool(
        conninfo=configuracion.base_datos_url,
        min_size=1,
        max_size=10,
        kwargs={"row_factory": dict_row},
        open=False,
    )
    _pool.open(wait=False)


def cerrar_pool() -> None:
    """Cierra el pool al apagar la API."""
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None


def obtener_conexion() -> Iterator[Connection]:
    """Dependencia de FastAPI: entrega una conexion dentro de una transaccion."""
    if _pool is None:
        raise ErrorNegocio(
            "BASE_DATOS_NO_DISPONIBLE",
            "La conexion con la base de datos no esta disponible.",
            503,
        )
    try:
        with _pool.connection(timeout=5) as conexion:
            yield conexion
    except PoolTimeout:
        raise ErrorNegocio(
            "BASE_DATOS_NO_DISPONIBLE",
            "No se pudo conectar con la base de datos. Intente de nuevo.",
            503,
        )
