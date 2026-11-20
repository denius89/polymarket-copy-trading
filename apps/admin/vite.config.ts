import { createHash } from 'node:crypto';
import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import { defineConfig, loadEnv } from 'vite';

function staffDeployment(mode: string) {
  const env = loadEnv(mode, process.cwd(), 'VITE_STAFF_Q06');
  if (env.VITE_STAFF_Q06 !== '1') return null;

  const version = 'staff-paper-pilot-origin-v1';
  const origin = env.VITE_STAFF_Q06_ORIGIN;
  if (!origin) throw new Error('VITE_STAFF_Q06_ORIGIN is required');
  const url = new URL(origin);
  const local = mode === 'staff-q06-local' && origin === 'http://127.0.0.1:52486';
  if (url.origin !== origin || (!local && url.protocol !== 'https:')) {
    throw new Error('Staff Q06 requires an exact HTTPS origin');
  }

  const pin = createHash('sha256').update(JSON.stringify({ origin, version })).digest('hex');
  if (pin !== env.VITE_STAFF_Q06_ORIGIN_SHA256) {
    throw new Error('Staff Q06 origin pin does not match');
  }
  return { origin, version, pin, rpId: null, paperPilot: true };
}

export default defineConfig(({ mode }) => ({
  base: '/admin/',
  plugins: [react(), tailwindcss()],
  define: { __STAFF_DEPLOYMENT__: JSON.stringify(staffDeployment(mode)) },
}));
