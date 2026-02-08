"use strict";
const electron = require("electron");
const path = require("path");
const child_process = require("child_process");
let scannerWindow = null;
let backendProcess = null;
const PROJECT_ROOT = path.join(__dirname, "..", "..", "..");
const BACKEND_SCRIPT = path.join(PROJECT_ROOT, "app.py");
const startBackend = () => {
  if (backendProcess) return;
  console.log("[backend] Starting app.py from:", BACKEND_SCRIPT);
  backendProcess = child_process.spawn("python3", [BACKEND_SCRIPT], {
    cwd: PROJECT_ROOT,
    stdio: ["ignore", "pipe", "pipe"]
  });
  backendProcess.stdout?.on("data", (data) => {
    console.log(`[backend] ${data.toString().trimEnd()}`);
  });
  backendProcess.stderr?.on("data", (data) => {
    console.error(`[backend] ${data.toString().trimEnd()}`);
  });
  backendProcess.on("exit", (code) => {
    console.log(`[backend] app.py exited with code ${code}`);
    backendProcess = null;
  });
};
const stopBackend = () => {
  if (!backendProcess) return;
  console.log("[backend] Stopping app.py");
  backendProcess.kill("SIGTERM");
  backendProcess = null;
};
const createWindow = () => {
  console.log("=== CREATING MAIN WINDOW ===");
  const mainWindow = new electron.BrowserWindow({
    width: 1200,
    height: 800,
    webPreferences: {
      preload: path.join(__dirname, "../preload/preload.js"),
      contextIsolation: true,
      nodeIntegration: false
    }
  });
  const devServerUrl = process.env.VITE_DEV_SERVER_URL || "http://localhost:5173";
  if (process.env.NODE_ENV !== "production" || process.env.VITE_DEV_SERVER_URL) {
    mainWindow.loadURL(devServerUrl);
  } else {
    mainWindow.loadFile(path.join(__dirname, "../renderer/index.html"));
  }
};
const createScannerWindow = () => {
  if (scannerWindow && !scannerWindow.isDestroyed()) {
    scannerWindow.focus();
    return;
  }
  const { width: screenWidth } = electron.screen.getPrimaryDisplay().workAreaSize;
  const windowWidth = 450;
  const windowHeight = 840;
  scannerWindow = new electron.BrowserWindow({
    width: windowWidth,
    height: windowHeight,
    x: screenWidth - windowWidth,
    y: 0,
    alwaysOnTop: true,
    show: false,
    webPreferences: {
      preload: path.join(__dirname, "../preload/preload.js"),
      contextIsolation: true,
      nodeIntegration: false
    }
  });
  const devServerUrl = process.env.VITE_DEV_SERVER_URL || "http://localhost:5173";
  const scannerUrl = `${devServerUrl}/scanner.html`;
  console.log("Loading scanner from:", scannerUrl);
  scannerWindow.loadURL(scannerUrl).then(() => {
    console.log("Scanner window loaded successfully");
    scannerWindow?.show();
  }).catch((err) => {
    console.error("Failed to load scanner:", err);
  });
  scannerWindow.on("closed", () => {
    scannerWindow = null;
  });
};
const closeScannerWindow = () => {
  if (scannerWindow && !scannerWindow.isDestroyed()) {
    scannerWindow.close();
    scannerWindow = null;
  }
};
electron.app.whenReady().then(() => {
  console.log("=== APP STARTING ===");
  startBackend();
  createWindow();
  electron.ipcMain.handle("open-scanner", () => {
    console.log("=== IPC: open-scanner called ===");
    createScannerWindow();
  });
  electron.ipcMain.handle("close-scanner", () => {
    closeScannerWindow();
  });
  electron.app.on("activate", () => {
    if (electron.BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});
electron.app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    electron.app.quit();
  }
});
electron.app.on("will-quit", () => {
  stopBackend();
});
