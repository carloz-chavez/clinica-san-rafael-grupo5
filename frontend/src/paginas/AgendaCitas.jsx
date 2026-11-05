import React, { useEffect, useMemo, useState } from 'react';
import { crearClienteCitas } from '../api/citas';
import { crearClientePacientes } from '../api/pacientes';
import Alerta from '../componentes/Alerta';
import Boton from '../componentes/Boton';
import Campo from '../componentes/Campo';
import InsigniaEstado from '../componentes/InsigniaEstado';
import Modal from '../componentes/Modal';
import Selector from '../componentes/Selector';
import Tabla from '../componentes/Tabla';
import {
  fechaLocalISO,
  formatearFecha,
  formatearHora,
  mensajeErrorCita,
} from '../utilidades/agenda';

const HOY = fechaLocalISO();

const COLUMNAS = [
  { clave: 'hora', titulo: 'Hora', render: fila => formatearHora(fila.hora) },
  {
    clave: 'paciente',
    titulo: 'Paciente',
    render: fila => `${fila.apellidos_paciente}, ${fila.nombres_paciente}`,
  },
  {
    clave: 'medico',
    titulo: 'Médico',
    render: fila => `${fila.apellidos_medico}, ${fila.nombres_medico}`,
  },
  { clave: 'especialidad', titulo: 'Especialidad' },
  { clave: 'estado', titulo: 'Estado', render: fila => <InsigniaEstado estado={fila.estado} /> },
  { clave: 'motivo', titulo: 'Motivo' },
];

