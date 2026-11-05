"""Actualiza exclusivamente los metadatos de anulacion, nunca el registro clinico."""
from psycopg import Connection


def marcar_anulada(conexion: Connection, id_consulta: int, id_usuario: int, motivo: str) -> dict | None:
    with conexion.cursor() as cursor:
        cursor.execute(
            """UPDATE public.consultas_medicas
               SET anulada=true, motivo_anulacion=%s,
                   fecha_anulacion=clock_timestamp()::timestamp, id_usuario_anulacion=%s
               WHERE id_consulta=%s AND anulada=false
               RETURNING id_consulta, anulada, motivo_anulacion,
                         fecha_anulacion, id_usuario_anulacion""",
            (motivo, id_usuario, id_consulta),
        )
        return cursor.fetchone()
