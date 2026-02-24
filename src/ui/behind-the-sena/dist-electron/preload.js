"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
const electron_1 = require("electron");
// Expose protected methods that allow the renderer process to use
// the ipcRenderer without exposing the entire object
electron_1.contextBridge.exposeInMainWorld("sena", {
    // Window management
    openWindow: (feature, title) => electron_1.ipcRenderer.invoke("open-window", feature, title),
    closeWindow: (windowId) => electron_1.ipcRenderer.invoke("close-window", windowId),
    minimizeWindow: () => electron_1.ipcRenderer.invoke("minimize-window"),
    maximizeWindow: () => electron_1.ipcRenderer.invoke("maximize-window"),
    setWindowPinned: (pinned) => electron_1.ipcRenderer.invoke("set-window-pinned", pinned),
    quitApp: () => electron_1.ipcRenderer.invoke("quit-app"),
    // Server management
    getServerStatus: () => electron_1.ipcRenderer.invoke("get-server-status"),
    getApiBaseUrl: () => electron_1.ipcRenderer.invoke("get-api-base-url"),
    getWsBaseUrl: () => electron_1.ipcRenderer.invoke("get-ws-base-url"),
    signalLoaderReady: () => electron_1.ipcRenderer.invoke("signal-loader-ready"),
    openSetupWindow: () => electron_1.ipcRenderer.invoke("open-setup-window"),
    signalSetupComplete: () => electron_1.ipcRenderer.invoke("signal-setup-complete"),
    // Event listeners
    onServerLog: (callback) => {
        electron_1.ipcRenderer.on("server-log", (_event, message) => callback(message));
    },
    onStartupStep: (callback) => {
        electron_1.ipcRenderer.on("startup-step", (_event, data) => callback(data));
    },
    onStartupError: (callback) => {
        electron_1.ipcRenderer.on("startup-error", (_event, data) => callback(data));
    },
    onWindowClosed: (callback) => {
        electron_1.ipcRenderer.on("window-closed", (_event, windowId) => callback(windowId));
    },
    getHotkey: () => electron_1.ipcRenderer.invoke("get-hotkey"),
    setHotkey: (key) => electron_1.ipcRenderer.invoke("set-hotkey", key),
    // Remove listeners
    removeListener: (channel) => {
        electron_1.ipcRenderer.removeAllListeners(channel);
    },
});
