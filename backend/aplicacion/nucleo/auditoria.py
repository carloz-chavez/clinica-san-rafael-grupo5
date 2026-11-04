"""CONTRATO e implementacion de la bitacora de auditoria (RNF02 y RNF04).

Toda consulta o modificacion de informacion clinica debe llamar a
registrar_bitacora DENTRO DE LA MISMA TRANSACCION de la operacion:

    registrar_bitacora(
        conexion, usuario.id_usuario, id_paciente,
        ACCION_CREACION, ENTIDAD_CONSULTA_MEDICA,
        id_registro=id_consulta, detalle="Registro de consulta",
    )

Reglas del esquema (bitacora_auditoria):
  - Inmutable: un trigger impide UPDATE y DELETE.
  - Registra usuario, paciente (si aplica), accion, entidad e id_registro.
"""


def registrar_bitacora(
    conexion,
    id_usuario: int,
    id_paciente: int | None,
    accion: str,
    entidad: str,
    id_registro: int | None = None,
    detalle: str | None = None,
    *,
    id_consulta: int | None = None,
) -> None:
    """Inserta una fila en bitacora_auditoria usando la conexion recibida."""
    registro_id = id_registro if id_registro is not None else id_consulta
    if conexion is None:
        return

    with conexion.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO bitacora_auditoria (
                id_usuario, id_paciente, accion, entidad, id_registro, detalle
            ) VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (id_usuario, id_paciente, accion, entidad, registro_id, detalle),
        )
