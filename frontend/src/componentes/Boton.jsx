import React from 'react';

const ESTILOS = {
  primario: 'bg-sanrafael-800 text-white hover:bg-sanrafael-900 focus-visible:outline-sanrafael-700',
  secundario: 'border border-sanrafael-900/15 bg-white text-sanrafael-900 hover:bg-sanrafael-50 focus-visible:outline-sanrafael-500',
  peligro: 'bg-rose-700 text-white hover:bg-rose-800 focus-visible:outline-rose-600',
  texto: 'text-sanrafael-800 hover:bg-sanrafael-50 focus-visible:outline-sanrafael-500',
};

export default function Boton({
  children,
  variante = 'primario',
  type = 'button',
  className = '',
  ...propiedades
}) {
  return (
    <button
      type={type}
      className={`inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2.5 text-sm font-semibold transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 disabled:cursor-not-allowed disabled:opacity-60 ${ESTILOS[variante] || ESTILOS.primario} ${className}`}
      {...propiedades}
    >
      {children}
    </button>
  );
}
