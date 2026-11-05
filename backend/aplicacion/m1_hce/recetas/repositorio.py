"""Inserciones HU04 parametrizadas; no modifica ni elimina registros historicos."""
from psycopg import Connection

from aplicacion.m1_hce.recetas.esquemas import DatosIndicacion, DatosReceta


def registrar_receta(conexion: Connection, id_consulta: int, datos: DatosReceta) -> dict:
    with conexion.cursor() as cursor:
        cursor.execute(
            """INSERT INTO public.recetas
                (id_consulta,medicamento,dosis,frecuencia,duracion,indicaciones)
                VALUES (%s,%s,%s,%s,%s,%s)
                RETURNING id_receta,id_consulta,medicamento,dosis,frecuencia,
                          duracion,indicaciones,fecha_registro""",
            (id_consulta, datos.medicamento, datos.dosis, datos.frecuencia, datos.duracion, datos.indicaciones),
        )
        return cursor.fetchone()


def registrar_indicacion(conexion: Connection, id_consulta: int, datos: DatosIndicacion) -> dict:
    with conexion.cursor() as cursor:
        cursor.execute(
            """INSERT INTO public.indicaciones_medicas(id_consulta,descripcion)
                VALUES (%s,%s)
                RETURNING id_indicacion,id_consulta,descripcion,fecha_registro""",
            (id_consulta, datos.descripcion),
        )
        return cursor.fetchone()
