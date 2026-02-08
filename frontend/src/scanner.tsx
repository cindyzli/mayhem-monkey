import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { VulnerabilityScannerWindow } from './components/VulnerabilityScannerWindow.tsx'
import './index.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <VulnerabilityScannerWindow />
  </StrictMode>,
)
