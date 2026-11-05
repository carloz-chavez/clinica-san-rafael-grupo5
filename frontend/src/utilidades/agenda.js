export function formatearHora(valor) {
  return String(valor || '').slice(0, 5);
}

export function formatearFecha(valor) {
  const texto = String(valor || '');
  const partes = texto.slice(0, 10).split('-');
  return partes.length === 3 ? `${partes[2]}/${partes[1]}/${partes[0]}` : texto;
}

export function fechaLocalISO(fecha = new Date()) {
  const anio = fecha.getFullYear();
  const mes = String(fecha.getMonth() + 1).padStart(2, '0');
  const dia = String(fecha.getDate()).padStart(2, '0');
  return `${anio}-${mes}-${dia}`;
}

export function mensajeErrorCita(fallo) {
  if (!fallo) return 'No se pudo completar la reserva. Intenta nuevamente.';
  if (fallo.estado === 409) {
    return fallo.message || 'Ese horario acaba de ocuparse. Actualiza la disponibilidad y elige otro turno.';
  }
  if (fallo.estado === 403) return 'No tienes permiso para registrar citas.';
  if (fallo.estado === 404) return fallo.message || 'No se encontro el paciente o el medico.';
  if (fallo.estado === 422) return fallo.message || 'Revisa los datos de la cita.';
  if (fallo.estado === 0) return fallo.message || 'No se pudo conectar con el servidor.';
  return fallo.message || 'No se pudo completar la reserva.';
}
