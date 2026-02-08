import { app, BrowserWindow, ipcMain, screen } from 'electron'
import path from 'path'
import { spawn, ChildProcess } from 'child_process'

let scannerWindow: BrowserWindow | null = null
let backendProcess: ChildProcess | null = null

// app.py lives at the project root (one level above frontend/)
const PROJECT_ROOT = path.join(__dirname, '..', '..', '..')
const BACKEND_SCRIPT = path.join(PROJECT_ROOT, 'app.py')

const startBackend = () => {
  if (backendProcess) return

  console.log('[backend] Starting app.py from:', BACKEND_SCRIPT)
  backendProcess = spawn('python3', [BACKEND_SCRIPT], {
    cwd: PROJECT_ROOT,
    stdio: ['ignore', 'pipe', 'pipe'],
  })

  backendProcess.stdout?.on('data', (data: Buffer) => {
    console.log(`[backend] ${data.toString().trimEnd()}`)
  })
  backendProcess.stderr?.on('data', (data: Buffer) => {
    console.error(`[backend] ${data.toString().trimEnd()}`)
  })
  backendProcess.on('exit', (code) => {
    console.log(`[backend] app.py exited with code ${code}`)
    backendProcess = null
  })
}

const stopBackend = () => {
  if (!backendProcess) return
  console.log('[backend] Stopping app.py')
  backendProcess.kill('SIGTERM')
  backendProcess = null
}

const createWindow = () => {
  console.log('=== CREATING MAIN WINDOW ===')
  const mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    webPreferences: {
      preload: path.join(__dirname, '../preload/preload.js'),
      contextIsolation: true,
      nodeIntegration: false
    }
  })

  // Load the app
  const devServerUrl = process.env.VITE_DEV_SERVER_URL || 'http://localhost:5173'
  if (process.env.NODE_ENV !== 'production' || process.env.VITE_DEV_SERVER_URL) {
    mainWindow.loadURL(devServerUrl)
    mainWindow.webContents.openDevTools()
  } else {
    mainWindow.loadFile(path.join(__dirname, '../renderer/index.html'))
  }
}

const createScannerWindow = () => {
  if (scannerWindow && !scannerWindow.isDestroyed()) {
    scannerWindow.focus()
    return
  }

  const { width: screenWidth } = screen.getPrimaryDisplay().workAreaSize
  const windowWidth = 450
  const windowHeight = 840

  scannerWindow = new BrowserWindow({
    width: windowWidth,
    height: windowHeight,
    x: screenWidth - windowWidth,
    y: 0,
    alwaysOnTop: true,
    show: false,
    webPreferences: {
      preload: path.join(__dirname, '../preload/preload.js'),
      contextIsolation: true,
      nodeIntegration: false
    }
  })

  // Load the scanner window
  const devServerUrl = process.env.VITE_DEV_SERVER_URL || 'http://localhost:5173'
  const scannerUrl = `${devServerUrl}/scanner.html`
  
  console.log('Loading scanner from:', scannerUrl)
  
  scannerWindow.loadURL(scannerUrl).then(() => {
    console.log('Scanner window loaded successfully')
    scannerWindow?.show()
    scannerWindow?.webContents.openDevTools()
  }).catch((err) => {
    console.error('Failed to load scanner:', err)
  })

  scannerWindow.on('closed', () => {
    scannerWindow = null
  })
}

const closeScannerWindow = () => {
  if (scannerWindow && !scannerWindow.isDestroyed()) {
    scannerWindow.close()
    scannerWindow = null
  }
}

app.whenReady().then(() => {
  console.log('=== APP STARTING ===')
  startBackend()
  createWindow()

  // IPC handlers for scanner window
  ipcMain.handle('open-scanner', () => {
    console.log('=== IPC: open-scanner called ===')
    createScannerWindow()
  })

  ipcMain.handle('close-scanner', () => {
    closeScannerWindow()
  })

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow()
    }
  })
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit()
  }
})

app.on('will-quit', () => {
  stopBackend()
})
