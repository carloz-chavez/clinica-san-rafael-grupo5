"""Reglas de disponibilidad (HU06): horario de atencion menos citas activas.

La disponibilidad es informativa: no reserva el turno. La reserva real la
resuelve la base de datos al registrar la cita (HU07/HU08).
"""
from datetime import date, datetime, time, timedelta

from psycopg import Connection

from aplicacion.m2_agenda.disponibilidad import repositorio
from aplicacion.m2_agenda.disponibilidad.esquemas import (
    FranjaDisponibilidad,
    MedicoDisponibilidad,
    MedicoItem,
    RespuestaCatalogos,
    RespuestaDisponibilidad,
)

BLOQUE_MINUTOS = 30


def generar_franjas(hora_inicio: time, hora_fin: time) -> list[time]:
    """Divide un intervalo en turnos completos de 30 minutos."""
    base = datetime.combine(date(2000, 1, 1), hora_inicio)
    limite = datetime.combine(date(2000, 1, 1), hora_fin)
    paso = timedelta(minutes=BLOQUE_MINUTOS)
    franjas: list[time] = []
    while base + paso <= limite:
        franjas.append(base.time())
        base += paso
    return franjas


def _ya_paso(fecha: date, hora: time, ahora: datetime) -> bool:
    if fecha < ahora.date():
        return True
    return fecha == ahora.date() and hora <= ahora.time()


def construir_franjas(
    horarios: list[dict],
    horas_ocupadas: set[time],
    fecha: date,
    ahora: datetime | None = None,
) -> list[FranjaDisponibilidad]:
    """Combina los intervalos del medico con las citas ya tomadas."""
    momento = ahora or datetime.now()
    horas: set[time] = set()
    for horario in horarios:
        horas.update(generar_franjas(horario["hora_inicio"], horario["hora_fin"]))
    return [
        FranjaDisponibilidad(
            hora=hora,
            disponible=hora not in horas_ocupadas and not _ya_paso(fecha, hora, momento),
        )
        for hora in sorted(horas)
    ]


def obtener_catalogos(conexion: Connection) -> RespuestaCatalogos:
    return RespuestaCatalogos(
        especialidades=repositorio.listar_especialidades(conexion),
        medicos=repositorio.listar_medicos(conexion),
    )


def obtener_disponibilidad(
    conexion: Connection,
    fecha: date,
    id_especialidad: int | None = None,
    id_medico: int | None = None,
    ahora: datetime | None = None,
) -> RespuestaDisponibilidad:
    medicos = repositorio.listar_medicos(conexion, id_especialidad, id_medico)
    if not medicos:
        return RespuestaDisponibilidad(fecha=fecha, medicos=[])

    ids = [medico["id_medico"] for medico in medicos]
    horarios = repositorio.listar_horarios(conexion, ids, fecha.isoweekday())
    ocupadas = repositorio.listar_citas_ocupadas(conexion, ids, fecha)

    horarios_por_medico: dict[int, list[dict]] = {id_: [] for id_ in ids}
    for horario in horarios:
        horarios_por_medico[horario["id_medico"]].append(horario)

    ocupadas_por_medico: dict[int, set[time]] = {id_: set() for id_ in ids}
    for cita in ocupadas:
        ocupadas_por_medico[cita["id_medico"]].add(cita["hora"])

    resultado = [
        MedicoDisponibilidad(
            **MedicoItem.model_validate(medico).model_dump(),
            franjas=construir_franjas(
                horarios_por_medico[medico["id_medico"]],
                ocupadas_por_medico[medico["id_medico"]],
                fecha,
                ahora,
            ),
        )
        for medico in medicos
    ]
    return RespuestaDisponibilidad(fecha=fecha, medicos=resultado)
