"""Repositorio de datos para consultas medicas e historia clinica (HU02 y HU03)."""
from datetime import datetime

from psycopg import Connection


def buscar_paciente(conexion: Connection, id_paciente: int) -> dict | None:
    """Busca un paciente por su identificador primario."""
    with conexion.cursor() as cursor:
        cursor.execute(
            """
            SELECT id_paciente, dni, nombres, apellidos, fecha_nacimiento,
                   sexo, telefono, correo, direccion, activo
            FROM pacientes
            WHERE id_paciente = %s
            """,
            (id_paciente,),
        )
        return cursor.fetchone()


def buscar_cita(conexion: Connection, id_cita: int) -> dict | None:
    """Obtiene los datos de una cita agendada."""
    with conexion.cursor() as cursor:
        cursor.execute(
            """
            SELECT id_cita, id_paciente, id_medico, fecha, hora, estado, motivo
            FROM citas
            WHERE id_cita = %s
            """,
            (id_cita,),
        )
        return cursor.fetchone()


def marcar_cita_atendida(conexion: Connection, id_cita: int) -> None:
    """Actualiza el estado de la cita a atendida al finalizar la consulta."""
    with conexion.cursor() as cursor:
        cursor.execute(
            """
            UPDATE citas
            SET estado = 'atendida'
            WHERE id_cita = %s
            """,
            (id_cita,),
        )


def insertar_consulta(
    conexion: Connection,
    id_paciente: int,
    id_medico: int,
    id_cita: int | None,
    fecha_hora: datetime,
    diagnostico_cie10: str | None,
    observaciones: str | None,
) -> dict:
    """Inserta una nueva consulta medica en la base de datos."""
    with conexion.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO consultas_medicas (
                id_paciente, id_medico, id_cita, fecha_hora, diagnostico_cie10, observaciones, anulada
            ) VALUES (
                %s, %s, %s, %s, %s, %s, FALSE
            )
            RETURNING id_consulta, id_paciente, id_medico, id_cita, fecha_hora,
                      diagnostico_cie10, observaciones, anulada,
                      motivo_anulacion, fecha_anulacion, id_usuario_anulacion
            """,
            (
                id_paciente,
                id_medico,
                id_cita,
                fecha_hora,
                diagnostico_cie10,
                observaciones,
            ),
        )
        return cursor.fetchone()


def buscar_consulta_por_id(conexion: Connection, id_consulta: int) -> dict | None:
    """Recupera una consulta medica individual por su identificador."""
    with conexion.cursor() as cursor:
        cursor.execute(
            """
            SELECT id_consulta, id_paciente, id_medico, id_cita, fecha_hora,
                   diagnostico_cie10, observaciones, anulada,
                   motivo_anulacion, fecha_anulacion, id_usuario_anulacion
            FROM consultas_medicas
            WHERE id_consulta = %s
            """,
            (id_consulta,),
        )
        return cursor.fetchone()


def listar_consultas_paciente(conexion: Connection, id_paciente: int) -> list[dict]:
    """Obtiene todas las consultas del paciente ordenadas cronologicamente descendente.

    Incluye las consultas activas y anuladas, con los datos de filiacion del medico tratante.
    """
    with conexion.cursor() as cursor:
        cursor.execute(
            """
            SELECT c.id_consulta,
                   c.id_paciente,
                   c.id_medico,
                   c.id_cita,
                   c.fecha_hora,
                   c.diagnostico_cie10,
                   c.observaciones,
                   c.anulada,
                   c.motivo_anulacion,
                   c.fecha_anulacion,
                   c.id_usuario_anulacion,
                   (m.nombres || ' ' || m.apellidos) AS medico_nombre_completo,
                   m.numero_colegiatura AS medico_colegiatura,
                   e.nombre AS medico_especialidad
            FROM consultas_medicas c
            JOIN medicos m ON c.id_medico = m.id_medico
            LEFT JOIN especialidades e ON m.id_especialidad = e.id_especialidad
            WHERE c.id_paciente = %s
            ORDER BY c.fecha_hora DESC, c.id_consulta DESC
            """,
            (id_paciente,),
        )
        return cursor.fetchall()


def listar_recetas_por_consultas(conexion: Connection, ids_consultas: list[int]) -> list[dict]:
    """Obtiene las recetas emitidas para el conjunto de consultas especificado."""
    if not ids_consultas:
        return []
    with conexion.cursor() as cursor:
        cursor.execute(
            """
            SELECT id_receta, id_consulta, medicamento, dosis, frecuencia,
                   duracion, indicaciones, fecha_registro
            FROM recetas
            WHERE id_consulta = ANY(%s)
            ORDER BY id_receta ASC
            """,
            (ids_consultas,),
        )
        return cursor.fetchall()


def listar_indicaciones_por_consultas(conexion: Connection, ids_consultas: list[int]) -> list[dict]:
    """Obtiene las indicaciones medicas emitidas para el conjunto de consultas."""
    if not ids_consultas:
        return []
    with conexion.cursor() as cursor:
        cursor.execute(
            """
            SELECT id_indicacion, id_consulta, descripcion, fecha_registro
            FROM indicaciones_medicas
            WHERE id_consulta = ANY(%s)
            ORDER BY id_indicacion ASC
            """,
            (ids_consultas,),
        )
        return cursor.fetchall()
