// G1 puede inyectar su transporte. Una escritura nunca se reintenta automaticamente.
export function crearClienteAnulaciones({ token, baseUrl = '', solicitar = fetch }) {
  return {
    async anular(idConsulta, datos) {
      const respuesta = await solicitar(`${baseUrl.replace(/\/$/, '')}/consultas/${encodeURIComponent(idConsulta)}/anular`, {
        method: 'POST',
        cache: 'no-store',
        headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
        body: JSON.stringify(datos),
      });
      const cuerpo = await respuesta.json().catch(() => ({}));
      if (!respuesta.ok) {
        const error = new Error(cuerpo.detalle || 'No se pudo anular la consulta.');
        error.estado = respuesta.status;
        error.codigo = cuerpo.codigo;
        error.campos = cuerpo.campos || [];
        throw error;
      }
      return cuerpo;
    },
  };
}
