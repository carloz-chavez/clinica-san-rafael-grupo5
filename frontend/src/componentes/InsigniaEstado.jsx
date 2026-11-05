import React from 'react';

const ESTILOS = {
  registrada: 'bg-amber-100 text-amber-800 ring-amber-200',
  confirmada: 'bg-emerald-100 text-emerald-800 ring-emerald-200',
  cancelada: 'bg-rose-100 text-rose-800 ring-rose-200',
  atendida: 'bg-sky-100 text-sky-800 ring-sky-200',
};

const ETIQUETAS = {
  registrada: 'Registrada',
  confirmada: 'Confirmada',
  cancelada: 'Cancelada',
  atendida: 'Atendida',
};

export default function InsigniaEstado({ estado }) {
  return (
    <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ring-inset ${ESTILOS[estado] || 'bg-slate-100 text-slate-700 ring-slate-200'}`}>
      {ETIQUETAS[estado] || estado || 'Sin estado'}
    </span>
  );
}
