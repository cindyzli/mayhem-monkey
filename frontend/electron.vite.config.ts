import { defineConfig } from 'electron-vite'
import react from '@vitejs/plugin-react-swc'

export default defineConfig({
  main: {
    // Main process config
    build: {
      outDir: 'dist-electron/main',
      rollupOptions: {
        input: 'electron/main.ts'
      }
    }
  },
  preload: {
    // Preload scripts config
    build: {
      outDir: 'dist-electron/preload',
      rollupOptions: {
        input: 'electron/preload.ts'
      }
    }
  },
  renderer: {
    // Renderer process (your existing React app)
    build: {
      outDir: 'dist-electron/renderer'
    },
    plugins: [react()]
  }
})
