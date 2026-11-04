"""HU04: registro aditivo de recetas/indicaciones con auditoria atomica."""
from psycopg import Connection

from aplicacion.m1_hce import publico
from aplicacion.m1_hce.recetas import repositorio
from aplicacion.m1_hce.recetas.esquemas import RegistroIndicaciones, RegistroRespuesta
from aplicacion.nucleo.auditoria import registrar_bitacora
from aplicacion.nucleo.constantes import ACCION_CREACION, ENTIDAD_INDICACION, ENTIDAD_RECETA, ROL_MEDICO
from aplicacion.nucleo.dependencias import UsuarioActual
from aplicacion.nucleo.errores import ErrorNegocio


def registrar(conexion: Connection, usuario: UsuarioActual, id_consulta: int, datos: RegistroIndicaciones) -> RegistroRespuesta:
    # Politica propuesta HU04 para validacion del equipo: solo medico responsable.
    # No concede capacidad de prescribir a roles administrativos.
    if usuario.rol != ROL_MEDICO or usuario.id_medico is None:
        raise ErrorNegocio("ROL_NO_AUTORIZADO", "Solo el médico responsable puede registrar indicaciones.", 403)
    consulta = publico.obtener_contexto_consulta(conexion, id_consulta)
    if consulta is None:
        raise ErrorNegocio("CONSULTA_NO_ENCONTRADA", "Consulta médica no encontrada.", 404)
    if consulta.id_medico != usuario.id_medico:
        raise ErrorNegocio("ROL_NO_AUTORIZADO", "No eres el médico responsable de esta consulta.", 403)
    if consulta.anulada:
        raise ErrorNegocio("CONSULTA_ANULADA", "No se pueden agregar registros a una consulta anulada.", 409)

    recetas = []
    indicaciones = []
    for receta in datos.recetas:
        fila = repositorio.registrar_receta(conexion, id_consulta, receta)
        registrar_bitacora(conexion, usuario.id_usuario, consulta.id_paciente,
                           ACCION_CREACION, ENTIDAD_RECETA, id_registro=fila["id_receta"])
        recetas.append(fila)
    for indicacion in datos.indicaciones:
        fila = repositorio.registrar_indicacion(conexion, id_consulta, indicacion)
        registrar_bitacora(conexion, usuario.id_usuario, consulta.id_paciente,
                           ACCION_CREACION, ENTIDAD_INDICACION, id_registro=fila["id_indicacion"])
        indicaciones.append(fila)
    return RegistroRespuesta(id_consulta=id_consulta, recetas=recetas, indicaciones=indicaciones)
