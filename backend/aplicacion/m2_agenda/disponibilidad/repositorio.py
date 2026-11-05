"""Consultas SQL de medicos, horarios y citas ocupadas (HU06).

Solo lectura: la agenda no modifica pacientes ni datos clinicos.
"""
from datetime import date

from psycopg import Connection


def listar_especialidades(conexion: Connection) -> list[dict]:
    with conexion.cursor() as cursor:
        cursor.execute(
            "SELECT id_especialidad, nombre FROM public.especialidades ORDER BY nombre"
        )
        return cursor.fetchall()


def listar_medicos(
    conexion: Connection,
    id_especialidad: int | None = None,
    id_medico: int | None = None,
) -> list[dict]:
    condiciones = ["m.activo = TRUE"]
    parametros: list[int] = []
    if id_especialidad is not None:
        condiciones.append("m.id_especialidad = %s")
        parametros.append(id_especialidad)
    if id_medico is not None:
        condiciones.append("m.id_medico = %s")
        parametros.append(id_medico)
    consulta = f"""
        SELECT m.id_medico, m.nombres, m.apellidos,
               m.id_especialidad, e.nombre AS especialidad
        FROM public.medicos m
        JOIN public.especialidades e ON e.id_especialidad = m.id_especialidad
        WHERE {' AND '.join(condiciones)}
        ORDER BY e.nombre, m.apellidos, m.nombres
    """
    with conexion.cursor() as cursor:
        cursor.execute(consulta, tuple(parametros))
        return cursor.fetchall()


def listar_horarios(conexion: Connection, ids_medicos: list[int], dia_semana: int) -> list[dict]:
    if not ids_medicos:
        return []
    with conexion.cursor() as cursor:
        cursor.execute(
            """SELECT id_medico, hora_inicio, hora_fin
               FROM public.horarios_medicos
               WHERE activo = TRUE AND dia_semana = %s AND id_medico = ANY(%s)
               ORDER BY id_medico, hora_inicio""",
            (dia_semana, ids_medicos),
        )
        return cursor.fetchall()


def listar_citas_ocupadas(conexion: Connection, ids_medicos: list[int], fecha: date) -> list[dict]:
    if not ids_medicos:
        return []
    with conexion.cursor() as cursor:
        cursor.execute(
            """SELECT id_medico, hora
               FROM public.citas
               WHERE fecha = %s AND estado <> 'cancelada' AND id_medico = ANY(%s)""",
            (fecha, ids_medicos),
        )
        return cursor.fetchall()
