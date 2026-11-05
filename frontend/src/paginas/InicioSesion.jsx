import React, { useState } from 'react';
import { Navigate, useNavigate } from 'react-router-dom';
import { useSesion } from '../autenticacion/ContextoSesion';
import Alerta from '../componentes/Alerta';
import Boton from '../componentes/Boton';
import Campo from '../componentes/Campo';
import Selector from '../componentes/Selector';
import { rutaInicioPorRol } from '../utilidades/sesion';

const MODO_SIMULADO = import.meta.env.VITE_AUTENTICACION_SIMULADA === 'true';

export default function InicioSesion() {
  const { usuario, iniciarSesion, entrarSimulado } = useSesion();
  const navegar = useNavigate();
  const [correo, establecerCorreo] = useState('');
  const [contrasena, establecerContrasena] = useState('');
  const [rolSimulado, establecerRolSimulado] = useState('ADMISION');
  const [ocupado, establecerOcupado] = useState(false);
  const [error, establecerError] = useState('');

  if (usuario) return <Navigate to={rutaInicioPorRol(usuario.rol)} replace />;

  async function enviar(evento) {
    evento.preventDefault();
    establecerError('');
    establecerOcupado(true);
    try {
      const autenticado = await iniciarSesion(correo.trim(), contrasena);
      navegar(rutaInicioPorRol(autenticado.rol), { replace: true });
    } catch (fallo) {
      establecerError(fallo?.estado === 401
        ? 'Correo o contraseña incorrectos.'
        : fallo?.message || 'No se pudo iniciar sesión.');
    } finally {
      establecerOcupado(false);
    }
  }

  function entrarComoSimulado() {
    const simulado = entrarSimulado(rolSimulado);
    navegar(rutaInicioPorRol(simulado.rol), { replace: true });
  }

  return (
    <div className="grid min-h-screen bg-[#f4f7f5] lg:grid-cols-[1.05fr_.95fr]">
      <aside className="relative hidden overflow-hidden bg-sanrafael-950 px-12 py-16 text-white lg:flex lg:flex-col lg:justify-between">
        <div className="absolute -right-24 -top-24 h-80 w-80 rounded-full bg-sanrafael-600/30 blur-3xl" />
        <div className="absolute -bottom-32 -left-10 h-96 w-96 rounded-full bg-sanrafael-500/20 blur-3xl" />
        <div className="relative">
          <span className="flex h-14 w-14 items-center justify-center rounded-2xl bg-sanrafael-500 text-xl font-black">
            SR
          </span>
          <p className="mt-8 text-sm font-semibold uppercase tracking-[0.24em] text-sanrafael-200">
            Clínica San Rafael S.A.C.
          </p>
          <h1 className="mt-4 max-w-md text-4xl font-bold leading-tight">
            Historia clínica y agenda en un solo lugar.
          </h1>
          <p className="mt-5 max-w-md text-base leading-relaxed text-sanrafael-100/80">
            Accede con tu cuenta institucional para gestionar pacientes, consultas y citas de forma segura.
          </p>
        </div>
        <div className="relative grid grid-cols-2 gap-4 text-sm">
          <div className="rounded-xl border border-white/10 bg-white/5 p-4">
            <p className="font-semibold text-white">Historia clínica</p>
            <p className="mt-1 text-sanrafael-100/70">Registro cronológico y auditoría.</p>
          </div>
          <div className="rounded-xl border border-white/10 bg-white/5 p-4">
            <p className="font-semibold text-white">Agenda médica</p>
            <p className="mt-1 text-sanrafael-100/70">Disponibilidad y reservas sin cruces.</p>
          </div>
        </div>
      </aside>

      <main className="flex items-center justify-center px-4 py-12 sm:px-8">
        <section className="w-full max-w-md rounded-2xl border border-sanrafael-900/10 bg-white p-7 shadow-tarjeta sm:p-9">
          <div className="lg:hidden">
            <span className="flex h-12 w-12 items-center justify-center rounded-xl bg-sanrafael-800 text-base font-black text-white">
              SR
            </span>
          </div>
          <h2 className="mt-6 text-2xl font-bold tracking-tight text-sanrafael-950 lg:mt-0">Iniciar sesión</h2>
          <p className="mt-2 text-sm text-slate-500">Usa una cuenta ficticia de demostración del sprint.</p>

          {error && <Alerta tipo="error" className="mt-5">{error}</Alerta>}

          <form onSubmit={enviar} className="mt-6 grid gap-4" aria-busy={ocupado}>
            <Campo
              etiqueta="Correo electrónico"
              tipo="email"
              value={correo}
              onChange={evento => establecerCorreo(evento.target.value)}
              placeholder="usuario@sanrafael.invalid"
              autoComplete="username"
              required
              disabled={ocupado}
            />
            <Campo
              etiqueta="Contraseña"
              tipo="password"
              value={contrasena}
              onChange={evento => establecerContrasena(evento.target.value)}
              placeholder="Tu contraseña"
              autoComplete="current-password"
              required
              disabled={ocupado}
            />
            <Boton type="submit" disabled={ocupado} className="mt-1 w-full">
              {ocupado ? 'Ingresando…' : 'Ingresar'}
            </Boton>
          </form>

          {MODO_SIMULADO && (
            <div className="mt-6 border-t border-sanrafael-900/10 pt-5">
              <p className="text-xs font-semibold uppercase tracking-wide text-amber-700">Modo simulado de desarrollo</p>
              <p className="mt-1 text-xs text-slate-500">
                Solo úsalo con <code>AUTENTICACION_SIMULADA=true</code> en el backend.
              </p>
              <div className="mt-3 grid gap-3">
                <Selector
                  etiqueta="Rol simulado"
                  value={rolSimulado}
                  onChange={evento => establecerRolSimulado(evento.target.value)}
                  opciones={[
                    { valor: 'ADMISION', etiqueta: 'Admisión' },
                    { valor: 'MEDICO', etiqueta: 'Médico' },
                    { valor: 'ADMINISTRADOR', etiqueta: 'Administrador' },
                  ]}
                />
                <Boton variante="secundario" onClick={entrarComoSimulado}>Entrar en modo simulado</Boton>
              </div>
            </div>
          )}

          <p className="mt-6 text-center text-xs leading-relaxed text-slate-400">
            Todos los datos de este entorno son ficticios y exclusivos para pruebas.
          </p>
        </section>
      </main>
    </div>
  );
}
