import prueba from 'node:test';
import assert from 'node:assert/strict';
import { crearClienteAutenticacion } from '../src/api/autenticacion.js';
import { etiquetaRol, normalizarSesion, rutaInicioPorRol } from '../src/utilidades/sesion.js';

prueba('login envia correo y contrasena al backend sin token previo', async () => {
  const resultado = {
    token_acceso: 'token-ficticio',
    tipo_token: 'bearer',
    usuario: { id_usuario: 1, correo: 'admision.c2@sanrafael.invalid', rol: 'ADMISION' },
  };
  const cliente = crearClienteAutenticacion({ baseUrl: 'http://qa.invalid/', solicitar: async (url, opciones) => {
    assert.equal(url, 'http://qa.invalid/auth/login');
    assert.equal(opciones.method, 'POST');
    assert.equal(opciones.cache, 'no-store');
    assert.equal(opciones.headers.Authorization, undefined);
    assert.equal(opciones.headers['Content-Type'], 'application/json');
    assert.deepEqual(JSON.parse(opciones.body), {
      correo: 'admision.c2@sanrafael.invalid',
      contrasena: 'clave-ficticia',
    });
    return { ok: true, json: async () => resultado };
  } });

  assert.deepEqual(
    await cliente.iniciarSesion('admision.c2@sanrafael.invalid', 'clave-ficticia'),
    resultado,
  );
});

prueba('login conserva el 401 y el mensaje del backend', async () => {
  const cliente = crearClienteAutenticacion({
    solicitar: async () => ({
      ok: false,
      status: 401,
      json: async () => ({ detalle: 'Correo o contrasena incorrectos.', codigo: 'CREDENCIALES_INVALIDAS' }),
    }),
  });
  await assert.rejects(
    cliente.iniciarSesion('noexiste@sanrafael.invalid', 'clave'),
    error => error.estado === 401 && error.codigo === 'CREDENCIALES_INVALIDAS',
  );
});

prueba('login traduce una caida de red sin reintentar', async () => {
  let llamadas = 0;
  const cliente = crearClienteAutenticacion({
    solicitar: async () => {
      llamadas += 1;
      throw new TypeError('Red QA');
    },
  });
  await assert.rejects(
    cliente.iniciarSesion('usuario@sanrafael.invalid', 'clave'),
    error => error.estado === 0 && error.codigo === 'ERROR_RED' && error.message.includes('conectar'),
  );
  assert.equal(llamadas, 1);
});

prueba('cada rol inicia en su pantalla y muestra su etiqueta', () => {
  assert.equal(rutaInicioPorRol('MEDICO'), '/historia');
  assert.equal(rutaInicioPorRol('ADMISION'), '/pacientes');
  assert.equal(rutaInicioPorRol('ADMINISTRADOR'), '/pacientes');
  assert.equal(etiquetaRol('MEDICO'), 'Médico');
  assert.equal(etiquetaRol('ADMISION'), 'Admisión');
});

prueba('normalizarSesion rechaza sesiones incompletas o con rol desconocido', () => {
  assert.equal(normalizarSesion(null), null);
  assert.equal(normalizarSesion({ token: null, usuario: { id_usuario: 1, rol: 'OTRO' } }), null);
  assert.deepEqual(
    normalizarSesion({ token: 'token', usuario: { id_usuario: 2, correo: 'x@y.invalid', rol: 'MEDICO' } }),
    { token: 'token', usuario: { id_usuario: 2, correo: 'x@y.invalid', rol: 'MEDICO' } },
  );
  assert.deepEqual(
    normalizarSesion({ token: null, usuario: { id_usuario: 0, correo: 'simulado@local', rol: 'ADMISION' } }),
    { token: null, usuario: { id_usuario: 0, correo: 'simulado@local', rol: 'ADMISION' } },
  );
});
