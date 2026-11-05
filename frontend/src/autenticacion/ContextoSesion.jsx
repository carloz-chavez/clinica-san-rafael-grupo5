import React, { createContext, useCallback, useContext, useMemo, useState } from 'react';
import { crearClienteAutenticacion } from '../api/autenticacion';
import { normalizarSesion } from '../utilidades/sesion';

const CLAVE_SESION = 'sanrafael.sesion';
const ContextoSesion = createContext(null);

function leerSesionGuardada() {
  try {
    return normalizarSesion(JSON.parse(sessionStorage.getItem(CLAVE_SESION)));
  } catch {
    return null;
  }
}

function guardarSesion(sesion) {
  try {
    if (sesion) sessionStorage.setItem(CLAVE_SESION, JSON.stringify(sesion));
    else sessionStorage.removeItem(CLAVE_SESION);
  } catch {
    // Sin almacenamiento la sesion sigue viva en memoria.
  }
}

export function ProveedorSesion({ children, baseUrl = '', solicitar = fetch }) {
  const [sesion, establecerSesion] = useState(leerSesionGuardada);

  const iniciarSesion = useCallback(async (correo, contrasena) => {
    const cliente = crearClienteAutenticacion({ baseUrl, solicitar });
    const respuesta = await cliente.iniciarSesion(correo, contrasena);
    const nueva = { token: respuesta.token_acceso, usuario: respuesta.usuario };
    guardarSesion(nueva);
    establecerSesion(nueva);
    return respuesta.usuario;
  }, [baseUrl, solicitar]);

  const cerrarSesion = useCallback(() => {
    guardarSesion(null);
    establecerSesion(null);
  }, []);

  const entrarSimulado = useCallback((rol) => {
    const nueva = {
      token: null,
      usuario: {
        id_usuario: 0,
        correo: `simulado.${String(rol).toLowerCase()}@sanrafael.local`,
        rol,
        id_medico: null,
      },
    };
    guardarSesion(nueva);
    establecerSesion(nueva);
    return nueva.usuario;
  }, []);

  const valor = useMemo(() => ({
    usuario: sesion?.usuario ?? null,
    token: sesion?.token ?? null,
    iniciarSesion,
    cerrarSesion,
    entrarSimulado,
  }), [sesion, iniciarSesion, cerrarSesion, entrarSimulado]);

  return <ContextoSesion.Provider value={valor}>{children}</ContextoSesion.Provider>;
}

export function useSesion() {
  const contexto = useContext(ContextoSesion);
  if (!contexto) throw new Error('useSesion debe usarse dentro de ProveedorSesion.');
  return contexto;
}
