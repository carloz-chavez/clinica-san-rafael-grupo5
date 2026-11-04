from psycopg import Connection

from aplicacion.m1_hce.pacientes import repositorio


def buscar_paciente(conexion: Connection, id_paciente: int) -> dict | None:
    """Obtiene solo las columnas del contrato publico usando filas diccionario."""
    # La fachada C3 mantiene PacienteSalida y filtra los campos internos.
    return repositorio.buscar_por_id(conexion, id_paciente)
