import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Vite configuration for the Prompt Workbench frontend.
// - `/api` requests are proxied to the local backend on port 8765 during dev.
// - Production assets are emitted to `dist`.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8765',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
  },
});
