// QA opcional sin modificar G1: C6_UI_QA apunta a una carpeta temporal con
// react, react-dom, esbuild y jsdom. Sin esas dependencias se omite esta suite.
import prueba from 'node:test';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { resolve, join } from 'node:path';

prueba('modal HU10: motivo, doble envio, permisos, errores y cambio de consulta', { skip: !process.env.C6_UI_QA }, async () => {
  const carpeta = process.env.C6_UI_QA;
  const requerir = createRequire(join(carpeta, 'package.json'));
  const { JSDOM } = requerir('jsdom');
  const dom = new JSDOM('<!doctype html><html><body><div id="raiz"></div></body></html>', { url: 'http://qa.invalid/' });
  const anteriores = new Map();
  for (const [nombre, valor] of Object.entries({ window: dom.window, document: dom.window.document, navigator: dom.window.navigator, IS_REACT_ACT_ENVIRONMENT: true })) {
    anteriores.set(nombre, Object.getOwnPropertyDescriptor(globalThis, nombre));
    Object.defineProperty(globalThis, nombre, { configurable: true, writable: true, value: valor });
  }
  // JSDOM no implementa dialog modal; se simula solo su API nativa.
  dom.window.HTMLDialogElement.prototype.showModal = function () { this.open = true; };
  dom.window.HTMLDialogElement.prototype.close = function () { this.open = false; };
  const React = requerir('react');
  const { act } = React;
  const { createRoot } = requerir('react-dom/client');
  const salida = join(carpeta, 'ModalAnulacion.cjs');
  await requerir('esbuild').build({ entryPoints: [resolve('frontend/src/componentes/recetas/ModalAnulacion.jsx')],
    bundle: true, platform: 'node', format: 'cjs', outfile: salida, external: ['react'], loader: { '.css': 'empty' } });
  const Modal = requerir(salida).default;
  const raiz = createRoot(document.getElementById('raiz'));
  const usuario = { id_usuario: 8, rol: 'MEDICO', id_medico: 9 };
  const consulta = { id_consulta: 7, id_paciente: 6, id_medico: 9, anulada: false };
  let llamadas = 0;
  let completar;
  let recibidos = [];
  let cierres = 0;
  const cliente = { anular: async (id, datos) => {
    llamadas += 1;
    assert.equal(id, 7);
    assert.deepEqual(datos, { motivo_anulacion: 'Motivo ficticio' });
    return new Promise(resolver => { completar = resolver; });
  } };
  const propiedades = { abierto: true, consulta, usuario, cliente, alAnular: dato => recibidos.push(dato), alCerrar: () => { cierres += 1; } };
  async function renderizar(cambios = {}) { await act(async () => raiz.render(React.createElement(Modal, { ...propiedades, ...cambios }))); }
  async function escribir(valor) {
    await act(async () => {
      const campo = document.querySelector('textarea');
      Object.getOwnPropertyDescriptor(dom.window.HTMLTextAreaElement.prototype, 'value').set.call(campo, valor);
      campo.dispatchEvent(new dom.window.Event('input', { bubbles: true }));
    });
  }
  async function enviar() { await act(async () => document.querySelector('form').dispatchEvent(new dom.window.Event('submit', { bubbles: true, cancelable: true }))); }
  try {
    await renderizar();
    assert.ok(document.querySelector('dialog').open);
    await escribir('   ');
    await enviar();
    assert.equal(llamadas, 0);
    await escribir('  Motivo ficticio  ');
    await enviar();
    await enviar();
    assert.equal(llamadas, 1);
    assert.ok(document.querySelector('fieldset').disabled);
    await act(async () => document.querySelector('dialog').dispatchEvent(new dom.window.Event('cancel', { cancelable: true })));
    assert.equal(cierres, 0);
    await act(async () => completar({ id_consulta: 7, anulada: true }));
    assert.deepEqual(recibidos, [{ id_consulta: 7, anulada: true }]);
    assert.match(document.body.textContent, /Consulta anulada correctamente/);
    await enviar();
    assert.equal(llamadas, 1);
    await renderizar({ usuario: { ...usuario, id_medico: 10 } });
    assert.ok(document.querySelector('fieldset').disabled);
    assert.match(document.body.textContent, /Solo el médico responsable/);
    await renderizar({ consulta: { ...consulta, anulada: true } });
    assert.ok(document.querySelector('fieldset').disabled);
    const clienteError = { anular: async () => { throw Object.assign(new Error('La consulta ya está anulada.'), { codigo: 'CONSULTA_ANULADA' }); } };
    await renderizar({ cliente: clienteError });
    await escribir('Motivo ficticio');
    await enviar();
    assert.match(document.querySelector('[role="alert"]').textContent, /ya está anulada/);
    assert.ok(document.querySelector('fieldset').disabled);
    await renderizar();
    await escribir('Motivo ficticio');
    await enviar();
    await renderizar({ consulta: { ...consulta, id_consulta: 11 } });
    await act(async () => completar({ id_consulta: 7, anulada: true }));
    assert.equal(recibidos.length, 1, 'No entrega respuesta obsoleta a otra consulta');
    assert.equal(document.querySelector('textarea').value, '');
  } finally {
    await act(async () => raiz.unmount());
    dom.window.close();
    for (const [nombre, descriptor] of anteriores) {
      if (descriptor) Object.defineProperty(globalThis, nombre, descriptor);
      else delete globalThis[nombre];
    }
  }
});
