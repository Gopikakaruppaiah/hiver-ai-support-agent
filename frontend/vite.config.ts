import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Backend URL for the dev-server proxy. Override with BACKEND_URL if the
// backend runs on a different host/port (e.g. inside a container).
const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': BACKEND_URL,
      '/health': BACKEND_URL,
    },
  },
})
