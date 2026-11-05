import React, { useEffect, useId, useRef } from 'react';

export default function Modal({ abierto, titulo, alCerrar, children, pie, className = '' }) {
  const dialogo = useRef(null);
  const id = useId();

  useEffect(() => {
    const elemento = dialogo.current;
    if (!elemento) return;
    if (abierto && !elemento.open) elemento.showModal();
    if (!abierto && elemento.open) elemento.close();
  }, [abierto]);

  return (
    <dialog
      ref={dialogo}
      aria-labelledby={`${id}-titulo`}
      onCancel={evento => {
        evento.preventDefault();
        alCerrar?.();
      }}
      className={`w-[calc(100%-2rem)] max-w-lg rounded-2xl border border-sanrafael-900/10 p-0 text-sanrafael-950 shadow-2xl backdrop:bg-slate-950/50 ${className}`}
    >
      <div className="flex max-h-[85vh] flex-col">
        <header className="flex items-start justify-between gap-4 border-b border-sanrafael-900/10 px-5 py-4">
          <h2 id={`${id}-titulo`} className="text-lg font-bold">{titulo}</h2>
          <button
            type="button"
            onClick={alCerrar}
            aria-label="Cerrar"
            className="rounded-md px-2 py-1 text-xl leading-none text-slate-500 transition hover:bg-slate-100 hover:text-slate-800"
          >
            ×
          </button>
        </header>
        <div className="overflow-y-auto px-5 py-4">{children}</div>
        {pie && <footer className="border-t border-sanrafael-900/10 px-5 py-4">{pie}</footer>}
      </div>
    </dialog>
  );
}
