import React from 'react';
import { Link } from 'react-router-dom';
import { useSesion } from '../autenticacion/ContextoSesion';
import { rutaInicioPorRol } from '../utilidades/sesion';

export default function NoEncontrado() {
  const { usuario } = useSesion();
  const destino = usuario ? rutaInicioPorRol(usuario.rol) : '/iniciar-sesion';

  return (
    <section className="mx-auto flex max-w-2xl flex-col items-center px-4 py-20 text-center">
      <p className="text-sm font-bold uppercase tracking-[0.2em] text-sanrafael-600">Error 404</p>
      <h1 className="mt-2 text-3xl font-bold text-sanrafael-950">Página no encontrada</h1>
      <p className="mt-2 text-sm text-slate-500">La ruta solicitada no existe o no está disponible para tu rol.</p>
      <Link
        to={destino}
        className="mt-6 rounded-lg bg-sanrafael-800 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-sanrafael-900"
      >
        Volver al inicio
      </Link>
    </section>
  );
}
