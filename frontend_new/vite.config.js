import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // Bind all interfaces so a local tunnel (cloudflared/ngrok -> 127.0.0.1)
    // can reach the dev server; without this Vite listens on ::1 only.
    host: true,
    // Vite 6+ rejects non-localhost Host headers (403) unless allowed. The
    // tunnel uses a random *.trycloudflare.com host each run, so allow any
    // host on this DEV server (never used for production builds).
    allowedHosts: true,
    // services/api.js defaults baseURL='/api' — proxy to the Flask backend.
    proxy: {
      '/api': 'http://127.0.0.1:5000',
    },
  },
})
