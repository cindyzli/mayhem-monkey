import { contextBridge } from 'electron'

// Expose protected methods that allow the renderer process to use
// the ipcRenderer without exposing the entire object
contextBridge.exposeInMainWorld('electronAPI', {
  // Add your API methods here
  platform: process.platform,
})

// TypeScript support for exposed API
declare global {
  interface Window {
    electronAPI: {
      platform: string
    }
  }
}
