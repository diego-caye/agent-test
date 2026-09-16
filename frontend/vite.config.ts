import path from 'node:path'

import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

const apiTarget = process.env.VITE_API_TARGET ?? 'http://localhost:8000'

// En Docker el código se monta desde el sistema de archivos de Windows y los
// eventos de inotify no cruzan el bind mount: sin polling, editar un .tsx no
// dispara el HMR. En local (sin la variable) se usa el watcher nativo.
const polling = process.env.VITE_POLLING === 'true'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  // shadcn/ui genera sus componentes importando desde '@/'.
  resolve: {
    alias: { '@': path.resolve(import.meta.dirname, './src') },
  },
  server: {
    host: true,
    port: 5173,
    ...(polling ? { watch: { usePolling: true, interval: 400 } } : {}),
    proxy: {
      '/api': { target: apiTarget, changeOrigin: true },
      '/healthz': { target: apiTarget, changeOrigin: true },
      '/openapi.json': { target: apiTarget, changeOrigin: true },
    },
  },
})
