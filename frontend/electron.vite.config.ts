import { defineConfig } from 'electron-vite'
import react from '@vitejs/plugin-react-swc'
import path from 'path'
import { fileURLToPath } from 'url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

export default defineConfig({
  main: {
    build: {
      outDir: 'dist-electron/main',
      rollupOptions: {
        input: path.join(__dirname, 'electron/main.ts')
      }
    }
  },
  preload: {
    build: {
      outDir: 'dist-electron/preload',
      rollupOptions: {
        input: path.join(__dirname, 'electron/preload.ts')
      }
    }
  },
  renderer: {
    root: __dirname,
    build: {
      outDir: 'dist-electron/renderer',
      rollupOptions: {
        input: {
          index: path.join(__dirname, 'index.html'),
          scanner: path.join(__dirname, 'scanner.html')
        }
      }
    },
    plugins: [react()],
    server: {
      port: 5173
    }
  }
})
