"""Persistencia de citas (HU07). El llamador controla la transaccion."""
from datetime import date

from psycopg import Connection

from aplicacion.m2_agenda.citas.esquemas import SolicitudCita

# M2 no consulta la tabla pacientes: los datos del paciente llegan por
# aplicacion.m1_hce.publico.obtener_paciente (ADR 4 y ADR 5).
_DETALLE = """
    SELECT c.id_cita, c.id_paciente,
           c.id_medico, m.nombres AS nombres_medico, m.apellidos AS apellidos_medico,
           e.nombre AS especialidad,
           c.fecha, c.hora, c.estado, c.motivo, c.fecha_registro
    FROM public.citas c
    JOIN public.medicos m ON m.id_medico = c.id_medico
    JOIN public.especialidades e ON e.id_especialidad = m.id_especialidad
"""


def obtener_medico_activo(conexion: Connection, id_medico: int) -> dict | None:
    with conexion.cursor() as cursor:
        cursor.execute(
            "SELECT id_medico FROM public.medicos WHERE id_medico = %s AND activo = TRUE",
            (id_medico,),
        )
        return cursor.fetchone()


def registrar(conexion: Connection, datos: SolicitudCita) -> int:
    with conexion.cursor() as cursor:
        cursor.execute(
            """INSERT INTO public.citas (id_paciente, id_medico, fecha, hora, motivo)
               VALUES (%s, %s, %s, %s, %s)
               RETURNING id_cita""",
            (datos.id_paciente, datos.id_medico, datos.fecha, datos.hora, datos.motivo),
        )
        return cursor.fetchone()["id_cita"]


def buscar_detalle(conexion: Connection, id_cita: int) -> dict | None:
    with conexion.cursor() as cursor:
        cursor.execute(f"{_DETALLE} WHERE c.id_cita = %s", (id_cita,))
        return cursor.fetchone()


def listar_por_fecha(conexion: Connection, fecha: date) -> list[dict]:
    with conexion.cursor() as cursor:
        cursor.execute(
            f"{_DETALLE} WHERE c.fecha = %s ORDER BY c.hora, m.apellidos, m.nombres",
            (fecha,),
        )
        return cursor.fetchall()
