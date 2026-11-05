import React from 'react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { useSesion } from '../autenticacion/ContextoSesion';
import { etiquetaRol } from '../utilidades/sesion';
import Boton from '../componentes/Boton';

const ENLACES_POR_ROL = {
  ADMISION: [
    { ruta: '/pacientes', texto: 'Pacientes' },
    { ruta: '/agenda', texto: 'Agenda' },
  ],
  ADMINISTRADOR: [
    { ruta: '/pacientes', texto: 'Pacientes' },
    { ruta: '/agenda', texto: 'Agenda' },
  ],
  MEDICO: [
    { ruta: '/historia', texto: 'Historia clínica' },
  ],
};

function claseEnlace({ isActive }) {
  return [
    'flex items-center rounded-lg px-4 py-2.5 text-sm font-semibold transition',
    isActive
      ? 'bg-white/15 text-white shadow-sm'
      : 'text-sanrafael-100/80 hover:bg-white/10 hover:text-white',
  ].join(' ');
}

export default function Diseno() {
  const { usuario, cerrarSesion } = useSesion();
  const navegar = useNavigate();
  const enlaces = ENLACES_POR_ROL[usuario.rol] || [];

  function salir() {
    cerrarSesion();
    navegar('/iniciar-sesion', { replace: true });
  }

  return (
    <div className="min-h-screen bg-[#f4f7f5] lg:grid lg:grid-cols-[17rem_1fr]">
      <aside className="bg-sanrafael-950 text-white lg:sticky lg:top-0 lg:h-screen lg:p-6">
        <div className="flex items-center justify-between gap-4 px-4 py-4 lg:block lg:px-0 lg:py-0">
          <div className="flex items-center gap-3">
            <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-sanrafael-500 text-base font-black tracking-tight">
              SR
            </span>
            <div>
              <p className="text-sm font-bold leading-tight">Clínica San Rafael</p>
              <p className="text-xs text-sanrafael-200/80">Gestión clínica</p>
            </div>
          </div>
          <nav className="hidden lg:mt-8 lg:flex lg:flex-col lg:gap-1" aria-label="Menú principal">
            {enlaces.map(enlace => (
              <NavLink key={enlace.ruta} to={enlace.ruta} className={claseEnlace}>
                {enlace.texto}
              </NavLink>
            ))}
          </nav>
        </div>

        <nav className="flex gap-1 overflow-x-auto px-4 pb-4 lg:hidden" aria-label="Menú principal">
          {enlaces.map(enlace => (
            <NavLink
              key={enlace.ruta}
              to={enlace.ruta}
              className={({ isActive }) => `${claseEnlace({ isActive })} whitespace-nowrap`}
            >
              {enlace.texto}
            </NavLink>
          ))}
        </nav>

        <div className="hidden border-t border-white/10 pt-5 lg:mt-6 lg:block">
          <p className="truncate text-sm font-semibold">{usuario.correo}</p>
          <p className="mt-0.5 text-xs text-sanrafael-200/80">{etiquetaRol(usuario.rol)}</p>
          <Boton
            variante="secundario"
            onClick={salir}
            className="mt-4 w-full border-white/20 bg-white/5 text-white hover:bg-white/10"
          >
            Cerrar sesión
          </Boton>
        </div>
      </aside>

      <div className="flex min-h-screen flex-col">
        <header className="flex items-center justify-between gap-4 border-b border-sanrafael-900/10 bg-white/80 px-4 py-3 backdrop-blur lg:px-8">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-sanrafael-700">
              {etiquetaRol(usuario.rol)}
            </p>
            <p className="text-sm text-slate-500">Sistema de historia clínica y agenda</p>
          </div>
          <div className="flex items-center gap-3 lg:hidden">
            <span className="max-w-[11rem] truncate text-xs text-slate-500">{usuario.correo}</span>
            <Boton variante="secundario" onClick={salir} className="px-3 py-2">Salir</Boton>
          </div>
        </header>
        <main className="flex-1">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
