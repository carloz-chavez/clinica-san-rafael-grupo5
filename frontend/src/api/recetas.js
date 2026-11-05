// HU04: G1 proporciona su transporte/sesion; no se guardan datos clinicos ni tokens.
export function crearClienteRecetas({ token, baseUrl = '', solicitar = fetch }) {
  return {
    async registrar(idConsulta, datos) {
      const respuesta = await solicitar(`${baseUrl.replace(/\/$/, '')}/consultas/${encodeURIComponent(idConsulta)}/indicaciones`, {
        method: 'POST',
        cache: 'no-store',
        headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
        body: JSON.stringify(datos),
      });
      const cuerpo = await respuesta.json().catch(() => ({}));
      if (!respuesta.ok) {
        const error = new Error(cuerpo.detalle || 'No se pudo registrar la información.');
        error.estado = respuesta.status;
        error.codigo = cuerpo.codigo;
        error.campos = cuerpo.campos || [];
        throw error;
      }
      return cuerpo;
    },
  };
}
