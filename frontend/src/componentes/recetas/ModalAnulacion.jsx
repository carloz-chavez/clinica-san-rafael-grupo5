import React, { useEffect, useId, useMemo, useRef, useState } from 'react';
import { crearClienteAnulaciones } from '../../api/anulaciones';
import './ModalAnulacion.css';

// HU02/G1 controla abierto, consulta y usuario. alAnular recibe los metadatos
// para actualizar el estado de la consulta y deshabilitar el formulario de C5.
export default function ModalAnulacion({ abierto, consulta, usuario, cliente, token, baseUrl = '', alCerrar, alAnular }) {
  const api = useMemo(() => cliente || crearClienteAnulaciones({ token, baseUrl }), [cliente, token, baseUrl]);
  const dialogo = useRef(null);
  const enviando = useRef(false);
  const version = useRef(0);
  const id = useId();
  const [motivo, establecerMotivo] = useState('');
  const [ocupado, establecerOcupado] = useState(false);
  const [error, establecerError] = useState('');
  const [terminado, establecerTerminado] = useState(false);
  const permitido = usuario?.rol === 'MEDICO' && usuario?.id_medico != null && usuario.id_medico === consulta?.id_medico;

  useEffect(() => {
    version.current += 1;
    enviando.current = false;
    establecerMotivo('');
    establecerError('');
    establecerOcupado(false);
    establecerTerminado(false);
    const elemento = dialogo.current;
    if (abierto && elemento && !elemento.open) elemento.showModal();
    if (!abierto && elemento?.open) elemento.close();
    return () => { version.current += 1; };
  }, [abierto, consulta?.id_consulta, consulta?.id_paciente, consulta?.id_medico, consulta?.anulada,
    usuario?.id_usuario, usuario?.rol, usuario?.id_medico, api]);

  async function confirmar(evento) {
    evento.preventDefault();
    if (enviando.current || !permitido || !consulta?.id_consulta || consulta.anulada || terminado || !motivo.trim()) return;
    enviando.current = true;
    establecerOcupado(true);
    establecerError('');
    const solicitud = version.current;
    let resultado;
    try {
      resultado = await api.anular(consulta.id_consulta, { motivo_anulacion: motivo.trim() });
    } catch (fallo) {
      if (solicitud === version.current) {
        establecerError(fallo.message || 'No se pudo conectar con el servidor.');
        if (fallo.codigo === 'CONSULTA_ANULADA') establecerTerminado(true);
      }
      return;
    } finally {
      if (solicitud === version.current) {
        enviando.current = false;
        establecerOcupado(false);
      }
    }
    if (solicitud !== version.current) return;
    establecerTerminado(true);
    establecerMotivo('');
    alAnular?.(resultado);
  }

  return <dialog ref={dialogo} className="hu10-modal" aria-labelledby={`${id}-titulo`} aria-describedby={`${id}-ayuda`}
    onCancel={evento => { evento.preventDefault(); if (!enviando.current) alCerrar?.(); }}>
    <form onSubmit={confirmar} aria-busy={ocupado}>
      <h2 id={`${id}-titulo`}>Anular consulta médica</h2>
      <p id={`${id}-ayuda`}>La consulta, sus recetas e indicaciones se conservarán en el historial. Confirma el motivo de anulación.</p>
      {!permitido && <p role="alert">Solo el médico responsable puede anular esta consulta.</p>}
      {consulta?.anulada && <p role="status">La consulta ya está anulada.</p>}
      {error && <p role="alert">{error}</p>}
      {terminado && !error && <p role="status">Consulta anulada correctamente.</p>}
      <fieldset disabled={ocupado || !permitido || !consulta?.id_consulta || consulta.anulada || terminado}>
        <label htmlFor={`${id}-motivo`}>Motivo de anulación *</label>
        <textarea id={`${id}-motivo`} autoFocus required maxLength={200} value={motivo}
          onChange={evento => establecerMotivo(evento.target.value)} />
        <button type="submit" disabled={!motivo.trim()}>{ocupado ? 'Anulando…' : 'Confirmar anulación'}</button>
      </fieldset>
      <button type="button" disabled={ocupado} onClick={() => alCerrar?.()}>{terminado ? 'Cerrar' : 'Cancelar'}</button>
    </form>
  </dialog>;
}
