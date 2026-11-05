import React from 'react';

const ESTILOS = {
  error: 'border-rose-200 bg-rose-50 text-rose-800',
  exito: 'border-emerald-200 bg-emerald-50 text-emerald-800',
  info: 'border-sky-200 bg-sky-50 text-sky-800',
  aviso: 'border-amber-200 bg-amber-50 text-amber-900',
};

export default function Alerta({ tipo = 'info', children, className = '' }) {
  const esError = tipo === 'error';
  return (
    <div
      role={esError ? 'alert' : 'status'}
      className={`rounded-lg border px-4 py-3 text-sm font-medium ${ESTILOS[tipo] || ESTILOS.info} ${className}`}
    >
      {children}
    </div>
  );
}
