import {
  app,
  BrowserWindow,
  ipcMain,
  screen,
  net,
  globalShortcut,
} from "electron";
import { spawn, ChildProcess } from "child_process";
import fs from "fs";
import path from "path";
import { parse as parseYaml } from "yaml";

// Window management
const windows = new Map<string, BrowserWindow>();
const floatingOrder: string[] = [];
const floatingMoved = new Set<string>();
let serverProcess: ChildProcess | null = null;
let isDev = false;
let currentHotkey = "Home";
let loaderReadyResolver: (() => void) | null = null;
let setupWindowOpen = false;

// Server configuration
type ServerConfig = {
  host: string;
  port: number;
};

const DEFAULT_SERVER_CONFIG: ServerConfig = {
  host: "127.0.0.1",
  port: 8000,
};

function readSettingsConfig(projectRoot: string): ServerConfig {
  const candidates = [
    path.join(projectRoot, "config", "settings.yaml"),
    path.join(projectRoot, "src", "config", "settings.yaml"),
  ];

  for (const candidate of candidates) {
    if (!fs.existsSync(candidate)) continue;

    try {
      const raw = fs.readFileSync(candidate, "utf-8");
      const parsed = parseYaml(raw) as {
        api?: { host?: string; port?: number };
      };

      const host = parsed?.api?.host;
      const port = parsed?.api?.port;

      return {
        host: typeof host === "string" ? host : DEFAULT_SERVER_CONFIG.host,
        port: typeof port === "number" ? port : DEFAULT_SERVER_CONFIG.port,
      };
    } catch {
      return DEFAULT_SERVER_CONFIG;
    }
  }

  return DEFAULT_SERVER_CONFIG;
}

const SERVER_CONFIG = readSettingsConfig(resolveProjectRoot());
const SERVER_PORT = SERVER_CONFIG.port;
const SERVER_HOST = SERVER_CONFIG.host;
const SERVER_URL = `http://${SERVER_HOST}:${SERVER_PORT}`;
const WS_BASE_URL = `ws://${SERVER_HOST}:${SERVER_PORT}`;

/**
 * Check if server is healthy
 */
async function checkServerHealth(): Promise<boolean> {
  try {
    const request = net.request(`${SERVER_URL}/health`);

    return new Promise((resolve) => {
      request.on("response", (response) => {
        resolve(response.statusCode === 200);
      });

      request.on("error", () => {
        resolve(false);
      });

      // Timeout after 2 seconds
      setTimeout(() => {
        request.abort();
        resolve(false);
      }, 2000);

      request.end();
    });
  } catch {
    return false;
  }
}

/**
 * Start the Python API server
 */
function startServer(): Promise<void> {
  return new Promise((resolve, reject) => {
    const projectRoot = resolveProjectRoot();
    const pythonPath = getPythonPath(projectRoot);

    serverProcess = spawn(
      pythonPath,
      [
        "-m",
        "uvicorn",
        "src.api.server:app",
        "--host",
        SERVER_HOST,
        "--port",
        SERVER_PORT.toString(),
      ],
      {
        cwd: projectRoot,
        stdio: ["ignore", "pipe", "pipe"],
      },
    );

    // Send stdout to loader window
    serverProcess.stdout?.on("data", (data) => {
      const message = data.toString();
      sendToWindow("loader", "server-log", message);
    });

    // Send stderr to loader window
    serverProcess.stderr?.on("data", (data) => {
      const message = data.toString();
      sendToWindow("loader", "server-log", message);
    });

    serverProcess.on("error", (error) => {
      reject(error);
    });

    // Wait for server to be ready
    const checkInterval = setInterval(async () => {
      const isHealthy = await checkServerHealth();
      if (isHealthy) {
        clearInterval(checkInterval);
        resolve();
      }
    }, 500);
  });
}

function getPythonPath(projectRoot: string): string {
  const venvBinDir = process.platform === "win32" ? "Scripts" : "bin";
  const pythonBinary = process.platform === "win32" ? "python.exe" : "python";
  return path.join(projectRoot, ".venv", venvBinDir, pythonBinary);
}

