// Type definitions for window.sena API exposed via preload
export interface SenaAPI {
  openWindow: (feature: string, title: string) => Promise<void>
  closeWindow: (windowId: string) => Promise<void>
  minimizeWindow: () => Promise<void>
  maximizeWindow: () => Promise<void>
  setWindowPinned: (pinned: boolean) => Promise<void>
  quitApp: () => Promise<void>
  getServerStatus: () => Promise<boolean>
  onServerLog: (callback: (message: string) => void) => void
  onStartupStep: (callback: (data: { step: string }) => void) => void
  onStartupError: (callback: (data: { error: string }) => void) => void
  onWindowClosed: (callback: (windowId: string) => void) => void
  getHotkey: () => Promise<string>
  setHotkey: (key: string) => Promise<void>
  setWindowPinned: (pinned: boolean) => Promise<void>
  removeListener: (channel: string) => void
}

declare global {
  interface Window {
    sena: SenaAPI
  }
}

export {}
