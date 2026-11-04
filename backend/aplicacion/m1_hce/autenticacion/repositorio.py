"""Acceso a datos de usuarios para autenticacion (HU09)."""
from psycopg import Connection


def buscar_usuario_por_correo(conexion: Connection, correo: str) -> dict | None:
    """Busca un usuario activo por su correo electronico (insensible a mayusculas)."""
    with conexion.cursor() as cursor:
        cursor.execute(
            """
            SELECT id_usuario, correo, contrasena_hash, rol, id_medico, activo
            FROM usuarios
            WHERE LOWER(correo) = LOWER(%s)
            """,
            (correo.strip(),),
        )
        return cursor.fetchone()
