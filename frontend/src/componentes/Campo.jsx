import React, { useId } from 'react';

export default function Campo({
  etiqueta,
  id,
  error,
  ayuda,
  requerido = false,
  tipo = 'text',
  className = '',
  ...propiedades
}) {
  const generado = useId();
  const identificador = id || generado;
  const idError = `${identificador}-error`;
  const idAyuda = `${identificador}-ayuda`;
  const descrito = [error ? idError : null, ayuda ? idAyuda : null].filter(Boolean).join(' ') || undefined;

  return (
    <div className={className}>
      <label htmlFor={identificador} className="mb-1.5 block text-sm font-semibold text-sanrafael-900">
        {etiqueta}{requerido ? ' *' : ''}
      </label>
      <input
        id={identificador}
        type={tipo}
        aria-invalid={Boolean(error)}
        aria-describedby={descrito}
        className={`w-full rounded-lg border bg-white px-3 py-2.5 text-sm text-sanrafael-950 shadow-sm outline-none transition placeholder:text-slate-400 focus:border-sanrafael-500 focus:ring-2 focus:ring-sanrafael-200 disabled:bg-slate-100 ${error ? 'border-rose-400' : 'border-sanrafael-900/15'}`}
        {...propiedades}
      />
      {ayuda && <p id={idAyuda} className="mt-1.5 text-xs text-slate-500">{ayuda}</p>}
      {error && <p id={idError} role="alert" className="mt-1.5 text-xs font-medium text-rose-700">{error}</p>}
    </div>
  );
}
