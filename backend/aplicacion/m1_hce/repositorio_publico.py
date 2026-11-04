from psycopg import Connection

from aplicacion.m1_hce.pacientes import repositorio


def buscar_paciente(conexion: Connection, id_paciente: int) -> dict | None:
    """Obtiene solo las columnas del contrato publico usando filas diccionario."""
    # La fachada C3 mantiene PacienteSalida y filtra los campos internos.
    return repositorio.buscar_por_id(conexion, id_paciente)


def buscar_contexto_consulta(conexion: Connection, id_consulta: int) -> dict | None:
    """Lectura minima C5; el bloqueo dura hasta finalizar la transaccion del llamador."""
    with conexion.cursor() as cursor:
        cursor.execute(
            """SELECT id_consulta,id_paciente,id_medico,anulada
                FROM public.consultas_medicas WHERE id_consulta=%s FOR UPDATE""",
            (id_consulta,),
        )
        return cursor.fetchone()
