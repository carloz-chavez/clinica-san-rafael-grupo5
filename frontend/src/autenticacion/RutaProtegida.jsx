import React from 'react';
import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useSesion } from './ContextoSesion';
import { rutaInicioPorRol } from '../utilidades/sesion';

export default function RutaProtegida({ roles, children }) {
  const { usuario } = useSesion();
  const ubicacion = useLocation();

  if (!usuario) {
    return <Navigate to="/iniciar-sesion" state={{ desde: ubicacion.pathname }} replace />;
  }

  if (roles && !roles.includes(usuario.rol)) {
    return <Navigate to={rutaInicioPorRol(usuario.rol)} replace />;
  }

  return children ?? <Outlet />;
}
