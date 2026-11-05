// Node 22+: node --test frontend/pruebas/*.prueba.mjs
import prueba from 'node:test';
import assert from 'node:assert/strict';
import { crearClienteRecetas } from '../src/api/recetas.js';

for (const datos of [
  { recetas: [{ medicamento: 'Producto ficticio', dosis: 'Dosis ilustrativa', frecuencia: 'Frecuencia ficticia' }], indicaciones: [] },
  { recetas: [], indicaciones: [{ descripcion: 'Indicación ficticia' }] },
  { recetas: [{ medicamento: 'Producto ficticio', dosis: 'Dosis ilustrativa', frecuencia: 'Frecuencia ficticia' }], indicaciones: [{ descripcion: 'Indicación ficticia' }] },
]) {
  prueba(`envia lote HU04 con ${datos.recetas.length} recetas y ${datos.indicaciones.length} indicaciones`, async () => {
    const resultado = { id_consulta: 7, recetas: [], indicaciones: [] };
    const cliente = crearClienteRecetas({ token: 'token-ficticio', baseUrl: 'http://qa.invalid/', solicitar: async (url, opciones) => {
      assert.equal(url, 'http://qa.invalid/consultas/7/indicaciones');
      assert.equal(opciones.method, 'POST');
      assert.equal(opciones.cache, 'no-store');
      assert.equal(opciones.headers.Authorization, 'Bearer token-ficticio');
      assert.deepEqual(JSON.parse(opciones.body), datos);
      return { ok: true, json: async () => resultado };
    } });
    assert.deepEqual(await cliente.registrar(7, datos), resultado);
  });
}

for (const estado of [401, 403, 404, 409, 422, 500]) {
  prueba(`conserva error ${estado} y campos de validacion`, async () => {
    const campos = [{ campo: 'recetas.0.dosis', mensaje: 'Campo obligatorio' }];
    const cliente = crearClienteRecetas({ solicitar: async () => ({ ok: false, status: estado, json: async () => ({ detalle: 'Error ficticio', codigo: 'ERROR_PRUEBA', campos }) }) });
    await assert.rejects(cliente.registrar(7, {}), error => error.estado === estado && error.codigo === 'ERROR_PRUEBA' && error.campos === campos);
  });
}

prueba('un error de red se propaga y no se reintenta una escritura', async () => {
  let llamadas = 0;
  const cliente = crearClienteRecetas({ solicitar: async () => { llamadas += 1; throw new TypeError('Red QA no disponible'); } });
  await assert.rejects(cliente.registrar(7, {}), TypeError);
  assert.equal(llamadas, 1);
});
