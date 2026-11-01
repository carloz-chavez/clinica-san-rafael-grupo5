"""CONTRATO de la bitacora de auditoria (RNF02 y RNF04).

Toda consulta o modificacion de informacion clinica debe llamar a
registrar_bitacora DENTRO DE LA MISMA TRANSACCION de la operacion:

    registrar_bitacora(
        conexion, usuario.id_usuario, id_paciente,
        ACCION_CREACION, ENTIDAD_CONSULTA_MEDICA,
        id_consulta=id_consulta, detalle="Registro de consulta",
    )

Reglas del esquema (bitacora_auditoria):
  - Si la entidad NO es HISTORIA, id_consulta es obligatorio.
  - La tabla es inmutable: un trigger impide UPDATE y DELETE.

Responsable de la implementacion: Carlos (tarea C3).
"""


def registrar_bitacora(
    conexion,
    id_usuario: int,
    id_paciente: int,
    accion: str,
    entidad: str,
    id_consulta: int | None = None,
    detalle: str | None = None,
) -> None:
    """Inserta una fila en bitacora_auditoria usando la conexion recibida."""
    raise NotImplementedError("Pendiente: Carlos (tarea C3)")
