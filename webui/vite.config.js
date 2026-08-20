import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Builds into zoetrading/ui/static, served by FastAPI as the local-only UI.
// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  build: {
    outDir: '../zoetrading/ui/static',
    emptyOutDir: true,
  },
  server: {
    proxy: {
      '/api': 'http://127.0.0.1:8765',
    },
  },
})
