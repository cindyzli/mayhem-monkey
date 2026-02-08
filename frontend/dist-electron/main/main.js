"use strict";
const electron = require("electron");
const path = require("path");
let scannerWindow = null;
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
    mainWindow.webContents.openDevTools();
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
    scannerWindow?.webContents.openDevTools();
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
