import { app, BrowserWindow, ipcMain, screen } from 'electron'
import path from 'path'

let scannerWindow: BrowserWindow | null = null

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