function resolveProjectRoot(): string {
  const candidates = [
    path.resolve(__dirname, "../../../../"),
    path.resolve(__dirname, "../../../.."),
    path.resolve(process.cwd(), "../../.."),
    path.resolve(process.cwd(), ".."),
  ];

  for (const candidate of candidates) {
    if (fs.existsSync(getPythonPath(candidate))) {
      return candidate;
    }
  }

  return path.resolve(__dirname, "../../../../");
}

/**
 * Stop the Python API server
 */
function stopServer() {
  if (serverProcess) {
    serverProcess.kill();
    serverProcess = null;
  }
}

/**
 * Send message to specific window
 */
function sendToWindow(windowId: string, channel: string, data: any) {
  const window = windows.get(windowId);
  if (window && !window.isDestroyed()) {
    window.webContents.send(channel, data);
  }
}

/**
 * Create loader window
 */
function createLoaderWindow() {
  const loaderWindow = new BrowserWindow({
    width: 600,
    height: 420,
    frame: false,
    transparent: true,
    backgroundColor: "#00000000",
    resizable: false,
    alwaysOnTop: true,
    focusable: true,
    acceptFirstMouse: true,
    center: true,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      backgroundThrottling: false,
      preload: path.join(__dirname, "preload.js"),
    },
  });

  if (isDev) {
    loaderWindow.loadURL("http://localhost:5173/#/loader");
  } else {
    loaderWindow.loadFile(path.join(__dirname, "../dist/index.html"), {
      hash: "/loader",
    });
  }

  windows.set("loader", loaderWindow);

  loaderWindow.setAlwaysOnTop(true, "screen-saver");
  loaderWindow.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true });

  loaderWindow.on("closed", () => {
    windows.delete("loader");
  });

  return loaderWindow;
}

/**
 * Create setup window for initial LLM configuration
 */
function createSetupWindow() {
  const existingWindow = windows.get("setup");
  if (existingWindow && !existingWindow.isDestroyed()) {
    existingWindow.focus();
    return existingWindow;
  }

  const setupWindow = new BrowserWindow({
    width: 660,
    height: 620,
    frame: false,
    transparent: true,
    backgroundColor: "#00000000",
    resizable: true,
    minWidth: 560,
    minHeight: 520,
    alwaysOnTop: true,
    focusable: true,
    acceptFirstMouse: true,
    center: true,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      backgroundThrottling: false,
      preload: path.join(__dirname, "preload.js"),
    },
  });

  setupWindow.setAlwaysOnTop(true, "screen-saver");
  setupWindow.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true });

  if (isDev) {
    setupWindow.loadURL("http://localhost:5173/#/setup");
  } else {
    setupWindow.loadFile(path.join(__dirname, "../dist/index.html"), {
      hash: "/setup",
    });
  }

  windows.set("setup", setupWindow);
  setupWindowOpen = true;

  setupWindow.on("closed", () => {
    windows.delete("setup");
    setupWindowOpen = false;
  });

  return setupWindow;
}

/**
 * Create dashboard hotbar window
 */
function createDashboardWindow() {
  const { width, height } = screen.getPrimaryDisplay().workAreaSize;

  const dashboardWindow = new BrowserWindow({
    width: 500,
    height: 80,
    x: Math.floor((width - 500) / 2),
    y: height - 100,
    frame: false,
    transparent: true,
    resizable: false,
    alwaysOnTop: true,
    focusable: true,
    acceptFirstMouse: true,
    skipTaskbar: true,
    autoHideMenuBar: true,
    ...(process.platform === "win32"
      ? {
          titleBarStyle: "hidden",
          titleBarOverlay: false,
        }
      : {}),
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, "preload.js"),
    },
  });

  dashboardWindow.setMenuBarVisibility(false);
  dashboardWindow.setAutoHideMenuBar(true);
  dashboardWindow.setAlwaysOnTop(true, "screen-saver");
  dashboardWindow.setVisibleOnAllWorkspaces(true, {
    visibleOnFullScreen: true,
  });

  if (isDev) {
    dashboardWindow.loadURL("http://localhost:5173/#/dashboard");
  } else {
    dashboardWindow.loadFile(path.join(__dirname, "../dist/index.html"), {
      hash: "/dashboard",
    });
  }

  windows.set("dashboard", dashboardWindow);

  dashboardWindow.on("closed", () => {
    windows.delete("dashboard");
  });

  return dashboardWindow;
}

