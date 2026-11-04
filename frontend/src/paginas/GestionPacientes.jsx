import React, { useEffect, useMemo, useRef, useState } from 'react';
import { crearClientePacientes } from '../api/pacientes';
import './GestionPacientes.css';

const vacio = { dni: '', nombres: '', apellidos: '', fecha_nacimiento: '', sexo: '', telefono: '', correo: '', direccion: '' };
const campos = [
  ['dni', 'DNI', 'text', 8, true], ['fecha_nacimiento', 'Fecha de nacimiento', 'date', null, true],
  ['nombres', 'Nombres', 'text', 100, true], ['apellidos', 'Apellidos', 'text', 100, true],
  ['telefono', 'Teléfono', 'tel', 20], ['correo', 'Correo electrónico', 'email', 150],
];

// Componente integrable en las rutas/sesion de G1; no implementa login ni otro modulo.
export default function GestionPacientes({ usuario, token, baseUrl = '', cliente }) {
  const api = useMemo(() => cliente || crearClientePacientes({ token, baseUrl }), [cliente, token, baseUrl]);
  const [busqueda, establecerBusqueda] = useState('');
  const [datos, establecerDatos] = useState(vacio);
  const [paciente, establecerPaciente] = useState(null);
  const [abierto, establecerAbierto] = useState(false);
  const [ocupado, establecerOcupado] = useState(false);
  const [mensaje, establecerMensaje] = useState('');
  const [error, establecerError] = useState('');
  const [errores, establecerErrores] = useState({});
  const vigente = useRef(0);
  const controlador = useRef(null);
  const puedeGestionar = ['ADMISION', 'ADMINISTRADOR'].includes(usuario?.rol);
  const puedeConsultar = puedeGestionar || usuario?.rol === 'MEDICO';

  useEffect(() => {
    vigente.current += 1;
    controlador.current?.abort();
    establecerPaciente(null);
    establecerBusqueda('');
    establecerDatos(vacio);
    establecerAbierto(false);
    establecerOcupado(false);
    establecerError('');
    establecerMensaje('');
    establecerErrores({});
    return () => { vigente.current += 1; controlador.current?.abort(); };
  }, [usuario?.id_usuario, usuario?.rol, usuario?.id_medico, api]);

  function informarError(fallo) {
    establecerError(fallo.message || 'No se pudo conectar con el servidor. Intenta nuevamente.');
    establecerErrores(Object.fromEntries((fallo.campos || []).map(campo => [campo.campo, campo.mensaje])));
  }

  function mostrarPaciente(fila) {
    establecerPaciente(fila);
    establecerDatos(Object.fromEntries(Object.keys(vacio).map(campo => [campo, fila[campo] ?? ''])));
    establecerAbierto(true);
  }

  async function buscar(evento) {
    evento.preventDefault();
    establecerMensaje('');
    establecerError('');
    establecerErrores({});
    if (!/^[0-9]{8}$/.test(busqueda)) {
      establecerError('Ingresa un DNI de exactamente ocho dígitos.');
      return;
    }
    const solicitud = ++vigente.current;
    controlador.current?.abort();
    controlador.current = new AbortController();
    establecerOcupado(true);
    establecerAbierto(false);
    establecerPaciente(null);
    establecerDatos(vacio);
    try {
      const fila = await api.buscarPorDni(busqueda, controlador.current.signal);
      if (solicitud === vigente.current) mostrarPaciente(fila);
    } catch (fallo) {
      if (solicitud !== vigente.current || fallo.name === 'AbortError') return;
      informarError(fallo);
      if (fallo.estado === 404 && puedeGestionar) establecerDatos({ ...vacio, dni: busqueda });
    } finally {
      if (solicitud === vigente.current) establecerOcupado(false);
    }
  }

  function nuevo() {
    establecerPaciente(null);
    establecerDatos({ ...vacio, dni: /^[0-9]{8}$/.test(busqueda) ? busqueda : '' });
    establecerErrores({});
    establecerError('');
    establecerMensaje('');
    establecerAbierto(true);
  }

  async function guardar(evento) {
    evento.preventDefault();
    if (!puedeGestionar || ocupado) return;
    const solicitud = ++vigente.current;
    establecerOcupado(true);
    establecerError('');
    establecerErrores({});
    establecerMensaje('');
    const cuerpo = { ...datos, sexo: datos.sexo || null, telefono: datos.telefono || null, correo: datos.correo || null, direccion: datos.direccion || null };
    try {
      const fila = paciente ? await api.actualizar(paciente.id_paciente, cuerpo) : await api.registrar(cuerpo);
      if (solicitud !== vigente.current) return;
      mostrarPaciente(fila);
      establecerBusqueda(fila.dni);
      establecerMensaje(paciente ? 'Datos del paciente actualizados correctamente.' : 'Paciente registrado correctamente.');
    } catch (fallo) {
      if (solicitud === vigente.current) informarError(fallo);
    } finally {
      if (solicitud === vigente.current) establecerOcupado(false);
    }
  }

  function cambiar(evento) {
    establecerDatos(anterior => ({ ...anterior, [evento.target.name]: evento.target.value }));
    establecerMensaje('');
  }

  if (!puedeConsultar) return <section className="gestion-pacientes"><p role="alert">No tienes permiso para gestionar pacientes. Inicia sesión con una cuenta autorizada.</p></section>;

  return <section className="gestion-pacientes" aria-labelledby="titulo-pacientes" aria-busy={ocupado}>
    <header className="pacientes-cabecera">
      <div><h1 id="titulo-pacientes">Gestión de pacientes</h1><p>Busca por DNI para consultar o actualizar los datos de un paciente.</p></div>
      {puedeGestionar && <button type="button" className="pacientes-primario" onClick={nuevo} disabled={ocupado}>Nuevo paciente</button>}
    </header>
    <form onSubmit={buscar} className="pacientes-busqueda" aria-label="Buscar paciente">
      <label htmlFor="buscar-dni">DNI del paciente</label>
      <div><input id="buscar-dni" value={busqueda} onChange={e => establecerBusqueda(e.target.value)} inputMode="numeric" maxLength={8} placeholder="Ingresa 8 dígitos" required disabled={ocupado}/><button type="submit" disabled={ocupado}>{ocupado ? 'Procesando…' : 'Buscar paciente'}</button></div>
    </form>
    {error && <div className="pacientes-error" role="alert">{error}</div>}
    {mensaje && <div className="pacientes-exito" role="status">{mensaje}</div>}
    {!abierto && <div className="pacientes-vacio"><h2>Datos del paciente</h2><p>Busca un DNI para consultar sus datos.{puedeGestionar ? ' Si aún no está registrado, selecciona Nuevo paciente.' : ''}</p></div>}
    {abierto && <form onSubmit={guardar} className="pacientes-formulario" aria-label="Datos del paciente">
      <div className="pacientes-subtitulo"><h2>{paciente ? 'Datos del paciente' : 'Registrar paciente'}</h2><span>{puedeGestionar ? 'Los campos con * son obligatorios.' : 'Consulta de datos · Solo lectura'}</span></div>
      <fieldset disabled={ocupado || !puedeGestionar}>
        <div className="pacientes-campos">
          {campos.map(([nombre, etiqueta, tipo, longitud, obligatorio]) => <div key={nombre}>
            <label htmlFor={`paciente-${nombre}`}>{etiqueta}{obligatorio ? ' *' : ''}</label>
            <input id={`paciente-${nombre}`} name={nombre} type={tipo} value={datos[nombre]} onChange={cambiar} maxLength={longitud || undefined} required={obligatorio} pattern={nombre === 'dni' ? '[0-9]{8}' : undefined} inputMode={nombre === 'dni' ? 'numeric' : undefined} min={tipo === 'date' ? '1900-01-01' : undefined} max={tipo === 'date' ? '2100-12-31' : undefined} aria-invalid={Boolean(errores[nombre])} aria-describedby={errores[nombre] ? `error-${nombre}` : undefined}/>
            {errores[nombre] && <span id={`error-${nombre}`} className="pacientes-error-campo">{errores[nombre]}</span>}
          </div>)}
          <div><label htmlFor="paciente-sexo">Sexo</label><select id="paciente-sexo" name="sexo" value={datos.sexo} onChange={cambiar}><option value="">Sin especificar</option><option value="F">Femenino</option><option value="M">Masculino</option></select>{errores.sexo && <span className="pacientes-error-campo">{errores.sexo}</span>}</div>
          <div><label htmlFor="paciente-direccion">Dirección</label><input id="paciente-direccion" name="direccion" maxLength={250} value={datos.direccion} onChange={cambiar}/>{errores.direccion && <span className="pacientes-error-campo">{errores.direccion}</span>}</div>
        </div>
      </fieldset>
      {puedeGestionar && <footer><span>Los cambios se guardan de forma segura en el sistema.</span><button type="submit" className="pacientes-primario" disabled={ocupado}>{ocupado ? 'Guardando…' : paciente ? 'Guardar cambios' : 'Registrar paciente'}</button></footer>}
    </form>}
  </section>;
}
