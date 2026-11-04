"""INTERFAZ PUBLICA de M1 (Historia Clinica Electronica).

Es lo UNICO de M1 que otros modulos pueden importar. M2 (Agenda y Citas)
valida al paciente con obtener_paciente y nunca consulta la tabla pacientes
ni importa el repositorio de M1 (decision de arquitectura, ADR 4 y ADR 5).
"""
from datetime import date

from pydantic import BaseModel


class PacienteSalida(BaseModel):
    id_paciente: int
    dni: str
    nombres: str
    apellidos: str
    fecha_nacimiento: date
    telefono: str | None = None
    correo: str | None = None


def obtener_paciente(conexion, id_paciente: int) -> PacienteSalida | None:
    """Devuelve el paciente o None si no existe o esta inactivo."""
    if conexion is None:
        return None

    with conexion.cursor() as cursor:
        cursor.execute(
            """
            SELECT id_paciente, dni, nombres, apellidos, fecha_nacimiento, telefono, correo
            FROM pacientes
            WHERE id_paciente = %s AND activo = TRUE
            """,
            (id_paciente,),
        )
        fila = cursor.fetchone()
        if not fila:
            return None

        return PacienteSalida(
            id_paciente=fila["id_paciente"],
            dni=fila["dni"],
            nombres=fila["nombres"],
            apellidos=fila["apellidos"],
            fecha_nacimiento=fila["fecha_nacimiento"],
            telefono=fila.get("telefono"),
            correo=fila.get("correo"),
        )
