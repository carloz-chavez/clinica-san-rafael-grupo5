"""HTTP HU01: control de roles, validacion y delegacion al servicio."""
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query
from psycopg import Connection

from aplicacion.m1_hce.pacientes import servicio
from aplicacion.m1_hce.pacientes.esquemas import DatosPaciente, PacienteRespuesta
from aplicacion.nucleo.base_datos import obtener_conexion
from aplicacion.nucleo.constantes import ROL_ADMINISTRADOR, ROL_ADMISION, ROL_MEDICO
from aplicacion.nucleo.dependencias import UsuarioActual, requerir_roles

enrutador = APIRouter(prefix="/pacientes", tags=["Pacientes"])
_Gestion = Annotated[UsuarioActual, Depends(requerir_roles(ROL_ADMISION, ROL_ADMINISTRADOR))]
_Consulta = Annotated[UsuarioActual, Depends(requerir_roles(ROL_ADMISION, ROL_ADMINISTRADOR, ROL_MEDICO))]
_Conexion = Annotated[Connection, Depends(obtener_conexion)]
_Identificador = Annotated[int, Path(gt=0)]


@enrutador.post("", response_model=PacienteRespuesta, status_code=201)
def registrar_paciente(datos: DatosPaciente, usuario: _Gestion, conexion: _Conexion):
    return servicio.registrar(conexion, usuario, datos)


@enrutador.put("/{id_paciente}", response_model=PacienteRespuesta)
def actualizar_paciente(id_paciente: _Identificador, datos: DatosPaciente, usuario: _Gestion, conexion: _Conexion):
    return servicio.actualizar(conexion, usuario, id_paciente, datos)


@enrutador.get("", response_model=PacienteRespuesta)
def buscar_paciente(usuario: _Consulta, conexion: _Conexion, dni: Annotated[str, Query(min_length=8, max_length=8, pattern=r"^[0-9]{8}$")]):
    return servicio.consultar_por_dni(conexion, usuario, dni)


@enrutador.get("/{id_paciente}", response_model=PacienteRespuesta)
def consultar_paciente(id_paciente: _Identificador, usuario: _Consulta, conexion: _Conexion):
    return servicio.consultar_por_id(conexion, usuario, id_paciente)
