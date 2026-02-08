import { contextBridge, ipcRenderer } from 'electron'

// Expose protected methods that allow the renderer process to use
// the ipcRenderer without exposing the entire object
contextBridge.exposeInMainWorld('electronAPI', {
  platform: process.platform,
  openScanner: () => ipcRenderer.invoke('open-scanner'),
  closeScanner: () => ipcRenderer.invoke('close-scanner'),
})

declare global {
  interface Window {
    electronAPI: {
      platform: string
      openScanner: () => Promise<void>
      closeScanner: () => Promise<void>
    }
  }
}
