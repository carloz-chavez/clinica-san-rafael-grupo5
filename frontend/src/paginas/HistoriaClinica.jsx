import React from 'react';
import Alerta from '../componentes/Alerta';

export default function HistoriaClinica({ usuario }) {
  return (
    <section className="mx-auto max-w-4xl px-4 py-8 sm:px-6 lg:px-8">
      <p className="text-xs font-bold uppercase tracking-[0.18em] text-sanrafael-700">Historia clínica electrónica</p>
      <h1 className="mt-1 text-3xl font-bold tracking-tight text-sanrafael-950">Historia clínica</h1>
      <p className="mt-2 text-sm text-slate-600">
        Espacio de trabajo para {usuario?.correo}. Aquí se consultará la línea de tiempo del paciente, sus consultas y recetas.
      </p>

      <Alerta tipo="info" className="mt-6">
        La integración de HU02 (registro de consulta) y HU03 (línea de tiempo) llega desde la rama de consultas.
        Los componentes de recetas (HU04) y anulación (HU10) ya están disponibles para conectarse en esta pantalla.
      </Alerta>

      <div className="mt-6 grid gap-4 sm:grid-cols-2">
        <article className="rounded-2xl border border-sanrafael-900/10 bg-white p-5 shadow-sm">
          <h2 className="font-bold text-sanrafael-950">Registro de atención</h2>
          <p className="mt-1 text-sm text-slate-500">Diagnóstico, observaciones y evolución de la consulta.</p>
        </article>
        <article className="rounded-2xl border border-sanrafael-900/10 bg-white p-5 shadow-sm">
          <h2 className="font-bold text-sanrafael-950">Recetas e indicaciones</h2>
          <p className="mt-1 text-sm text-slate-500">Registro aditivo de medicación e indicaciones médicas.</p>
        </article>
      </div>
    </section>
  );
}
