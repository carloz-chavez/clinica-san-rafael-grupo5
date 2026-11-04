from psycopg import Connection


def buscar_paciente(conexion: Connection, id_paciente: int) -> dict | None:
    """Obtiene solo las columnas del contrato publico usando filas diccionario."""
    with conexion.cursor() as cursor:
        cursor.execute(
            """
            SELECT id_paciente, dni, nombres, apellidos, fecha_nacimiento,
                   telefono, correo
            FROM public.pacientes
            WHERE id_paciente = %s
            """,
            (id_paciente,),
        )
        return cursor.fetchone()
