import { contextBridge, ipcRenderer } from "electron";

// Expose protected methods that allow the renderer process to use
// the ipcRenderer without exposing the entire object
contextBridge.exposeInMainWorld("sena", {
  // Window management
  openWindow: (feature: string, title: string) =>
    ipcRenderer.invoke("open-window", feature, title),

  closeWindow: (windowId: string) =>
    ipcRenderer.invoke("close-window", windowId),

  minimizeWindow: () => ipcRenderer.invoke("minimize-window"),

  maximizeWindow: () => ipcRenderer.invoke("maximize-window"),
  setWindowPinned: (pinned: boolean) =>
    ipcRenderer.invoke("set-window-pinned", pinned),

  quitApp: () => ipcRenderer.invoke("quit-app"),

  // Server management
  getServerStatus: () => ipcRenderer.invoke("get-server-status"),
  getApiBaseUrl: () => ipcRenderer.invoke("get-api-base-url"),
  getWsBaseUrl: () => ipcRenderer.invoke("get-ws-base-url"),
  signalLoaderReady: () => ipcRenderer.invoke("signal-loader-ready"),
  openSetupWindow: () => ipcRenderer.invoke("open-setup-window"),
  signalSetupComplete: () => ipcRenderer.invoke("signal-setup-complete"),

  // Event listeners
  onServerLog: (callback: (message: string) => void) => {
    ipcRenderer.on("server-log", (_event, message: string) =>
      callback(message),
    );
  },

  onStartupStep: (callback: (data: { step: string }) => void) => {
    ipcRenderer.on("startup-step", (_event, data: { step: string }) =>
      callback(data),
    );
  },

  onStartupError: (callback: (data: { error: string }) => void) => {
    ipcRenderer.on("startup-error", (_event, data: { error: string }) =>
      callback(data),
    );
  },

  onWindowClosed: (callback: (windowId: string) => void) => {
    ipcRenderer.on("window-closed", (_event, windowId: string) =>
      callback(windowId),
    );
  },

  getHotkey: () => ipcRenderer.invoke("get-hotkey"),

  setHotkey: (key: string) => ipcRenderer.invoke("set-hotkey", key),

  // Remove listeners
  removeListener: (channel: string) => {
    ipcRenderer.removeAllListeners(channel);
  },
});
