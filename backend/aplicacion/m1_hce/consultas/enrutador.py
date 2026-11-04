"""Enrutador HTTP para consultas medicas e historia clinica (HU02 y HU03)."""
from fastapi import APIRouter, Depends, status
from psycopg import Connection

from aplicacion.m1_hce.consultas import servicio
from aplicacion.m1_hce.consultas.esquemas import (
    RespuestaConsulta,
    RespuestaHistoriaClinica,
    SolicitudRegistrarConsulta,
)
from aplicacion.nucleo.base_datos import obtener_conexion
from aplicacion.nucleo.constantes import ROL_MEDICO
from aplicacion.nucleo.dependencias import UsuarioActual, requerir_roles

enrutador = APIRouter(tags=["Consultas e Historia Clinica"])


@enrutador.post(
    "/consultas",
    response_model=RespuestaConsulta,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar atencion medica (HU02)",
)
def registrar_consulta(
    solicitud: SolicitudRegistrarConsulta,
    usuario: UsuarioActual = Depends(requerir_roles(ROL_MEDICO)),
    conexion: Connection = Depends(obtener_conexion),
):
    """Permite al medico autenticado registrar la atencion clinica de un paciente."""
    return servicio.registrar_consulta(conexion, solicitud, usuario)


@enrutador.get(
    "/consultas/{id_consulta}",
    response_model=RespuestaConsulta,
    summary="Obtener consulta medica por ID",
)
def obtener_consulta(
    id_consulta: int,
    usuario: UsuarioActual = Depends(requerir_roles(ROL_MEDICO)),
    conexion: Connection = Depends(obtener_conexion),
):
    """Recupera la informacion basica de una consulta medica individual."""
    return servicio.obtener_consulta_por_id(conexion, id_consulta, usuario)


@enrutador.get(
    "/pacientes/{id_paciente}/historia",
    response_model=RespuestaHistoriaClinica,
    summary="Consultar historia clinica unificada (HU03)",
)
@enrutador.get(
    "/consultas/pacientes/{id_paciente}/historia",
    response_model=RespuestaHistoriaClinica,
    include_in_schema=False,
)
def obtener_historia_clinica(
    id_paciente: int,
    usuario: UsuarioActual = Depends(requerir_roles(ROL_MEDICO)),
    conexion: Connection = Depends(obtener_conexion),
):
    """Retorna la historia clinica electronica completa del paciente en orden cronologico."""
    return servicio.obtener_historia_clinica(conexion, id_paciente, usuario)
