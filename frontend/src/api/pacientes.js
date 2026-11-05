// Cliente limitado a HU01. G1 entrega la sesion y la URL; no persiste datos ni tokens.
export function crearClientePacientes({ token, baseUrl = '', solicitar = fetch }) {
  async function enviar(ruta, { metodo = 'GET', datos, signal } = {}) {
    const respuesta = await solicitar(`${baseUrl.replace(/\/$/, '')}/pacientes${ruta}`, {
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
      const error = new Error(cuerpo.detalle || 'No se pudo completar la operación.');
      error.codigo = cuerpo.codigo;
      error.estado = respuesta.status;
      error.campos = cuerpo.campos || [];
      throw error;
    }
    return cuerpo;
  }
  return {
    buscarPorDni: (dni, signal) => enviar(`?dni=${encodeURIComponent(dni)}`, { signal }),
    consultar: (id, signal) => enviar(`/${encodeURIComponent(id)}`, { signal }),
    registrar: datos => enviar('', { metodo: 'POST', datos }),
    actualizar: (id, datos) => enviar(`/${encodeURIComponent(id)}`, { metodo: 'PUT', datos }),
  };
}
