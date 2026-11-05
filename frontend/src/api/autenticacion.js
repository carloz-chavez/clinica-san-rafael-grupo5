// HU09: login contra el backend. La sesion la administra ContextoSesion.
import { solicitarJson } from './cliente.js';

export function crearClienteAutenticacion({ baseUrl = '', solicitar = fetch } = {}) {
  return {
    iniciarSesion: (correo, contrasena) => solicitarJson('/auth/login', {
      metodo: 'POST',
      datos: { correo, contrasena },
      baseUrl,
      solicitar,
    }),
  };
}
