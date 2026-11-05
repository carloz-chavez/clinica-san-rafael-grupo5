import React, { useEffect, useMemo, useRef, useState } from 'react';
import { crearClienteConsultas } from '../api/consultas';
import { crearClientePacientes } from '../api/pacientes';
import Alerta from '../componentes/Alerta';
import FormularioRecetas from '../componentes/recetas/FormularioRecetas';
import ModalAnulacion from '../componentes/recetas/ModalAnulacion';

const atencionVacia = { diagnostico_cie10: '', observaciones: '' };

function formatearFechaHora(valor) {
  const fecha = new Date(valor);
  if (Number.isNaN(fecha.getTime())) return valor;
  return fecha.toLocaleString('es-PE', { dateStyle: 'medium', timeStyle: 'short' });
}

// Pantalla del medico (HU02 y HU03) con los componentes HU04 y HU10 integrados.
export default function HistoriaClinica({ usuario, token, baseUrl = '', cliente, clientePacientes }) {
  const api = useMemo(() => cliente || crearClienteConsultas({ token, baseUrl }), [cliente, token, baseUrl]);
  const apiPacientes = useMemo(() => clientePacientes || crearClientePacientes({ token, baseUrl }), [clientePacientes, token, baseUrl]);
  const [busqueda, establecerBusqueda] = useState('');
  const [idPaciente, establecerIdPaciente] = useState(null);
  const [historia, establecerHistoria] = useState(null);
  const [cargando, establecerCargando] = useState(false);
  const [cargandoHistoria, establecerCargandoHistoria] = useState(false);
  const [error, establecerError] = useState('');
  const [mensaje, establecerMensaje] = useState('');
  const [atencion, establecerAtencion] = useState(atencionVacia);
  const [ocupadoAtencion, establecerOcupadoAtencion] = useState(false);
  const [recetasPara, establecerRecetasPara] = useState(null);
  const [anulando, establecerAnulando] = useState(null);
  const vigente = useRef(0);
  const controlador = useRef(null);

  const puedeAtender = usuario?.rol === 'MEDICO' && usuario?.id_medico != null;

  useEffect(() => () => { vigente.current += 1; controlador.current?.abort(); }, [api, apiPacientes]);

  async function cargarHistoria(id, solicitud, controladorLocal) {
    establecerCargandoHistoria(true);
    try {
      const respuesta = await api.obtenerHistoria(id, controladorLocal?.signal);
      if (solicitud !== vigente.current) return;
      establecerHistoria(respuesta);
      establecerError('');
    } catch (fallo) {
      if (solicitud !== vigente.current || fallo.name === 'AbortError') return;
      establecerError(fallo.message || 'No se pudo consultar la historia clínica.');
      establecerHistoria(null);
    } finally {
      if (solicitud === vigente.current) establecerCargandoHistoria(false);
    }
  }

  async function recargarHistoria() {
    if (!idPaciente) return;
    controlador.current?.abort();
    const controladorLocal = new AbortController();
    controlador.current = controladorLocal;
    await cargarHistoria(idPaciente, ++vigente.current, controladorLocal);
  }

  async function buscar(evento) {
    evento.preventDefault();
    if (cargando) return;
    if (!/^[0-9]{8}$/.test(busqueda)) {
      establecerError('Ingresa un DNI de exactamente ocho dígitos.');
      return;
    }
    controlador.current?.abort();
    const controladorLocal = new AbortController();
    controlador.current = controladorLocal;
    const solicitud = ++vigente.current;
    establecerCargando(true);
    establecerError('');
    establecerMensaje('');
    establecerHistoria(null);
    establecerIdPaciente(null);
    establecerRecetasPara(null);
    try {
      const fila = await apiPacientes.buscarPorDni(busqueda, controladorLocal.signal);
      if (solicitud !== vigente.current) return;
      establecerIdPaciente(fila.id_paciente);
      await cargarHistoria(fila.id_paciente, solicitud, controladorLocal);
    } catch (fallo) {
      if (solicitud !== vigente.current || fallo.name === 'AbortError') return;
      establecerError(fallo.message || 'No se pudo consultar el paciente.');
    } finally {
      if (solicitud === vigente.current) establecerCargando(false);
    }
  }

  async function registrarAtencion(evento) {
    evento.preventDefault();
    if (!puedeAtender || ocupadoAtencion || !idPaciente) return;
    establecerOcupadoAtencion(true);
    establecerError('');
    establecerMensaje('');
    try {
      const respuesta = await api.registrar({
        id_paciente: idPaciente,
        diagnostico_cie10: atencion.diagnostico_cie10.trim() || null,
        observaciones: atencion.observaciones.trim() || null,
      });
      establecerAtencion(atencionVacia);
      establecerMensaje(`Atención registrada correctamente (consulta ${respuesta.id_consulta}). Agrega recetas o indicaciones abajo.`);
      establecerRecetasPara(respuesta.id_consulta);
      await recargarHistoria();
    } catch (fallo) {
      establecerError(fallo.message || 'No se pudo registrar la atención.');
    } finally {
      establecerOcupadoAtencion(false);
    }
  }

  function alRegistrarRecetas() {
    establecerMensaje('Registro de recetas e indicaciones guardado correctamente.');
    recargarHistoria();
  }

  function alAnular() {
    establecerAnulando(null);
    establecerMensaje('Consulta anulada correctamente. Se conserva el registro original.');
    recargarHistoria();
  }

  if (usuario?.rol !== 'MEDICO') {
    return (
      <section className="mx-auto max-w-4xl px-4 py-8 sm:px-6 lg:px-8">
        <Alerta tipo="error">Esta pantalla es exclusiva del rol Médico.</Alerta>
      </section>
    );
  }

  const datos = historia?.paciente;

  return (
    <section className="mx-auto max-w-5xl px-4 py-8 sm:px-6 lg:px-8" aria-busy={cargando || cargandoHistoria}>
      <p className="text-xs font-bold uppercase tracking-[0.18em] text-sanrafael-700">Historia clínica electrónica</p>
      <h1 className="mt-1 text-3xl font-bold tracking-tight text-sanrafael-950">Historia clínica</h1>
      <p className="mt-2 text-sm text-slate-600">
        Consulta la línea de tiempo del paciente, registra atenciones y agrega recetas o anula consultas.
      </p>

      {!puedeAtender && (
        <Alerta tipo="aviso" className="mt-4">
          Estás usando un usuario simulado sin médico asociado: puedes consultar, pero para registrar atenciones,
          recetas o anular consultas necesitas iniciar sesión con tu cuenta de médico.
        </Alerta>
      )}

      <form onSubmit={buscar} className="mt-6 flex flex-wrap items-end gap-3" aria-label="Buscar paciente por DNI">
        <div>
          <label htmlFor="historia-dni" className="block text-sm font-medium text-slate-700">DNI del paciente</label>
          <input
            id="historia-dni"
            value={busqueda}
            onChange={evento => establecerBusqueda(evento.target.value)}
            inputMode="numeric"
            maxLength={8}
            placeholder="Ingresa 8 dígitos"
            className="mt-1 w-44 rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-sanrafael-600 focus:outline-none focus:ring-2 focus:ring-sanrafael-200"
            disabled={cargando}
          />
        </div>
        <button
          type="submit"
          disabled={cargando}
          className="rounded-lg bg-sanrafael-700 px-4 py-2 text-sm font-semibold text-white transition hover:bg-sanrafael-800 disabled:opacity-50"
        >
          {cargando ? 'Buscando…' : 'Consultar historia'}
        </button>
      </form>

      {error && <Alerta tipo="error" className="mt-4">{error}</Alerta>}
      {mensaje && <Alerta tipo="exito" className="mt-4">{mensaje}</Alerta>}

      {!historia && !error && (
        <div className="mt-6 rounded-2xl border border-dashed border-slate-300 bg-white p-8 text-center">
          <h2 className="font-bold text-sanrafael-950">Historia clínica unificada</h2>
          <p className="mt-1 text-sm text-slate-500">Busca un DNI para ver las atenciones del paciente en orden cronológico.</p>
        </div>
      )}

      {historia && datos && (
        <>
          <article className="mt-6 rounded-2xl border border-sanrafael-900/10 bg-white p-5 shadow-sm">
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <h2 className="text-lg font-bold text-sanrafael-950">{datos.nombres} {datos.apellidos}</h2>
              <span className="text-sm font-semibold text-slate-500">DNI {datos.dni}</span>
            </div>
            <dl className="mt-3 grid gap-x-6 gap-y-1 text-sm text-slate-600 sm:grid-cols-2">
              <div><dt className="inline font-semibold text-slate-700">Nacimiento: </dt><dd className="inline">{datos.fecha_nacimiento || '—'}</dd></div>
              <div><dt className="inline font-semibold text-slate-700">Sexo: </dt><dd className="inline">{datos.sexo || 'Sin especificar'}</dd></div>
              <div><dt className="inline font-semibold text-slate-700">Teléfono: </dt><dd className="inline">{datos.telefono || '—'}</dd></div>
              <div><dt className="inline font-semibold text-slate-700">Correo: </dt><dd className="inline">{datos.correo || '—'}</dd></div>
            </dl>
          </article>

          <form onSubmit={registrarAtencion} className="mt-4 rounded-2xl border border-sanrafael-900/10 bg-white p-5 shadow-sm" aria-label="Registrar atención médica">
            <h2 className="font-bold text-sanrafael-950">Registrar nueva atención</h2>
            <div className="mt-3 grid gap-3 sm:grid-cols-2">
              <div>
                <label htmlFor="atencion-cie10" className="block text-sm font-medium text-slate-700">Diagnóstico (CIE-10)</label>
                <input
                  id="atencion-cie10"
                  value={atencion.diagnostico_cie10}
                  onChange={evento => establecerAtencion(anterior => ({ ...anterior, diagnostico_cie10: evento.target.value }))}
                  maxLength={100}
                  placeholder="Ej. J06.9"
                  className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-sanrafael-600 focus:outline-none focus:ring-2 focus:ring-sanrafael-200"
                  disabled={ocupadoAtencion || !puedeAtender}
                />
              </div>
              <div className="sm:col-span-2">
                <label htmlFor="atencion-observaciones" className="block text-sm font-medium text-slate-700">Observaciones clínicas</label>
                <textarea
                  id="atencion-observaciones"
                  value={atencion.observaciones}
                  onChange={evento => establecerAtencion(anterior => ({ ...anterior, observaciones: evento.target.value }))}
                  rows={3}
                  className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-sanrafael-600 focus:outline-none focus:ring-2 focus:ring-sanrafael-200"
                  disabled={ocupadoAtencion || !puedeAtender}
                />
              </div>
            </div>
            <button
              type="submit"
              disabled={ocupadoAtencion || !puedeAtender}
              className="mt-3 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-emerald-700 disabled:opacity-50"
            >
              {ocupadoAtencion ? 'Registrando…' : 'Registrar atención'}
            </button>
          </form>

          <div className="mt-6 flex items-baseline justify-between">
            <h2 className="text-lg font-bold text-sanrafael-950">Línea de tiempo</h2>
            <span className="text-sm text-slate-500">{historia.total_consultas} atención(es) registradas</span>
          </div>

          {historia.consultas.length === 0 && (
            <div className="mt-3 rounded-2xl border border-dashed border-slate-300 bg-white p-6 text-center text-sm text-slate-500">
              El paciente aún no tiene atenciones registradas.
            </div>
          )}

          <ol className="mt-3 space-y-4">
            {historia.consultas.map(consulta => (
              <li key={consulta.id_consulta} className={`rounded-2xl border bg-white p-5 shadow-sm ${consulta.anulada ? 'border-rose-200 opacity-80' : 'border-sanrafael-900/10'}`}>
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <h3 className="font-bold text-sanrafael-950">{formatearFechaHora(consulta.fecha_hora)}</h3>
                  {consulta.anulada
                    ? <span className="rounded-full bg-rose-100 px-3 py-1 text-xs font-bold text-rose-700">Anulada</span>
                    : <span className="rounded-full bg-emerald-100 px-3 py-1 text-xs font-bold text-emerald-700">Vigente</span>}
                </div>
                <p className="mt-1 text-sm text-slate-600">
                  Dr. {consulta.medico_nombre_completo} · Colegiatura {consulta.medico_colegiatura}
                  {consulta.medico_especialidad ? ` · ${consulta.medico_especialidad}` : ''}
                </p>
                {consulta.diagnostico_cie10 && (
                  <p className="mt-2 text-sm"><span className="rounded bg-sky-100 px-2 py-0.5 text-xs font-bold text-sky-800">CIE-10</span> <span className="ml-1 font-medium text-slate-700">{consulta.diagnostico_cie10}</span></p>
                )}
                {consulta.observaciones && <p className="mt-2 text-sm text-slate-700">{consulta.observaciones}</p>}
                {consulta.anulada && (
                  <p className="mt-2 rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-800">
                    <b>Motivo de anulación:</b> {consulta.motivo_anulacion} · {formatearFechaHora(consulta.fecha_anulacion)}
                  </p>
                )}
                {consulta.recetas.length > 0 && (
                  <div className="mt-3">
                    <h4 className="text-xs font-bold uppercase tracking-wide text-slate-500">Recetas</h4>
                    <ul className="mt-1 space-y-1 text-sm text-slate-700">
                      {consulta.recetas.map(receta => (
                        <li key={receta.id_receta} className="rounded-lg bg-slate-50 px-3 py-2">
                          <b>{receta.medicamento}</b> · {receta.dosis} · {receta.frecuencia}{receta.duracion ? ` · ${receta.duracion}` : ''}
                          {receta.indicaciones && <span className="block text-slate-500">{receta.indicaciones}</span>}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                {consulta.indicaciones.length > 0 && (
                  <div className="mt-3">
                    <h4 className="text-xs font-bold uppercase tracking-wide text-slate-500">Indicaciones</h4>
                    <ul className="mt-1 list-disc space-y-1 pl-5 text-sm text-slate-700">
                      {consulta.indicaciones.map(indicacion => <li key={indicacion.id_indicacion}>{indicacion.descripcion}</li>)}
                    </ul>
                  </div>
                )}
                {!consulta.anulada && (
                  <div className="mt-4 flex flex-wrap gap-2">
                    <button
                      type="button"
                      onClick={() => establecerRecetasPara(anterior => (anterior === consulta.id_consulta ? null : consulta.id_consulta))}
                      className="rounded-lg border border-sanrafael-700 px-3 py-1.5 text-sm font-semibold text-sanrafael-700 transition hover:bg-sanrafael-50"
                    >
                      {recetasPara === consulta.id_consulta ? 'Cerrar recetas' : 'Recetas e indicaciones'}
                    </button>
                    {puedeAtender && usuario.id_medico === consulta.id_medico && (
                      <button
                        type="button"
                        onClick={() => establecerAnulando(consulta)}
                        className="rounded-lg border border-rose-300 px-3 py-1.5 text-sm font-semibold text-rose-700 transition hover:bg-rose-50"
                      >
                        Anular consulta
                      </button>
                    )}
                  </div>
                )}
                {recetasPara === consulta.id_consulta && !consulta.anulada && (
                  <div className="mt-4">
                    <FormularioRecetas usuario={usuario} consulta={consulta} token={token} baseUrl={baseUrl} alRegistrar={alRegistrarRecetas} />
                  </div>
                )}
              </li>
            ))}
          </ol>
        </>
      )}

      <ModalAnulacion
        abierto={Boolean(anulando)}
        consulta={anulando}
        usuario={usuario}
        token={token}
        baseUrl={baseUrl}
        alCerrar={() => establecerAnulando(null)}
        alAnular={alAnular}
      />
    </section>
  );
}
