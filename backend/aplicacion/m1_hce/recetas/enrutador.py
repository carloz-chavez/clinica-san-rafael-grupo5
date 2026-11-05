"""Endpoint HU04; se registra automaticamente desde principal.py."""
from typing import Annotated

from fastapi import APIRouter, Depends, Path
from psycopg import Connection

from aplicacion.m1_hce.recetas import servicio
from aplicacion.m1_hce.recetas import anulacion_servicio
from aplicacion.m1_hce.recetas.anulacion_esquemas import AnulacionRespuesta, SolicitudAnulacion
from aplicacion.m1_hce.recetas.esquemas import RegistroIndicaciones, RegistroRespuesta
from aplicacion.nucleo.base_datos import obtener_conexion
from aplicacion.nucleo.constantes import ROL_MEDICO
from aplicacion.nucleo.dependencias import UsuarioActual, requerir_roles

enrutador = APIRouter(prefix="/consultas", tags=["Recetas e indicaciones"])


@enrutador.post("/{id_consulta}/indicaciones", response_model=RegistroRespuesta, status_code=201)
def registrar_indicaciones(
    id_consulta: Annotated[int, Path(gt=0)],
    datos: RegistroIndicaciones,
    usuario: Annotated[UsuarioActual, Depends(requerir_roles(ROL_MEDICO))],
    conexion: Annotated[Connection, Depends(obtener_conexion)],
):
    return servicio.registrar(conexion, usuario, id_consulta, datos)


@enrutador.post("/{id_consulta}/anular", response_model=AnulacionRespuesta)
def anular_consulta(
    id_consulta: Annotated[int, Path(gt=0)],
    datos: SolicitudAnulacion,
    usuario: Annotated[UsuarioActual, Depends(requerir_roles(ROL_MEDICO))],
    conexion: Annotated[Connection, Depends(obtener_conexion)],
):
    return anulacion_servicio.anular(conexion, usuario, id_consulta, datos)
