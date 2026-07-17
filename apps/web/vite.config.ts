import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://127.0.0.1:8490',
      '/healthz': 'http://127.0.0.1:8490',
      '/metrics': 'http://127.0.0.1:8490',
    },
  },
})
