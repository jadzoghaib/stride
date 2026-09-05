import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

/** The API the client talks to in development. Both the dev server and
 *  `vite preview` need it: preview serves the real production build, which is
 *  the only place a code-split chunk can fail to resolve, so it has to be
 *  testable against a live API rather than only in dev. */
const proxy = {
  '/api': 'http://127.0.0.1:8490',
  '/healthz': 'http://127.0.0.1:8490',
  '/metrics': 'http://127.0.0.1:8490',
}

export default defineConfig({
  plugins: [react()],
  server: { port: 5173, proxy },
  preview: { port: 4173, proxy },
})
