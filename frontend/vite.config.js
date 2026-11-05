import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

const destinoApi = 'http://127.0.0.1:8000';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/auth': destinoApi,
      '/pacientes': destinoApi,
      '/consultas': destinoApi,
      '/citas': destinoApi,
      '/salud': destinoApi,
    },
  },
});
