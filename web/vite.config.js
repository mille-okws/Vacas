import {defineConfig} from 'vite';
import react from '@vitejs/plugin-react';

// A interface compilada vai para src/vacas/web, de onde o servidor Python a entrega.
export default defineConfig({
  plugins: [react()],
  base: './',
  build: {outDir: '../src/vacas/web', emptyOutDir: true},
  server: {port: 5173, proxy: {'/api': 'http://127.0.0.1:8790'}},
});
