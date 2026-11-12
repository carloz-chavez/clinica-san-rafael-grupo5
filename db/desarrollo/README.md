# Datos de demostración

`cuentas_ficticias.example.json` define las siete cuentas C2, sin contraseñas.
El script pide las claves acordadas por entrada oculta y crea
`cuentas_ficticias.json`, excluido de Git. También puedes copiar ese archivo desde
el canal privado del equipo antes de ejecutar la preparación.

Son credenciales académicas, solo para desarrollo y demostraciones. El script
las convierte a Argon2id; el login de la aplicación nunca lee este archivo.

La carpeta se excluye en `.dockerignore` y está fuera del paquete del backend.
No la copies a imágenes ni despliegues de producción.
