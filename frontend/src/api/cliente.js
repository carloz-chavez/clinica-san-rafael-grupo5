// Transporte comun de G1: agrega el token, evita cache y traduce los errores de la API.
function unirUrl(baseUrl, ruta) {
  const raiz = String(baseUrl || '').replace(/\/$/, '');
  return `${raiz}${ruta}`;
}

export async function solicitarJson(ruta, {
  metodo = 'GET',
  datos,
  token,
  baseUrl = '',
  solicitar = fetch,
  signal,
} = {}) {
  let respuesta;
  try {
    respuesta = await solicitar(unirUrl(baseUrl, ruta), {
      method: metodo,
      signal,
      cache: 'no-store',
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(datos ? { 'Content-Type': 'application/json' } : {}),
      },
      ...(datos ? { body: JSON.stringify(datos) } : {}),
    });
  } catch (fallo) {
    if (fallo?.name === 'AbortError') throw fallo;
    const error = new Error('No se pudo conectar con el servidor. Revisa tu conexion e intenta nuevamente.');
    error.estado = 0;
    error.codigo = 'ERROR_RED';
    error.campos = [];
    error.causa = fallo;
    throw error;
  }

  const cuerpo = await respuesta.json().catch(() => ({}));
  if (!respuesta.ok) {
    const error = new Error(cuerpo.detalle || 'No se pudo completar la operacion.');
    error.estado = respuesta.status;
    error.codigo = cuerpo.codigo;
    error.campos = cuerpo.campos || [];
    throw error;
  }
  return cuerpo;
}
