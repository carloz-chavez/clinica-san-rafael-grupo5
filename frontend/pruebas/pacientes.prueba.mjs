// Ejecutar con Node 22+: node --test frontend/pruebas/pacientes.prueba.mjs
import prueba from 'node:test';
import assert from 'node:assert/strict';
import { crearClientePacientes } from '../src/api/pacientes.js';

prueba('buscar por DNI envia Bearer y no cachea datos de pacientes', async () => {
  const cliente = crearClientePacientes({ token: 'token-ficticio', baseUrl: 'http://qa.invalid/', solicitar: async (url, opciones) => {
    assert.equal(url, 'http://qa.invalid/pacientes?dni=00000001');
    assert.equal(opciones.headers.Authorization, 'Bearer token-ficticio');
    assert.equal(opciones.cache, 'no-store');
    return { ok: true, json: async () => ({ id_paciente: 1 }) };
  } });
  assert.deepEqual(await cliente.buscarPorDni('00000001'), { id_paciente: 1 });
});

for (const [operacion, metodo, ruta] of [['registrar', 'POST', ''], ['actualizar', 'PUT', '/1']]) {
  prueba(`${operacion} conserva datos y metodo HTTP`, async () => {
    const datos = { dni: '00000001', nombres: 'Ficticio' };
    const cliente = crearClientePacientes({ solicitar: async (url, opciones) => {
      assert.equal(url, `/pacientes${ruta}`);
      assert.equal(opciones.method, metodo);
      assert.deepEqual(JSON.parse(opciones.body), datos);
      assert.equal(opciones.headers['Content-Type'], 'application/json');
      return { ok: true, json: async () => datos };
    } });
    assert.deepEqual(await (operacion === 'registrar' ? cliente.registrar(datos) : cliente.actualizar(1, datos)), datos);
  });
}

for (const estado of [403, 404, 409, 422]) {
  prueba(`propaga error ${estado} y errores por campo del backend`, async () => {
    const campos = [{ campo: 'dni', mensaje: 'DNI invalido' }];
    const cliente = crearClientePacientes({ solicitar: async () => ({ ok: false, status: estado, json: async () => ({ detalle: 'Error ficticio', codigo: 'CODIGO_PRUEBA', campos }) }) });
    await assert.rejects(cliente.buscarPorDni('00000001'), error => error.estado === estado && error.codigo === 'CODIGO_PRUEBA' && error.campos === campos);
  });
}

prueba('propaga la cancelacion de una busqueda sin convertirla en datos', async () => {
  const controlador = new AbortController();
  controlador.abort();
  const cliente = crearClientePacientes({ solicitar: async (_url, opciones) => { opciones.signal.throwIfAborted(); } });
  await assert.rejects(cliente.buscarPorDni('00000001', controlador.signal), { name: 'AbortError' });
});
