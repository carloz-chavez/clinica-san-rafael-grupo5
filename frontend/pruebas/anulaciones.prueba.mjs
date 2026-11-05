import prueba from 'node:test';
import assert from 'node:assert/strict';
import { crearClienteAnulaciones } from '../src/api/anulaciones.js';

prueba('anular envia motivo y sesion sin cache, conserva respuesta', async () => {
  const datos = { motivo_anulacion: 'Corrección ficticia' };
  const resultado = { id_consulta: 7, anulada: true, ...datos, id_usuario_anulacion: 8, fecha_anulacion: '2026-11-04T10:00:00' };
  const cliente = crearClienteAnulaciones({ token: 'token-ficticio', baseUrl: 'http://qa.invalid/', solicitar: async (url, opciones) => {
    assert.equal(url, 'http://qa.invalid/consultas/7/anular');
    assert.equal(opciones.method, 'POST');
    assert.equal(opciones.cache, 'no-store');
    assert.equal(opciones.headers.Authorization, 'Bearer token-ficticio');
    assert.equal(opciones.headers['Content-Type'], 'application/json');
    assert.deepEqual(JSON.parse(opciones.body), datos);
    return { ok: true, json: async () => resultado };
  } });
  assert.deepEqual(await cliente.anular(7, datos), resultado);
});

for (const estado of [401, 403, 404, 409, 422, 500]) {
  prueba(`anulacion propaga error ${estado} sin reintentos`, async () => {
    let llamadas = 0;
    const campos = [{ campo: 'motivo_anulacion', mensaje: 'Campo obligatorio' }];
    const cliente = crearClienteAnulaciones({ solicitar: async () => {
      llamadas += 1;
      return { ok: false, status: estado, json: async () => ({ detalle: 'Error ficticio', codigo: 'ERROR_QA', campos }) };
    } });
    await assert.rejects(cliente.anular(7, {}), error => error.estado === estado && error.codigo === 'ERROR_QA' && error.campos === campos);
    assert.equal(llamadas, 1);
  });
}

prueba('fallo de red no repite la anulacion', async () => {
  let llamadas = 0;
  const cliente = crearClienteAnulaciones({ solicitar: async () => { llamadas += 1; throw new TypeError('Red QA'); } });
  await assert.rejects(cliente.anular(7, {}), TypeError);
  assert.equal(llamadas, 1);
});

prueba('respuesta de error sin JSON conserva estado y mensaje util', async () => {
  const cliente = crearClienteAnulaciones({ solicitar: async () => ({ ok: false, status: 502, json: async () => { throw new SyntaxError(); } }) });
  await assert.rejects(cliente.anular(7, {}), error => error.estado === 502 && error.message === 'No se pudo anular la consulta.');
});
