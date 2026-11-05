import React, { useId } from 'react';

export default function Selector({
  etiqueta,
  id,
  opciones = [],
  error,
  className = '',
  ...propiedades
}) {
  const generado = useId();
  const identificador = id || generado;
  const idError = `${identificador}-error`;

  return (
    <div className={className}>
      <label htmlFor={identificador} className="mb-1.5 block text-sm font-semibold text-sanrafael-900">
        {etiqueta}
      </label>
      <select
        id={identificador}
        aria-invalid={Boolean(error)}
        aria-describedby={error ? idError : undefined}
        className={`w-full rounded-lg border bg-white px-3 py-2.5 text-sm text-sanrafael-950 shadow-sm outline-none transition focus:border-sanrafael-500 focus:ring-2 focus:ring-sanrafael-200 disabled:bg-slate-100 ${error ? 'border-rose-400' : 'border-sanrafael-900/15'}`}
        {...propiedades}
      >
        {opciones.map(opcion => (
          <option key={opcion.valor} value={opcion.valor}>{opcion.etiqueta}</option>
        ))}
      </select>
      {error && <p id={idError} role="alert" className="mt-1.5 text-xs font-medium text-rose-700">{error}</p>}
    </div>
  );
}
