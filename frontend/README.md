# Frontend

Aplicación React + Vite + React Router + Tailwind para la Clínica San Rafael.
Implementa la base del frontend (G1), el inicio de sesión (G2) y el módulo de
agenda (G3, G4 y G5).

## Requisitos

- Node.js 22 o superior.
- Backend en `http://localhost:8000` (ver README de la raíz).

## Ejecución

```bash
cd frontend
npm install
npm run dev
```

Abre `http://localhost:5173`. El servidor de desarrollo redirige `/auth`,
`/pacientes`, `/consultas`, `/citas` y `/salud` al backend del puerto 8000.

Si el backend está en otra dirección, define `VITE_API_URL` antes de arrancar:

```bash
# PowerShell
$env:VITE_API_URL = "http://localhost:8000"
npm run dev
```

## Sesión y roles

- `ADMISION` y `ADMINISTRADOR`: menú **Pacientes** y **Agenda**.
- `MEDICO`: menú **Historia clínica** (pantalla reservada hasta integrar HU02/HU03).
- La sesión se guarda en `sessionStorage`; el token se envía como `Bearer`.
- Sin token, el backend solo responde si tiene `AUTENTICACION_SIMULADA=true`.

Modo simulado de desarrollo (solo si el backend también lo permite):

```powershell
$env:VITE_AUTENTICACION_SIMULADA = "true"
npm run dev
```

La pantalla de login mostrará un selector de rol. No uses este modo para
demostraciones: el login real de HU09 ya está disponible.

## Estructura

```
src/
├─ api/            cliente HTTP común, autenticación y citas
├─ autenticacion/  ContextoSesion y RutaProtegida
├─ componentes/    Boton, Campo, Selector, Tabla, Modal, InsigniaEstado, Alerta
├─ diseno/         menú lateral por rol y estructura general
├─ paginas/        InicioSesion, GestionPacientes, AgendaCitas, HistoriaClinica
├─ utilidades/     funciones de sesión, fechas y mensajes de error
└─ estilos/        Tailwind y estilos globales
```

Los componentes de Carlos (`GestionPacientes`, `FormularioRecetas`,
`ModalAnulacion`) se integran sin modificar su contrato.

## Endpoints de agenda

| Método | Ruta | Uso |
|---|---|---|
| GET | `/citas/catalogos` | Especialidades y médicos activos para los filtros. |
| GET | `/citas/disponibilidad?fecha=&id_especialidad=&id_medico=` | Turnos de 30 minutos marcados como libres u ocupados. |
| POST | `/citas` | Registra la cita; responde 409 si el turno está ocupado. |
| GET | `/citas?fecha=` | Citas del día ordenadas por hora y médico. |

El formulario de reserva busca al paciente por DNI con el endpoint de HU01 y
envía `id_paciente`, `id_medico`, `fecha`, `hora` y `motivo`. Nunca consulta la
tabla de pacientes directamente.

## Pruebas

```bash
npm run prueba
```

Las pruebas cubren los clientes de API, la sesión, los mensajes de error y el
conflicto 409. La prueba visual del modal HU10 sigue siendo opcional y requiere
`C6_UI_QA`, como se explica en `src/componentes/recetas/HU10.md`.
