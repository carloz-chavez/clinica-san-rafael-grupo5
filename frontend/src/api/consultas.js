// Cliente de HU02 y HU03. G1 entrega la sesion y la URL; no persiste datos clinicos ni tokens.
export function crearClienteConsultas({ token, baseUrl = '', solicitar = fetch }) {
  async function enviar(ruta, { metodo = 'GET', datos, signal } = {}) {
    const respuesta = await solicitar(`${baseUrl.replace(/\/$/, '')}${ruta}`, {
      method: metodo,
      signal,
      cache: 'no-store',
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(datos ? { 'Content-Type': 'application/json' } : {}),
      },
      ...(datos ? { body: JSON.stringify(datos) } : {}),
    });
    const cuerpo = await respuesta.json().catch(() => ({}));
    if (!respuesta.ok) {
      const error = new Error(cuerpo.detalle || 'No se pudo completar la operacion.');
      error.codigo = cuerpo.codigo;
      error.estado = respuesta.status;
      error.campos = cuerpo.campos || [];
      throw error;
    }
    return cuerpo;
  }
  return {
    registrar: datos => enviar('/consultas', { metodo: 'POST', datos }),
    obtenerPorId: (idConsulta, signal) => enviar(`/consultas/${encodeURIComponent(idConsulta)}`, { signal }),
    obtenerHistoria: (idPaciente, signal) => enviar(`/pacientes/${encodeURIComponent(idPaciente)}/historia`, { signal }),
  };
}