/**
 * Create floating window for specific feature
 */
function createFloatingWindow(feature: string, title: string) {
  const existingWindow = windows.get(feature);
  if (existingWindow && !existingWindow.isDestroyed()) {
    existingWindow.focus();
    return existingWindow;
  }

  const floatingWindow = new BrowserWindow({
    width: 700,
    height: 550,
    frame: false,
    transparent: true,
    backgroundColor: "#00000000",
    alwaysOnTop: true,
    focusable: true,
    acceptFirstMouse: true,
    show: false,
    ...(process.platform === "win32"
      ? {
          titleBarStyle: "hidden",
          titleBarOverlay: false,
        }
      : {}),
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, "preload.js"),
    },
  });

  floatingWindow.setAlwaysOnTop(true, "screen-saver");
  floatingWindow.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true });

  if (isDev) {
    floatingWindow.loadURL(`http://localhost:5173/#/${feature}`);
  } else {
    floatingWindow.loadFile(path.join(__dirname, "../dist/index.html"), {
      hash: `/${feature}`,
    });
  }

  // Show window after content loads
  floatingWindow.once("ready-to-show", () => {
    floatingWindow.show();
    floatingWindow.focus();
  });

  windows.set(feature, floatingWindow);
  floatingOrder.push(feature);
  layoutFloatingWindows();

  floatingWindow.on("closed", () => {
    windows.delete(feature);
    floatingMoved.delete(feature);
    const index = floatingOrder.indexOf(feature);
    if (index >= 0) {
      floatingOrder.splice(index, 1);
      layoutFloatingWindows();
    }
    // Notify dashboard that this window closed
    sendToWindow("dashboard", "window-closed", feature);
  });

  // Track manual window movement
  trackWindowMovement(feature, floatingWindow);

  return floatingWindow;
}

/**
 * Layout floating windows in a simple grid based on count
 */
function layoutFloatingWindows() {
  const { width, height } = screen.getPrimaryDisplay().workAreaSize;
  const gap = 24;
  const margin = 32;
  const columns = 2;

  floatingOrder.forEach((id, index) => {
    const win = windows.get(id);
    if (!win || win.isDestroyed() || floatingMoved.has(id)) return;

    const bounds = win.getBounds();
    const col = index % columns;
    const row = Math.floor(index / columns);

    const x = Math.min(
      margin + col * (bounds.width + gap),
      Math.max(margin, width - bounds.width - margin),
    );
    const y = Math.min(
      margin + row * (bounds.height + gap),
      Math.max(margin, height - bounds.height - margin),
    );

    win.setBounds({ x, y, width: bounds.width, height: bounds.height });
  });
}

/**
 * Track when user manually moves a window
 */
function trackWindowMovement(windowId: string, win: BrowserWindow) {
  let isMoving = false;

  win.on("will-move", () => {
    isMoving = true;
  });

  win.on("moved", () => {
    if (isMoving) {
      floatingMoved.add(windowId);
      isMoving = false;
    }
  });
}
/**
 * Application lifecycle
 */
app.whenReady().then(async () => {
  isDev = !app.isPackaged;

  // Create loader window
  const loaderWindow = createLoaderWindow();
  const loaderStart = Date.now();
  const loaderReadyPromise = new Promise<void>((resolve) => {
    loaderReadyResolver = resolve;
  });

  try {
    // Check if server is already running
    const isRunning = await checkServerHealth();

    if (!isRunning) {
      sendToWindow("loader", "startup-step", {
        step: "Starting Python server...",
      });
      await startServer();
    } else {
      sendToWindow("loader", "startup-step", {
        step: "Server already running",
      });
    }

    // Wait a moment for UI effect
    await new Promise((resolve) => setTimeout(resolve, 1000));

    sendToWindow("loader", "startup-step", { step: "Server ready!" });
    await new Promise((resolve) => setTimeout(resolve, 500));

    // Keep loader visible for at least 5 seconds
    const elapsed = Date.now() - loaderStart;
    if (elapsed < 5000) {
      await new Promise((resolve) => setTimeout(resolve, 5000 - elapsed));
    }

    await loaderReadyPromise;

    // Close loader and open dashboard
    loaderWindow.close();
    const dashboardWindow = createDashboardWindow();

    // Register the initial hotkey (Home key by default)
    globalShortcut.register(currentHotkey, () => {
      if (dashboardWindow.isVisible()) {
        dashboardWindow.hide();
      } else {
        dashboardWindow.show();
        dashboardWindow.focus();
      }
    });
  } catch (error) {
    sendToWindow("loader", "startup-error", {
      error: error instanceof Error ? error.message : "Unknown error",
    });
  }
});

