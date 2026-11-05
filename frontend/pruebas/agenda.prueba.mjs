import prueba from 'node:test';
import assert from 'node:assert/strict';
import {
  fechaLocalISO,
  formatearFecha,
  formatearHora,
  mensajeErrorCita,
} from '../src/utilidades/agenda.js';

prueba('el conflicto 409 muestra un mensaje claro de horario ocupado', () => {
  const mensaje = mensajeErrorCita({
    estado: 409,
    codigo: 'HORARIO_OCUPADO',
    message: 'El horario seleccionado acaba de ocuparse. Elige otro turno.',
  });
  assert.match(mensaje, /ocup/i);
});

prueba('el conflicto sin detalle usa un mensaje de respaldo que invita a elegir otro turno', () => {
  const mensaje = mensajeErrorCita({ estado: 409, codigo: 'HORARIO_OCUPADO' });
  assert.match(mensaje, /ocupa/i);
  assert.match(mensaje, /turno/i);
});

prueba('cada estado HTTP se traduce a un mensaje util', () => {
  assert.match(mensajeErrorCita({ estado: 403 }), /permiso/i);
  assert.match(mensajeErrorCita({ estado: 404 }), /paciente|medico|médico/i);
  assert.match(mensajeErrorCita({ estado: 422 }), /datos/i);
  assert.match(mensajeErrorCita({ estado: 0, message: 'Sin conexion' }), /Sin conexion/);
});

prueba('horas y fechas se presentan en formato local legible', () => {
  assert.equal(formatearHora('09:30:00'), '09:30');
  assert.equal(formatearHora('09:30'), '09:30');
  assert.equal(formatearFecha('2030-01-07'), '07/01/2030');
  assert.match(fechaLocalISO(new Date(2030, 0, 7)), /^2030-01-07$/);
});
