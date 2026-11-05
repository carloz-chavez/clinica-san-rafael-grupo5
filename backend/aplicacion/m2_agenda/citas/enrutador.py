"""HTTP HU07/HU08: registro y listado de citas del dia."""
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from psycopg import Connection

from aplicacion.m2_agenda.citas import servicio
from aplicacion.m2_agenda.citas.esquemas import CitaDetalle, SolicitudCita
from aplicacion.nucleo.base_datos import obtener_conexion
from aplicacion.nucleo.constantes import ROL_ADMINISTRADOR, ROL_ADMISION
from aplicacion.nucleo.dependencias import UsuarioActual, requerir_roles

enrutador = APIRouter(prefix="/citas", tags=["Citas"])

_Agenda = Annotated[UsuarioActual, Depends(requerir_roles(ROL_ADMISION, ROL_ADMINISTRADOR))]
_Conexion = Annotated[Connection, Depends(obtener_conexion)]


@enrutador.post("", response_model=CitaDetalle, status_code=status.HTTP_201_CREATED)
def registrar_cita(datos: SolicitudCita, usuario: _Agenda, conexion: _Conexion):
    """Registra la cita y devuelve 409 si el horario ya esta ocupado."""
    return servicio.registrar(conexion, usuario, datos)


@enrutador.get("", response_model=list[CitaDetalle])
def listar_citas(
    usuario: _Agenda,
    conexion: _Conexion,
    fecha: Annotated[date, Query()],
):
    """Citas de una fecha ordenadas por hora y medico."""
    return servicio.listar_por_fecha(conexion, fecha)