export default function AgendaCitas({ usuario, token, baseUrl = '', cliente, clientePacientes }) {
  const api = useMemo(() => cliente || crearClienteCitas({ token, baseUrl }), [cliente, token, baseUrl]);
  const apiPacientes = useMemo(
    () => clientePacientes || crearClientePacientes({ token, baseUrl }),
    [clientePacientes, token, baseUrl],
  );

  const [fecha, establecerFecha] = useState(HOY);
  const [catalogos, establecerCatalogos] = useState({ especialidades: [], medicos: [] });
  const [idEspecialidad, establecerIdEspecialidad] = useState('');
  const [idMedico, establecerIdMedico] = useState('');
  const [disponibilidad, establecerDisponibilidad] = useState({ fecha: HOY, medicos: [] });
  const [citas, establecerCitas] = useState([]);
  const [version, establecerVersion] = useState(0);
  const [cargando, establecerCargando] = useState(false);
  const [error, establecerError] = useState('');
  const [mensaje, establecerMensaje] = useState('');

  const [seleccion, establecerSeleccion] = useState(null);
  const [modalAbierto, establecerModalAbierto] = useState(false);
  const [dni, establecerDni] = useState('');
  const [paciente, establecerPaciente] = useState(null);
  const [buscando, establecerBuscando] = useState(false);
  const [errorPaciente, establecerErrorPaciente] = useState('');
  const [motivo, establecerMotivo] = useState('');
  const [errorReserva, establecerErrorReserva] = useState('');
  const [enviando, establecerEnviando] = useState(false);

  useEffect(() => {
    const control = new AbortController();
    let vigente = true;
    api.catalogos(control.signal)
      .then(datos => {
        if (vigente) establecerCatalogos(datos);
      })
      .catch(fallo => {
        if (!vigente || fallo?.name === 'AbortError') return;
        establecerError(fallo.message || 'No se pudieron cargar las especialidades y médicos.');
      });
    return () => {
      vigente = false;
      control.abort();
    };
  }, [api]);

  useEffect(() => {
    if (!fecha) return undefined;
    const control = new AbortController();
    let vigente = true;
    establecerCargando(true);
    establecerError('');
    Promise.all([
      api.disponibilidad({
        fecha,
        idEspecialidad: idEspecialidad || undefined,
        idMedico: idMedico || undefined,
      }, control.signal),
      api.listar(fecha, control.signal),
    ])
      .then(([nuevaDisponibilidad, nuevasCitas]) => {
        if (!vigente) return;
        establecerDisponibilidad(nuevaDisponibilidad);
        establecerCitas(nuevasCitas);
      })
      .catch(fallo => {
        if (!vigente || fallo?.name === 'AbortError') return;
        establecerError(fallo.message || 'No se pudo cargar la agenda para la fecha elegida.');
      })
      .finally(() => {
        if (vigente) establecerCargando(false);
      });
    return () => {
      vigente = false;
      control.abort();
    };
  }, [api, fecha, idEspecialidad, idMedico, version]);

  const medicosFiltrados = useMemo(
    () => catalogos.medicos.filter(medico => (
      !idEspecialidad || String(medico.id_especialidad) === String(idEspecialidad)
    )),
    [catalogos.medicos, idEspecialidad],
  );

  const opcionesEspecialidades = useMemo(() => [
    { valor: '', etiqueta: 'Todas las especialidades' },
    ...catalogos.especialidades.map(especialidad => ({
      valor: String(especialidad.id_especialidad),
      etiqueta: especialidad.nombre,
    })),
  ], [catalogos.especialidades]);

  const opcionesMedicos = useMemo(() => [
    { valor: '', etiqueta: 'Todos los médicos' },
    ...medicosFiltrados.map(medico => ({
      valor: String(medico.id_medico),
      etiqueta: `${medico.apellidos}, ${medico.nombres}`,
    })),
  ], [medicosFiltrados]);

  function cambiarEspecialidad(evento) {
    establecerIdEspecialidad(evento.target.value);
    establecerIdMedico('');
    establecerMensaje('');
  }

  function abrirReserva(medico, franja) {
    if (!franja.disponible) return;
    establecerSeleccion({
      id_medico: medico.id_medico,
      medico: `${medico.apellidos}, ${medico.nombres}`,
      especialidad: medico.especialidad,
      fecha,
      hora: franja.hora,
    });
    establecerDni('');
    establecerPaciente(null);
    establecerErrorPaciente('');
    establecerMotivo('');
    establecerErrorReserva('');
    establecerModalAbierto(true);
  }

  function cerrarModal() {
    if (enviando) return;
    establecerModalAbierto(false);
  }

  async function buscarPaciente() {
    establecerMensaje('');
    establecerErrorPaciente('');
    establecerPaciente(null);
    if (!/^[0-9]{8}$/.test(dni)) {
      establecerErrorPaciente('Ingresa un DNI de exactamente ocho dígitos.');
      return;
    }
    establecerBuscando(true);
    try {
      const encontrado = await apiPacientes.buscarPorDni(dni);
      establecerPaciente(encontrado);
    } catch (fallo) {
      if (fallo?.estado === 404) {
        establecerErrorPaciente('Paciente no encontrado. Regístralo primero en Gestión de pacientes.');
      } else if (fallo?.estado === 403) {
        establecerErrorPaciente('No tienes permiso para consultar pacientes.');
      } else {
        establecerErrorPaciente(fallo?.message || 'No se pudo buscar el paciente.');
      }
    } finally {
      establecerBuscando(false);
    }
  }

  async function confirmarReserva(evento) {
    evento.preventDefault();
    if (!seleccion || !paciente || !motivo.trim() || enviando) return;
    establecerEnviando(true);
    establecerErrorReserva('');
    try {
      const resultado = await api.registrar({
        id_paciente: paciente.id_paciente,
        id_medico: seleccion.id_medico,
        fecha: seleccion.fecha,
        hora: seleccion.hora,
        motivo: motivo.trim(),
      });
      establecerMensaje(`Cita registrada para ${resultado.nombres_paciente} ${resultado.apellidos_paciente} el ${formatearFecha(resultado.fecha)} a las ${formatearHora(resultado.hora)}.`);
      establecerModalAbierto(false);
      establecerVersion(actual => actual + 1);
    } catch (fallo) {
      establecerErrorReserva(mensajeErrorCita(fallo));
      if (fallo?.estado === 409) establecerVersion(actual => actual + 1);
    } finally {
      establecerEnviando(false);
    }
  }

  return (
    <section className="mx-auto max-w-6xl px-4 py-8 sm:px-6 lg:px-8" aria-busy={cargando}>
      <header className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.18em] text-sanrafael-700">Agenda médica</p>
          <h1 className="mt-1 text-3xl font-bold tracking-tight text-sanrafael-950">Reserva de citas</h1>
          <p className="mt-2 max-w-2xl text-sm text-slate-600">
            Consulta los turnos libres por especialidad, médico y fecha. Los turnos ocupados aparecen tachados.
          </p>
        </div>
        <p className="text-sm font-medium text-slate-500">
          Sesión: {usuario?.correo}
        </p>
      </header>

      <div className="mt-6 grid gap-4 rounded-2xl border border-sanrafael-900/10 bg-white p-4 shadow-sm sm:grid-cols-3 sm:p-5">
        <Campo
          etiqueta="Fecha"
          tipo="date"
          value={fecha}
          min={HOY}
          onChange={evento => establecerFecha(evento.target.value)}
        />
        <Selector
          etiqueta="Especialidad"
          value={idEspecialidad}
          onChange={cambiarEspecialidad}
          opciones={opcionesEspecialidades}
        />
        <Selector
          etiqueta="Médico"
          value={idMedico}
          onChange={evento => establecerIdMedico(evento.target.value)}
          opciones={opcionesMedicos}
          disabled={medicosFiltrados.length === 0}
        />
      </div>

      <div className="mt-4 grid gap-3">
        {error && <Alerta tipo="error">{error}</Alerta>}
        {mensaje && <Alerta tipo="exito">{mensaje}</Alerta>}
        {cargando && <p className="text-sm font-medium text-sanrafael-700" role="status">Actualizando agenda…</p>}
      </div>

      <div className="mt-6 grid gap-6 xl:grid-cols-[1.25fr_.75fr]">
        <section aria-labelledby="titulo-disponibilidad" className="rounded-2xl border border-sanrafael-900/10 bg-white p-4 shadow-sm sm:p-5">
          <header className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 id="titulo-disponibilidad" className="text-lg font-bold text-sanrafael-950">Disponibilidad</h2>
              <p className="text-sm text-slate-500">{formatearFecha(fecha)} · turnos de 30 minutos</p>
            </div>
            <div className="flex items-center gap-4 text-xs text-slate-500">
              <span className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-full bg-sanrafael-500" /> Libre</span>
              <span className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-full bg-slate-300" /> Ocupado</span>
            </div>
          </header>

          <div className="mt-4 grid gap-4">
            {disponibilidad.medicos.length === 0 && (
              <p className="rounded-lg bg-sanrafael-50 px-4 py-6 text-center text-sm text-slate-600">
                No hay médicos activos con los filtros seleccionados.
              </p>
            )}
            {disponibilidad.medicos.map(medico => (
              <article key={medico.id_medico} className="rounded-xl border border-sanrafael-900/10 p-4">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div>
                    <h3 className="font-bold text-sanrafael-950">{medico.apellidos}, {medico.nombres}</h3>
                    <p className="text-xs font-semibold uppercase tracking-wide text-sanrafael-600">{medico.especialidad}</p>
                  </div>
                  {medico.franjas.length > 0 && (
                    <span className="text-xs font-medium text-slate-500">
                      {medico.franjas.filter(franja => franja.disponible).length} libres
                    </span>
                  )}
                </div>
                {medico.franjas.length === 0 ? (
                  <p className="mt-3 text-sm text-slate-500">Sin horario de atención para esta fecha.</p>
                ) : (
                  <div className="mt-3 grid grid-cols-3 gap-2 sm:grid-cols-4">
                    {medico.franjas.map(franja => (
                      <button
                        key={franja.hora}
                        type="button"
                        disabled={!franja.disponible}
                        onClick={() => abrirReserva(medico, franja)}
                        aria-label={`${formatearHora(franja.hora)} con ${medico.apellidos}, ${medico.nombres}: ${franja.disponible ? 'disponible' : 'ocupado'}`}
                        className={franja.disponible
                          ? 'rounded-lg border border-sanrafael-200 bg-sanrafael-50 px-2 py-2.5 text-sm font-semibold text-sanrafael-800 transition hover:border-sanrafael-500 hover:bg-sanrafael-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sanrafael-600'
                          : 'cursor-not-allowed rounded-lg border border-slate-200 bg-slate-50 px-2 py-2.5 text-sm font-semibold text-slate-400 line-through'}
                      >
                        {formatearHora(franja.hora)}
                      </button>
                    ))}
                  </div>
                )}
              </article>
            ))}
          </div>
        </section>

        <section aria-labelledby="titulo-citas" className="rounded-2xl border border-sanrafael-900/10 bg-white p-4 shadow-sm sm:p-5">
          <header>
            <h2 id="titulo-citas" className="text-lg font-bold text-sanrafael-950">Citas del día</h2>
            <p className="text-sm text-slate-500">{formatearFecha(fecha)} · {citas.length} registrada(s)</p>
          </header>
          <Tabla
            columnas={COLUMNAS}
            filas={citas}
            vacio="No hay citas registradas para esta fecha."
            className="mt-4"
          />
        </section>
      </div>

      <Modal
        abierto={modalAbierto}
        titulo="Registrar cita"
        alCerrar={cerrarModal}
      >
        {seleccion && (
          <form onSubmit={confirmarReserva} className="grid gap-4" aria-busy={enviando}>
            <div className="rounded-lg bg-sanrafael-50 px-4 py-3 text-sm text-sanrafael-900">
              <p className="font-semibold">{seleccion.medico}</p>
              <p className="text-sanrafael-700">{seleccion.especialidad}</p>
              <p className="mt-1 font-medium">
                {formatearFecha(seleccion.fecha)} a las {formatearHora(seleccion.hora)}
              </p>
            </div>

            <div>
              <label htmlFor="agenda-dni" className="mb-1.5 block text-sm font-semibold text-sanrafael-900">
                DNI del paciente *
              </label>
              <div className="flex gap-2">
                <input
                  id="agenda-dni"
                  value={dni}
                  onChange={evento => {
                    establecerDni(evento.target.value);
                    establecerPaciente(null);
                    establecerErrorPaciente('');
                  }}
                  inputMode="numeric"
                  maxLength={8}
                  placeholder="8 dígitos"
                  className="min-w-0 flex-1 rounded-lg border border-sanrafael-900/15 bg-white px-3 py-2.5 text-sm outline-none focus:border-sanrafael-500 focus:ring-2 focus:ring-sanrafael-200"
                />
                <Boton variante="secundario" onClick={buscarPaciente} disabled={buscando}>
                  {buscando ? 'Buscando…' : 'Buscar'}
                </Boton>
              </div>
            </div>

            {paciente && (
              <Alerta tipo="exito">
                Paciente: {paciente.apellidos}, {paciente.nombres} (DNI {paciente.dni})
              </Alerta>
            )}
            {errorPaciente && <Alerta tipo="error">{errorPaciente}</Alerta>}

            <Campo
              etiqueta="Motivo de la cita"
              value={motivo}
              onChange={evento => establecerMotivo(evento.target.value)}
              maxLength={200}
              placeholder="Motivo de la consulta"
              required
              disabled={enviando}
            />

            {errorReserva && <Alerta tipo="error">{errorReserva}</Alerta>}

            <div className="flex justify-end gap-3 border-t border-sanrafael-900/10 pt-4">
              <Boton variante="secundario" onClick={cerrarModal} disabled={enviando}>Cancelar</Boton>
              <Boton type="submit" disabled={!paciente || !motivo.trim() || enviando}>
                {enviando ? 'Registrando…' : 'Confirmar cita'}
              </Boton>
            </div>
          </form>
        )}
      </Modal>
    </section>
  );
}
