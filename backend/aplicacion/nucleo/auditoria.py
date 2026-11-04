"""CONTRATO de la bitacora de auditoria (RNF02 y RNF04).

Toda consulta o modificacion de informacion clinica debe llamar a
registrar_bitacora DENTRO DE LA MISMA TRANSACCION de la operacion:
"""
from psycopg import Connection

from aplicacion.nucleo.constantes import ACCIONES_BITACORA, ENTIDADES_BITACORA
from aplicacion.nucleo.errores import ErrorNegocio


def _validar_identificador(valor: int | None, *, opcional: bool) -> None:
    if valor is None and opcional:
        return
    if type(valor) is not int or valor <= 0:
        raise ErrorNegocio("DATOS_INVALIDOS", "Los identificadores deben ser enteros positivos.", 422)


def registrar_bitacora(
    conexion: Connection,
    id_usuario: int,
    id_paciente: int | None,
    accion: str,
    entidad: str,
    id_registro: int | None = None,
    detalle: str | None = None,
    *,
    id_consulta: int | None = None,
) -> None:
    if conexion.autocommit is True:
        raise ErrorNegocio("DATOS_INVALIDOS", "La auditoria requiere una conexion transaccional.", 422)
    if accion not in ACCIONES_BITACORA or entidad not in ENTIDADES_BITACORA:
        raise ErrorNegocio("DATOS_INVALIDOS", "Accion o entidad de auditoria no autorizada.", 422)
    _validar_identificador(id_usuario, opcional=False)
    _validar_identificador(id_paciente, opcional=True)
    _validar_identificador(id_registro, opcional=True)
    _validar_identificador(id_consulta, opcional=True)
    if id_registro is not None and id_consulta is not None and id_registro != id_consulta:
        raise ErrorNegocio("DATOS_INVALIDOS", "id_registro e id_consulta deben coincidir.", 422)
    registro = id_registro if id_registro is not None else id_consulta
    detalle_seguro = None if detalle is None else f"{accion} de {entidad}"
    with conexion.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO public.bitacora_auditoria
                (id_usuario, id_paciente, accion, entidad, id_registro, detalle)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (id_usuario, id_paciente, accion, entidad, registro, detalle_seguro),
        )
