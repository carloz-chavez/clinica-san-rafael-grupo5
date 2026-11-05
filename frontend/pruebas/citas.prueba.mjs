import prueba from 'node:test';
import assert from 'node:assert/strict';
import { crearClienteCitas } from '../src/api/citas.js';

prueba('catalogos consulta especialidades y medicos con Bearer', async () => {
  const resultado = { especialidades: [], medicos: [] };
  const cliente = crearClienteCitas({ token: 'token-ficticio', baseUrl: 'http://qa.invalid/', solicitar: async (url, opciones) => {
    assert.equal(url, 'http://qa.invalid/citas/catalogos');
    assert.equal(opciones.headers.Authorization, 'Bearer token-ficticio');
    assert.equal(opciones.cache, 'no-store');
    return { ok: true, json: async () => resultado };
  } });
  assert.deepEqual(await cliente.catalogos(), resultado);
});

prueba('disponibilidad arma la consulta con fecha, especialidad y medico', async () => {
  const resultado = { fecha: '2030-01-07', medicos: [] };
  const cliente = crearClienteCitas({ token: 'token-ficticio', baseUrl: 'http://qa.invalid/', solicitar: async (url, opciones) => {
    assert.equal(
      url,
      'http://qa.invalid/citas/disponibilidad?fecha=2030-01-07&id_especialidad=2&id_medico=5',
    );
    assert.equal(opciones.headers.Authorization, 'Bearer token-ficticio');
    return { ok: true, json: async () => resultado };
  } });
  assert.deepEqual(
    await cliente.disponibilidad({ fecha: '2030-01-07', idEspecialidad: 2, idMedico: 5 }),
    resultado,
  );
});

prueba('listar citas usa solo la fecha indicada', async () => {
  const cliente = crearClienteCitas({ solicitar: async (url) => {
    assert.equal(url, '/citas?fecha=2030-01-07');
    return { ok: true, json: async () => [] };
  } });
  assert.deepEqual(await cliente.listar('2030-01-07'), []);
});

prueba('registrar cita envia el cuerpo completo por POST', async () => {
  const datos = {
    id_paciente: 8,
    id_medico: 5,
    fecha: '2030-01-07',
    hora: '09:00',
    motivo: 'Motivo ficticio',
  };
  const resultado = { id_cita: 1, ...datos, estado: 'registrada' };
  const cliente = crearClienteCitas({ token: 'token-ficticio', solicitar: async (url, opciones) => {
    assert.equal(url, '/citas');
    assert.equal(opciones.method, 'POST');
    assert.equal(opciones.headers['Content-Type'], 'application/json');
    assert.equal(opciones.headers.Authorization, 'Bearer token-ficticio');
    assert.deepEqual(JSON.parse(opciones.body), datos);
    return { ok: true, json: async () => resultado };
  } });
  assert.deepEqual(await cliente.registrar(datos), resultado);
});

prueba('un 409 conserva codigo y mensaje para mostrarlo en pantalla', async () => {
  const cliente = crearClienteCitas({
    solicitar: async () => ({
      ok: false,
      status: 409,
      json: async () => ({ detalle: 'El horario seleccionado acaba de ocuparse.', codigo: 'HORARIO_OCUPADO' }),
    }),
  });
  await assert.rejects(
    cliente.registrar({}),
    error => error.estado === 409
      && error.codigo === 'HORARIO_OCUPADO'
      && error.message.includes('ocuparse'),
  );
});

prueba('un error de red no se reintenta', async () => {
  let llamadas = 0;
  const cliente = crearClienteCitas({
    solicitar: async () => {
      llamadas += 1;
      throw new TypeError('Red QA');
    },
  });
  await assert.rejects(cliente.registrar({}), error => error.estado === 0 && error.codigo === 'ERROR_RED');
  assert.equal(llamadas, 1);
});
