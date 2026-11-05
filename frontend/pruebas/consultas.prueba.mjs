// Node 22+: node --test frontend/pruebas/*.prueba.mjs
import prueba from 'node:test';
import assert from 'node:assert/strict';
import { crearClienteConsultas } from '../src/api/consultas.js';

prueba('registra atencion HU02 con cuerpo y encabezados correctos', async () => {
  const datos = { id_paciente: 3, diagnostico_cie10: 'J06.9', observaciones: 'Atencion ficticia' };
  const resultado = { id_consulta: 9, id_paciente: 3, anulada: false };
  const cliente = crearClienteConsultas({ token: 'token-ficticio', baseUrl: 'http://qa.invalid/', solicitar: async (url, opciones) => {
    assert.equal(url, 'http://qa.invalid/consultas');
    assert.equal(opciones.method, 'POST');
    assert.equal(opciones.cache, 'no-store');
    assert.equal(opciones.headers.Authorization, 'Bearer token-ficticio');
    assert.deepEqual(JSON.parse(opciones.body), datos);
    return { ok: true, json: async () => resultado };
  } });
  assert.deepEqual(await cliente.registrar(datos), resultado);
});

prueba('consulta historia clinica HU03 por id de paciente y pasa la senal', async () => {
  const senal = new AbortController().signal;
  const resultado = { paciente: { id_paciente: 3 }, total_consultas: 1, consultas: [] };
  const cliente = crearClienteConsultas({ token: 'token-ficticio', baseUrl: '', solicitar: async (url, opciones) => {
    assert.equal(url, '/pacientes/3/historia');
    assert.equal(opciones.method, 'GET');
    assert.equal(opciones.cache, 'no-store');
    assert.equal(opciones.headers.Authorization, 'Bearer token-ficticio');
    assert.equal(opciones.signal, senal);
    return { ok: true, json: async () => resultado };
  } });
  assert.deepEqual(await cliente.obtenerHistoria(3, senal), resultado);
});

prueba('consulta una atencion individual por id', async () => {
  const resultado = { id_consulta: 5, anulada: false };
  const cliente = crearClienteConsultas({ baseUrl: 'http://qa.invalid', solicitar: async url => {
    assert.equal(url, 'http://qa.invalid/consultas/5');
    return { ok: true, json: async () => resultado };
  } });
  assert.deepEqual(await cliente.obtenerPorId(5), resultado);
});

for (const estado of [401, 403, 404, 409, 422, 500]) {
  prueba(`conserva error ${estado} y campos de validacion`, async () => {
    const campos = [{ campo: 'id_paciente', mensaje: 'Campo obligatorio' }];
    const cliente = crearClienteConsultas({ solicitar: async () => ({ ok: false, status: estado, json: async () => ({ detalle: 'Error ficticio', codigo: 'ERROR_PRUEBA', campos }) }) });
    await assert.rejects(cliente.registrar({}), error => error.estado === estado && error.codigo === 'ERROR_PRUEBA' && error.campos === campos);
  });
}

prueba('un error de red se propaga y no se reintenta una escritura', async () => {
  let llamadas = 0;
  const cliente = crearClienteConsultas({ solicitar: async () => { llamadas += 1; throw new TypeError('Red QA no disponible'); } });
  await assert.rejects(cliente.registrar({}), TypeError);
  assert.equal(llamadas, 1);
});
