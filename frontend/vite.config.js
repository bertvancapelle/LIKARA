import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'

// Frontend-module-loading (Optie A): platform-code via `@` (frontend/src) en
// module-frontendcode via de generieke `@modules`-alias (modules/-root). Zo heeft
// een volgende module géén vite-config-wijziging nodig. `server.fs.allow` is strak
// gescoopt tot frontend/ + modules/ (niet de kale repo-root → backend/.env blijft
// buiten de dev-server). De productie-build (dist/) raakt dit niet.
const frontendDir = fileURLToPath(new URL('.', import.meta.url))
const modulesDir = fileURLToPath(new URL('../modules', import.meta.url))

export default defineConfig({
  test: { environment: 'happy-dom', globals: true },
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
      '@modules': modulesDir,
    },
  },
  plugins: [vue(), tailwindcss()],
  server: {
    port: 3000,
    fs: { allow: [frontendDir, modulesDir] },
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
