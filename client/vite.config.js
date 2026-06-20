import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Dev server proxies API + SSE to the FastAPI backend so the SPA can use
// relative paths in development. In production set VITE_API_BASE_URL.
// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://127.0.0.1:8000',
      '/auth': 'http://127.0.0.1:8000',
      '/get_live_data': 'http://127.0.0.1:8000',
      '/stream': { target: 'http://127.0.0.1:8000', changeOrigin: true },
    },
  },
})
