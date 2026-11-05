import React from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import RutaProtegida from './autenticacion/RutaProtegida';
import { useSesion } from './autenticacion/ContextoSesion';
import Diseno from './diseno/Diseno';
import AgendaCitas from './paginas/AgendaCitas';
import GestionPacientes from './paginas/GestionPacientes';
import HistoriaClinica from './paginas/HistoriaClinica';
import InicioSesion from './paginas/InicioSesion';
import NoEncontrado from './paginas/NoEncontrado';
import { rutaInicioPorRol } from './utilidades/sesion';

const BASE_URL_API = import.meta.env.VITE_API_URL || '';

function Inicio() {
  const { usuario } = useSesion();
  return <Navigate to={rutaInicioPorRol(usuario.rol)} replace />;
}

function PaginaPacientes() {
  const { usuario, token } = useSesion();
  return <GestionPacientes usuario={usuario} token={token} baseUrl={BASE_URL_API} />;
}

function PaginaAgenda() {
  const { usuario, token } = useSesion();
  return <AgendaCitas usuario={usuario} token={token} baseUrl={BASE_URL_API} />;
}

function PaginaHistoria() {
  const { usuario } = useSesion();
  return <HistoriaClinica usuario={usuario} />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/iniciar-sesion" element={<InicioSesion />} />
      <Route element={<RutaProtegida><Diseno /></RutaProtegida>}>
        <Route index element={<Inicio />} />
        <Route
          path="pacientes"
          element={<RutaProtegida roles={['ADMISION', 'ADMINISTRADOR']}><PaginaPacientes /></RutaProtegida>}
        />
        <Route
          path="agenda"
          element={<RutaProtegida roles={['ADMISION', 'ADMINISTRADOR']}><PaginaAgenda /></RutaProtegida>}
        />
        <Route
          path="historia"
          element={<RutaProtegida roles={['MEDICO']}><PaginaHistoria /></RutaProtegida>}
        />
        <Route path="*" element={<NoEncontrado />} />
      </Route>
    </Routes>
  );
}
