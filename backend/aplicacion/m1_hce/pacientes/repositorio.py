"""Persistencia HU01. Solo SQL parametrizado; la transaccion pertenece al llamador."""
from psycopg import Connection

from aplicacion.m1_hce.pacientes.esquemas import DatosPaciente

_COLUMNAS = "id_paciente, dni, nombres, apellidos, fecha_nacimiento, sexo, telefono, correo, direccion, fecha_registro, activo"
_CAMPOS = ("dni", "nombres", "apellidos", "fecha_nacimiento", "sexo", "telefono", "correo", "direccion")


def buscar_por_id(conexion: Connection, id_paciente: int) -> dict | None:
    with conexion.cursor() as cursor:
        cursor.execute(f"SELECT {_COLUMNAS} FROM public.pacientes WHERE id_paciente=%s", (id_paciente,))
        return cursor.fetchone()


def buscar_por_dni(conexion: Connection, dni: str) -> dict | None:
    with conexion.cursor() as cursor:
        cursor.execute(f"SELECT {_COLUMNAS} FROM public.pacientes WHERE dni=%s", (dni,))
        return cursor.fetchone()


def registrar(conexion: Connection, datos: DatosPaciente) -> dict:
    with conexion.cursor() as cursor:
        cursor.execute(
            f"""INSERT INTO public.pacientes
                (dni,nombres,apellidos,fecha_nacimiento,sexo,telefono,correo,direccion)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING {_COLUMNAS}""",
            tuple(getattr(datos, campo) for campo in _CAMPOS),
        )
        return cursor.fetchone()


def actualizar(conexion: Connection, id_paciente: int, datos: DatosPaciente) -> dict | None:
    with conexion.cursor() as cursor:
        cursor.execute(
            f"""UPDATE public.pacientes SET dni=%s,nombres=%s,apellidos=%s,
                fecha_nacimiento=%s,sexo=%s,telefono=%s,correo=%s,direccion=%s
                WHERE id_paciente=%s RETURNING {_COLUMNAS}""",
            (*(getattr(datos, campo) for campo in _CAMPOS), id_paciente),
        )
        return cursor.fetchone()


def tiene_vinculo_asistencial(conexion: Connection, id_medico: int, id_paciente: int) -> bool:
    """Solo existencia de relacion; no entrega datos clinicos ni modifica M2.

    Politica propuesta para validacion del equipo en C4: una cita no cancelada
    o consulta no anulada permite consultar. Aun no existe interfaz publica M2.
    """
    with conexion.cursor() as cursor:
        cursor.execute(
            """SELECT EXISTS(SELECT 1 FROM public.citas
                   WHERE id_medico=%s AND id_paciente=%s AND estado<>'cancelada')
                OR EXISTS(SELECT 1 FROM public.consultas_medicas
                   WHERE id_medico=%s AND id_paciente=%s AND NOT anulada) AS permitido""",
            (id_medico, id_paciente, id_medico, id_paciente),
        )
        return cursor.fetchone()["permitido"]
