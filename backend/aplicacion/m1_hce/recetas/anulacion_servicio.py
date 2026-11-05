"""HU10: anulacion logica y auditoria en la transaccion de la solicitud."""
from psycopg import Connection

from aplicacion.m1_hce import publico
from aplicacion.m1_hce.recetas import anulacion_repositorio as repositorio
from aplicacion.m1_hce.recetas.anulacion_esquemas import AnulacionRespuesta, SolicitudAnulacion
from aplicacion.nucleo.auditoria import registrar_bitacora
from aplicacion.nucleo.constantes import ACCION_ANULACION, ENTIDAD_CONSULTA_MEDICA, ROL_MEDICO
from aplicacion.nucleo.dependencias import UsuarioActual
from aplicacion.nucleo.errores import ErrorNegocio


def anular(conexion: Connection, usuario: UsuarioActual, id_consulta: int,
           datos: SolicitudAnulacion) -> AnulacionRespuesta:
    if usuario.rol != ROL_MEDICO or usuario.id_medico is None:
        raise ErrorNegocio("ROL_NO_AUTORIZADO", "Solo el médico responsable puede anular la consulta.", 403)
    # Mismo bloqueo de fila que C5; se conserva hasta commit/rollback, incluida auditoria.
    consulta = publico.obtener_contexto_consulta(conexion, id_consulta)
    if consulta is None:
        raise ErrorNegocio("CONSULTA_NO_ENCONTRADA", "Consulta médica no encontrada.", 404)
    if consulta.id_medico != usuario.id_medico:
        raise ErrorNegocio("ROL_NO_AUTORIZADO", "No eres el médico responsable de esta consulta.", 403)
    if consulta.anulada:
        raise ErrorNegocio("CONSULTA_ANULADA", "La consulta ya está anulada.", 409)
    fila = repositorio.marcar_anulada(conexion, id_consulta, usuario.id_usuario, datos.motivo_anulacion)
    if fila is None:
        raise ErrorNegocio("CONSULTA_ANULADA", "La consulta ya está anulada.", 409)
    registrar_bitacora(conexion, usuario.id_usuario, consulta.id_paciente,
                      ACCION_ANULACION, ENTIDAD_CONSULTA_MEDICA, id_consulta=id_consulta)
    return AnulacionRespuesta.model_validate(fila)
