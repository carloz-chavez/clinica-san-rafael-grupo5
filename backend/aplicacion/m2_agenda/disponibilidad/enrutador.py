"""HTTP HU06: catalogos y disponibilidad para agendar citas."""
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from psycopg import Connection

from aplicacion.m2_agenda.disponibilidad import servicio
from aplicacion.m2_agenda.disponibilidad.esquemas import RespuestaCatalogos, RespuestaDisponibilidad
from aplicacion.nucleo.base_datos import obtener_conexion
from aplicacion.nucleo.constantes import ROL_ADMINISTRADOR, ROL_ADMISION
from aplicacion.nucleo.dependencias import UsuarioActual, requerir_roles

enrutador = APIRouter(prefix="/citas", tags=["Disponibilidad"])

_Agenda = Annotated[UsuarioActual, Depends(requerir_roles(ROL_ADMISION, ROL_ADMINISTRADOR))]
_Conexion = Annotated[Connection, Depends(obtener_conexion)]


@enrutador.get("/catalogos", response_model=RespuestaCatalogos)
def listar_catalogos(usuario: _Agenda, conexion: _Conexion):
    """Especialidades y medicos activos para armar los filtros de la agenda."""
    return servicio.obtener_catalogos(conexion)


@enrutador.get("/disponibilidad", response_model=RespuestaDisponibilidad)
def consultar_disponibilidad(
    usuario: _Agenda,
    conexion: _Conexion,
    fecha: Annotated[date, Query()],
    id_especialidad: Annotated[int | None, Query(gt=0)] = None,
    id_medico: Annotated[int | None, Query(gt=0)] = None,
):
    """Turnos de 30 minutos marcados como disponibles u ocupados para una fecha."""
    return servicio.obtener_disponibilidad(conexion, fecha, id_especialidad, id_medico)
