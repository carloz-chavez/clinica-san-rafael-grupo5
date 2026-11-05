// HU06/HU07: catalogos, disponibilidad, registro y listado de citas.
import { solicitarJson } from './cliente.js';

function cadenaConsulta(parametros) {
  const busqueda = new URLSearchParams();
  Object.entries(parametros).forEach(([clave, valor]) => {
    if (valor !== undefined && valor !== null && valor !== '') busqueda.set(clave, valor);
  });
  const texto = busqueda.toString();
  return texto ? `?${texto}` : '';
}

export function crearClienteCitas({ token, baseUrl = '', solicitar = fetch } = {}) {
  const comunes = { token, baseUrl, solicitar };
  return {
    catalogos: signal => solicitarJson('/citas/catalogos', { ...comunes, signal }),
    disponibilidad: ({ fecha, idEspecialidad, idMedico } = {}, signal) => solicitarJson(
      `/citas/disponibilidad${cadenaConsulta({
        fecha,
        id_especialidad: idEspecialidad,
        id_medico: idMedico,
      })}`,
      { ...comunes, signal },
    ),
    listar: (fecha, signal) => solicitarJson(`/citas${cadenaConsulta({ fecha })}`, { ...comunes, signal }),
    registrar: datos => solicitarJson('/citas', { ...comunes, metodo: 'POST', datos }),
  };
}
