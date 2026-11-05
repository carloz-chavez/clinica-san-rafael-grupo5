export const ROLES = ['ADMISION', 'MEDICO', 'ADMINISTRADOR'];

const ETIQUETAS_ROL = {
  ADMISION: 'Admisión',
  MEDICO: 'Médico',
  ADMINISTRADOR: 'Administrador',
};

export function esRolValido(rol) {
  return ROLES.includes(rol);
}

export function etiquetaRol(rol) {
  return ETIQUETAS_ROL[rol] || 'Usuario';
}

export function rutaInicioPorRol(rol) {
  return rol === 'MEDICO' ? '/historia' : '/pacientes';
}

export function normalizarSesion(valor) {
  if (!valor || typeof valor !== 'object') return null;
  const { token, usuario } = valor;
  if (token !== null && typeof token !== 'string') return null;
  if (!usuario || !Number.isInteger(usuario.id_usuario) || !esRolValido(usuario.rol)) return null;
  return { token: token ?? null, usuario };
}
