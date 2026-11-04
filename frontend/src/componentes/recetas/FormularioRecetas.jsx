import React, { useEffect, useMemo, useRef, useState } from 'react';
import { crearClienteRecetas } from '../../api/recetas';
import './FormularioRecetas.css';

const recetaVacia = { medicamento: '', dosis: '', frecuencia: '', duracion: '', indicaciones: '' };

// G1/HU02 proporciona usuario y consulta: id_consulta, id_paciente, id_medico, anulada.
// Puede inyectar cliente.registrar(idConsulta, datos) para reutilizar su API base.
// No configura rutas, sesion, layout ni componentes compartidos.
export default function FormularioRecetas({ usuario, consulta, cliente, token, baseUrl = '', alRegistrar }) {
  const api = useMemo(() => cliente || crearClienteRecetas({ token, baseUrl }), [cliente, token, baseUrl]);
  const [recetas, establecerRecetas] = useState([]);
  const [indicaciones, establecerIndicaciones] = useState([]);
  const [ocupado, establecerOcupado] = useState(false);
  const [error, establecerError] = useState('');
  const [errores, establecerErrores] = useState({});
  const [mensaje, establecerMensaje] = useState('');
  const secuencia = useRef(0);
  const version = useRef(0);
  const enviando = useRef(false);
  const puedeRegistrar = usuario?.rol === 'MEDICO' && usuario?.id_medico != null && usuario.id_medico === consulta?.id_medico;

  useEffect(() => {
    version.current += 1;
    enviando.current = false;
    establecerRecetas([]);
    establecerIndicaciones([]);
    establecerOcupado(false);
    establecerError('');
    establecerErrores({});
    establecerMensaje('');
    return () => { version.current += 1; };
  }, [consulta?.id_consulta, consulta?.id_paciente, consulta?.id_medico, consulta?.anulada, usuario?.id_usuario, usuario?.rol, usuario?.id_medico, api]);

  function agregar(tipo) {
    establecerMensaje('');
    establecerErrores({});
    const clave = ++secuencia.current;
    if (tipo === 'recetas') establecerRecetas(anteriores => [...anteriores, { clave, ...recetaVacia }]);
    else establecerIndicaciones(anteriores => [...anteriores, { clave, descripcion: '' }]);
  }

  function cambiar(tipo, clave, nombre, valor) {
    const establecer = tipo === 'recetas' ? establecerRecetas : establecerIndicaciones;
    establecer(anterior => anterior.map(fila => fila.clave === clave ? { ...fila, [nombre]: valor } : fila));
    establecerMensaje('');
  }

  function quitar(tipo, clave) {
    const establecer = tipo === 'recetas' ? establecerRecetas : establecerIndicaciones;
    establecer(anterior => anterior.filter(fila => fila.clave !== clave));
    establecerErrores({});
    establecerMensaje('');
  }

  async function guardar(evento) {
    evento.preventDefault();
    if (enviando.current || !puedeRegistrar || consulta.anulada || (!recetas.length && !indicaciones.length)) return;
    enviando.current = true;
    const solicitud = version.current;
    establecerOcupado(true);
    establecerError('');
    establecerErrores({});
    establecerMensaje('');
    const datos = {
      recetas: recetas.map(({ clave, ...fila }) => ({ ...fila, duracion: fila.duracion || null, indicaciones: fila.indicaciones || null })),
      indicaciones: indicaciones.map(({ clave, ...fila }) => fila),
    };
    let resultado;
    try {
      resultado = await api.registrar(consulta.id_consulta, datos);
    } catch (fallo) {
      if (solicitud === version.current) {
        establecerError(fallo.message || 'No se pudo conectar con el servidor.');
        establecerErrores(Object.fromEntries((fallo.campos || []).map(campo => [campo.campo, campo.mensaje])));
      }
      return;
    } finally {
      if (solicitud === version.current) {
        enviando.current = false;
        establecerOcupado(false);
      }
    }
    if (solicitud !== version.current) return;
    establecerRecetas([]);
    establecerIndicaciones([]);
    establecerMensaje('Registro guardado correctamente.');
    alRegistrar?.(resultado);
  }

  function campoReceta(fila, indice, nombre, etiqueta, longitud, obligatorio = false) {
    const ruta = `recetas.${indice}.${nombre}`;
    const id = `hu04-receta-${fila.clave}-${nombre}`;
    return <div key={nombre}>
      <label htmlFor={id}>{etiqueta}{obligatorio ? ' *' : ''}</label>
      <input id={id} value={fila[nombre]} onChange={e => cambiar('recetas', fila.clave, nombre, e.target.value)} maxLength={longitud} required={obligatorio} aria-invalid={Boolean(errores[ruta])} aria-describedby={errores[ruta] ? `${id}-error` : undefined}/>
      {errores[ruta] && <span id={`${id}-error`} className="hu04-error-campo">{errores[ruta]}</span>}
    </div>;
  }

  if (!consulta?.id_consulta) return <section className="formulario-recetas"><p role="status">Selecciona una consulta médica para registrar recetas o indicaciones.</p></section>;
  if (!puedeRegistrar) return <section className="formulario-recetas"><p role="alert">Solo el médico responsable puede registrar recetas e indicaciones.</p></section>;
  if (consulta.anulada) return <section className="formulario-recetas"><p role="alert">La consulta está anulada y no permite nuevos registros.</p></section>;

  return <section className="formulario-recetas" aria-labelledby="hu04-titulo" aria-busy={ocupado}>
    <header><h2 id="hu04-titulo">Recetas e indicaciones</h2><p>Agrega la medicación y las indicaciones correspondientes a esta consulta.</p></header>
    {error && <div role="alert" className="hu04-error">{error}</div>}
    {mensaje && <div role="status" className="hu04-exito">{mensaje}</div>}
    <form onSubmit={guardar} aria-label="Registrar recetas e indicaciones">
      <fieldset disabled={ocupado}>
        <div className="hu04-seccion"><h3>Recetas médicas</h3><button type="button" onClick={() => agregar('recetas')}>Agregar receta</button></div>
        {!recetas.length && <p className="hu04-ayuda">Puedes registrar una receta, una indicación independiente o ambas.</p>}
        {recetas.map((fila, indice) => <div className="hu04-borrador" key={fila.clave}>
          <div className="hu04-subtitulo"><h4>Receta {indice + 1}</h4><button type="button" onClick={() => quitar('recetas', fila.clave)}>Quitar del borrador</button></div>
          <div className="hu04-campos">
            {campoReceta(fila, indice, 'medicamento', 'Medicamento', 150, true)}
            {campoReceta(fila, indice, 'dosis', 'Dosis', 100, true)}
            {campoReceta(fila, indice, 'frecuencia', 'Frecuencia', 100, true)}
            {campoReceta(fila, indice, 'duracion', 'Duración', 100)}
          </div>
          <label htmlFor={`hu04-detalle-${fila.clave}`}>Indicaciones de la receta</label>
          <textarea id={`hu04-detalle-${fila.clave}`} value={fila.indicaciones} onChange={e => cambiar('recetas', fila.clave, 'indicaciones', e.target.value)} aria-invalid={Boolean(errores[`recetas.${indice}.indicaciones`])}/>
        </div>)}
        <div className="hu04-seccion"><h3>Indicaciones independientes</h3><button type="button" onClick={() => agregar('indicaciones')}>Agregar indicación</button></div>
        {indicaciones.map((fila, indice) => {
          const ruta = `indicaciones.${indice}.descripcion`;
          return <div className="hu04-borrador" key={fila.clave}>
            <div className="hu04-subtitulo"><h4>Indicación {indice + 1}</h4><button type="button" onClick={() => quitar('indicaciones', fila.clave)}>Quitar del borrador</button></div>
            <label htmlFor={`hu04-indicacion-${fila.clave}`}>Descripción *</label>
            <textarea id={`hu04-indicacion-${fila.clave}`} value={fila.descripcion} onChange={e => cambiar('indicaciones', fila.clave, 'descripcion', e.target.value)} required aria-invalid={Boolean(errores[ruta])} aria-describedby={errores[ruta] ? `hu04-error-${fila.clave}` : undefined}/>
            {errores[ruta] && <span id={`hu04-error-${fila.clave}`} className="hu04-error-campo">{errores[ruta]}</span>}
          </div>;
        })}
      </fieldset>
      <footer><span>Los campos con * son obligatorios. Se agregarán nuevos registros al historial.</span><button className="hu04-guardar" type="submit" disabled={ocupado || (!recetas.length && !indicaciones.length)}>{ocupado ? 'Guardando…' : 'Guardar registro'}</button></footer>
    </form>
  </section>;
}
