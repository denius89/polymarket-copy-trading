import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
  base: process.env.VITE_PUBLIC_BASE || "/",
  plugins: [react(), tailwindcss()],
  server: { proxy: { '/api': { target: 'https://localhost:18443', changeOrigin: false, secure: false } } },
  build: { outDir: 'dist', emptyOutDir: true }
});
