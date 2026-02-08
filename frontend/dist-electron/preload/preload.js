"use strict";
const electron = require("electron");
electron.contextBridge.exposeInMainWorld("electronAPI", {
  platform: process.platform,
  openScanner: () => electron.ipcRenderer.invoke("open-scanner"),
  closeScanner: () => electron.ipcRenderer.invoke("close-scanner")
});
