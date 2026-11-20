import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

export default defineConfig(() => ({
  base: '/admin/',
  plugins: [react(), tailwindcss()],
  define: {
    __STAFF_DEPLOYMENT__: JSON.stringify({"origin": "http://127.0.0.1:52486", "version": "staff-paper-pilot-origin-v1", "pin": "fdc03d5d4faa27371db32001ef6d37fb86bd0d19fb1a4527b476d1333e44e8c4", "rpId": null, "paperPilot": true}),
  },
}));
