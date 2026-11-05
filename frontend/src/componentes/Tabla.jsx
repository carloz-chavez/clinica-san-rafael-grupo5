import React from 'react';

export default function Tabla({ columnas = [], filas = [], vacio = 'Sin registros.', className = '' }) {
  return (
    <div className={`overflow-x-auto rounded-xl border border-sanrafael-900/10 bg-white ${className}`}>
      <table className="min-w-full divide-y divide-sanrafael-900/10 text-left text-sm">
        <thead className="bg-sanrafael-50">
          <tr>
            {columnas.map(columna => (
              <th key={columna.clave} scope="col" className="whitespace-nowrap px-4 py-3 text-xs font-bold uppercase tracking-wide text-sanrafael-800">
                {columna.titulo}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-sanrafael-900/5">
          {filas.length === 0 && (
            <tr>
              <td colSpan={Math.max(columnas.length, 1)} className="px-4 py-8 text-center text-sm text-slate-500">
                {vacio}
              </td>
            </tr>
          )}
          {filas.map((fila, indice) => (
            <tr key={fila.id_cita ?? fila.id ?? indice} className="hover:bg-sanrafael-50/60">
              {columnas.map(columna => (
                <td key={columna.clave} className="px-4 py-3 align-top text-slate-700">
                  {columna.render ? columna.render(fila) : fila[columna.clave]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