app.on("window-all-closed", () => {
  stopServer();
  app.quit();
});

app.on("before-quit", () => {
  stopServer();
});

/**
 * IPC Handlers
 */

ipcMain.handle("signal-loader-ready", () => {
  if (loaderReadyResolver) {
    loaderReadyResolver();
    loaderReadyResolver = null;
  }
  return true;
});

// Open setup window (called by loader when settings are incomplete)
ipcMain.handle("open-setup-window", () => {
  if (!setupWindowOpen) {
    createSetupWindow();
  }
  return true;
});

// Setup complete (called by setup window after settings are saved)
ipcMain.handle("signal-setup-complete", () => {
  const setupWindow = windows.get("setup");
  if (setupWindow && !setupWindow.isDestroyed()) {
    setupWindow.close();
  }

  // Boot into the dashboard just like the loader does after a successful start
  if (!windows.get("dashboard")) {
    const dashboardWindow = createDashboardWindow();

    globalShortcut.register(currentHotkey, () => {
      if (dashboardWindow.isVisible()) {
        dashboardWindow.hide();
      } else {
        dashboardWindow.show();
        dashboardWindow.focus();
      }
    });
  }

  return true;
});

// Open floating window
ipcMain.handle("open-window", (event, feature: string, title: string) => {
  createFloatingWindow(feature, title);
});

// Close window
ipcMain.handle("close-window", (event, windowId: string) => {
  const window = windows.get(windowId);
  if (window && !window.isDestroyed()) {
    window.close();
  }
});

// Minimize window
ipcMain.handle("minimize-window", (event) => {
  const window = BrowserWindow.fromWebContents(event.sender);
  window?.minimize();
});

// Maximize/restore window
ipcMain.handle("maximize-window", (event) => {
  const window = BrowserWindow.fromWebContents(event.sender);
  if (window?.isMaximized()) {
    window.restore();
  } else {
    window?.maximize();
  }
});

// Toggle always-on-top state for floating window
ipcMain.handle("set-window-pinned", (event, pinned: boolean) => {
  const window = BrowserWindow.fromWebContents(event.sender);
  if (!window) return;
  window.setAlwaysOnTop(pinned, pinned ? "screen-saver" : "normal");
  window.setVisibleOnAllWorkspaces(pinned, { visibleOnFullScreen: pinned });
});

// Get server status
ipcMain.handle("get-server-status", async () => {
  return await checkServerHealth();
});

// Get API base URL
ipcMain.handle("get-api-base-url", async () => {
  return SERVER_URL;
});

// Get WebSocket base URL
ipcMain.handle("get-ws-base-url", async () => {
  return WS_BASE_URL;
});

// Get current hotkey
ipcMain.handle("get-hotkey", async () => {
  return currentHotkey;
});

// Set and register new hotkey
ipcMain.handle("set-hotkey", async (_event, key: string) => {
  // Unregister old hotkey if it exists
  if (currentHotkey) {
    globalShortcut.unregister(currentHotkey);
  }

  // Store the new hotkey
  currentHotkey = key;

  // Register new hotkey to toggle dashboard visibility
  const dashboardWindow = windows.get("dashboard");
  if (dashboardWindow) {
    globalShortcut.register(currentHotkey, () => {
      if (dashboardWindow.isVisible()) {
        dashboardWindow.hide();
      } else {
        dashboardWindow.show();
        dashboardWindow.focus();
      }
    });
  }

  return true;
});

// Quit application
ipcMain.handle("quit-app", () => {
  app.quit();
});
