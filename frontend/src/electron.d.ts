interface ElectronAPI {
  platform: string
  openScanner: () => Promise<void>
  closeScanner: () => Promise<void>
}

declare global {
  interface Window {
    electronAPI?: ElectronAPI
  }
}

export {}
