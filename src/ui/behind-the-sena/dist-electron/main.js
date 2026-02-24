"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const electron_1 = require("electron");
const child_process_1 = require("child_process");
const fs_1 = __importDefault(require("fs"));
const path_1 = __importDefault(require("path"));
const yaml_1 = require("yaml");
// Window management
const windows = new Map();
const floatingOrder = [];
const floatingMoved = new Set();
const windowPreExpandBounds = new Map();
let activeResize = null;
function stopActiveResize() {
    if (!activeResize)
        return;
    clearInterval(activeResize.intervalId);
    clearTimeout(activeResize.safetyTimeout);
    activeResize = null;
}
/**
 * Re-assert always-on-top on every blur so Windows 11 cannot lower the
 * window's z-order when it loses focus (taskbar thumbnails, Alt-Tab overlay,
 * Snap Assist, etc. all trigger a transient z-order drop on unfocus).
 *
 * Strategy:
 *  1. Immediately cycle off→on to invalidate the stale z-order entry.
 *  2. After a short delay, call moveTop() to push the window to the very top
 *     of the z-stack once DWM has finished processing the focus change.
 */
function keepOnTop(win) {
    win.setAlwaysOnTop(true, "screen-saver");
    win.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true });
    win.on("blur", () => {
        if (win.isDestroyed())
            return;
        // Cycle off→on forces DWM to refresh the z-order entry immediately.
        win.setAlwaysOnTop(false);
        win.setAlwaysOnTop(true, "screen-saver");
        // After DWM finishes settling the focus change, push to top again.
        setTimeout(() => {
            if (!win.isDestroyed()) {
                win.setAlwaysOnTop(true, "screen-saver");
                win.moveTop();
            }
        }, 50);
    });
}
/**
 * Resolve the best available icon for the current platform.
 *   Windows  → .ico  (multi-size, required for taskbar/Alt-Tab/shortcuts)
 *   macOS    → .icns (required for Dock / packaged .app)
 *   Linux    → .png  (any size; 256×256 or 512×512 recommended)
 *
 * Falls back to the PNG on any platform if the preferred format is absent
 * (e.g. during development before packaging icons are generated).
 */
/**
 * Load the best available icon as a NativeImage, with fallback chain:
 *   Windows  → .ico → .png
 *   macOS    → .icns → .png
 *   Linux    → .png
 *
 * Always returns a NativeImage (may be empty if all files are missing/corrupt).
 * Using a pre-loaded NativeImage instead of a string path is more reliable
 * because Electron validates the image once here rather than silently falling
 * back to the default Electron icon at window-creation time.
 */
function loadAppIcon() {
    const base = path_1.default.join(__dirname, "../assets");
    const candidates = [];
    if (process.platform === "win32") {
        candidates.push(path_1.default.join(base, "sena-logo.ico"));
    }
    else if (process.platform === "darwin") {
        candidates.push(path_1.default.join(base, "sena-logo.icns"));
    }
    // PNG is the universal fallback for all platforms
    candidates.push(path_1.default.join(base, "sena-logo.png"));
    for (const candidate of candidates) {
        if (fs_1.default.existsSync(candidate)) {
            const img = electron_1.nativeImage.createFromPath(candidate);
            if (!img.isEmpty())
                return img;
        }
    }
    return electron_1.nativeImage.createEmpty();
}
const APP_ICON = loadAppIcon();
let serverProcess = null;
let isDev = false;
/**
 * Per-platform icon bootstrap.
 * Must be called after app.whenReady() so the dock/taskbar APIs are available.
 */
function bootstrapAppIcon() {
    if (process.platform === "win32") {
        // Sets the AUMID so Windows groups all windows under a single taskbar
        // button and associates the correct icon with jump-lists / shortcuts.
        electron_1.app.setAppUserModelId("com.sena.app");
    }
    else if (process.platform === "darwin") {
        if (!APP_ICON.isEmpty()) {
            electron_1.app.dock?.setIcon(APP_ICON);
        }
    }
}
/**
 * Apply the custom app icon to a BrowserWindow.
 * Calling win.setIcon() explicitly after construction is the most reliable way
 * to set the icon shown in Alt-Tab, the taskbar button, and the window
 * chrome — even in development mode where the Electron executable itself
 * carries its own default icon.
 */
function applyWindowIcon(win) {
    if (!APP_ICON.isEmpty()) {
        win.setIcon(APP_ICON);
    }
}
let currentHotkey = "Home";
// Simulates keyup behaviour for globalShortcut (which only fires on keydown/repeat).
// Each keydown/repeat resets the timer; the toggle fires 150 ms after the LAST
// event, i.e. once the key has actually been released.
let toggleTimeout = null;
let loaderReadyResolver = null;
let setupWindowOpen = false;
const DEFAULT_SERVER_CONFIG = {
    host: "127.0.0.1",
    port: 8000,
};
function readSettingsConfig(projectRoot) {
    const candidates = [
        path_1.default.join(projectRoot, "config", "settings.yaml"),
        path_1.default.join(projectRoot, "src", "config", "settings.yaml"),
    ];
    for (const candidate of candidates) {
        if (!fs_1.default.existsSync(candidate))
            continue;
        try {
            const raw = fs_1.default.readFileSync(candidate, "utf-8");
            const parsed = (0, yaml_1.parse)(raw);
            const host = parsed?.api?.host;
            const port = parsed?.api?.port;
            return {
                host: typeof host === "string" ? host : DEFAULT_SERVER_CONFIG.host,
                port: typeof port === "number" ? port : DEFAULT_SERVER_CONFIG.port,
            };
        }
        catch {
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
async function checkServerHealth() {
    try {
        const request = electron_1.net.request(`${SERVER_URL}/health`);
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
    }
    catch {
        return false;
    }
}
/**
 * Start the Python API server
 */
function startServer() {
    return new Promise((resolve, reject) => {
        const projectRoot = resolveProjectRoot();
        const pythonPath = getPythonPath(projectRoot);
        serverProcess = (0, child_process_1.spawn)(pythonPath, [
            "-m",
            "uvicorn",
            "src.api.server:app",
            "--host",
            SERVER_HOST,
            "--port",
            SERVER_PORT.toString(),
        ], {
            cwd: projectRoot,
            stdio: ["ignore", "pipe", "pipe"],
        });
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
function getPythonPath(projectRoot) {
    const venvBinDir = process.platform === "win32" ? "Scripts" : "bin";
    const pythonBinary = process.platform === "win32" ? "python.exe" : "python";
    return path_1.default.join(projectRoot, ".venv", venvBinDir, pythonBinary);
}
function resolveProjectRoot() {
    const candidates = [
        path_1.default.resolve(__dirname, "../../../../"),
        path_1.default.resolve(__dirname, "../../../.."),
        path_1.default.resolve(process.cwd(), "../../.."),
        path_1.default.resolve(process.cwd(), ".."),
    ];
    for (const candidate of candidates) {
        if (fs_1.default.existsSync(getPythonPath(candidate))) {
            return candidate;
        }
    }
    return path_1.default.resolve(__dirname, "../../../../");
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
function sendToWindow(windowId, channel, data) {
    const window = windows.get(windowId);
    if (window && !window.isDestroyed()) {
        window.webContents.send(channel, data);
    }
}
/**
 * Create loader window
 */
function createLoaderWindow() {
    const loaderWindow = new electron_1.BrowserWindow({
        width: 600,
        height: 420,
        frame: false,
        thickFrame: false,
        transparent: true,
        backgroundColor: "#00000000",
        // Explicitly disable Windows 11 Mica/Acrylic background material.
        // Without this, DWM applies a semi-transparent gray/frosted effect to the
        // entire window surface on Windows 11, which appears as a gray frame around
        // the loader card even though the React content is bg-transparent.
        backgroundMaterial: "none",
        hasShadow: false,
        resizable: false,
        alwaysOnTop: true,
        focusable: true,
        acceptFirstMouse: true,
        skipTaskbar: true,
        center: true,
        icon: APP_ICON,
        // Hide until content is painted so no gray Chromium background flashes.
        show: false,
        webPreferences: {
            nodeIntegration: false,
            contextIsolation: true,
            backgroundThrottling: false,
            preload: path_1.default.join(__dirname, "preload.js"),
        },
    });
    keepOnTop(loaderWindow);
    loaderWindow.once("ready-to-show", () => {
        applyWindowIcon(loaderWindow);
        loaderWindow.show();
    });
    if (isDev) {
        loaderWindow.loadURL("http://localhost:5173/#/loader");
    }
    else {
        loaderWindow.loadFile(path_1.default.join(__dirname, "../dist/index.html"), {
            hash: "/loader",
        });
    }
    windows.set("loader", loaderWindow);
    keepOnTop(loaderWindow);
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
    const setupWindow = new electron_1.BrowserWindow({
        width: 660,
        height: 620,
        frame: false,
        thickFrame: false,
        transparent: true,
        backgroundColor: "#00000000",
        resizable: true,
        minWidth: 560,
        minHeight: 520,
        alwaysOnTop: true,
        focusable: true,
        acceptFirstMouse: true,
        skipTaskbar: true,
        center: true,
        icon: APP_ICON,
        // Hide until content is painted so no gray Chromium background flashes.
        show: false,
        webPreferences: {
            nodeIntegration: false,
            contextIsolation: true,
            backgroundThrottling: false,
            preload: path_1.default.join(__dirname, "preload.js"),
        },
    });
    keepOnTop(setupWindow);
    setupWindow.once("ready-to-show", () => {
        setupWindow.show();
    });
    if (isDev) {
        setupWindow.loadURL("http://localhost:5173/#/setup");
    }
    else {
        setupWindow.loadFile(path_1.default.join(__dirname, "../dist/index.html"), {
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
    const { width, height } = electron_1.screen.getPrimaryDisplay().workAreaSize;
    const dashboardWindow = new electron_1.BrowserWindow({
        width: 500,
        // Extra height above the hotbar bar gives the button tooltips room to render
        // without being clipped by the window edge.
        height: 110,
        x: Math.floor((width - 500) / 2),
        // Keep the same ~20 px bottom gap: y + height = workAreaHeight - 20
        y: height - 130,
        frame: false,
        thickFrame: false,
        transparent: true,
        backgroundColor: "#00000000",
        resizable: false,
        alwaysOnTop: true,
        focusable: true,
        acceptFirstMouse: true,
        skipTaskbar: true,
        autoHideMenuBar: true,
        icon: APP_ICON,
        // Hide until content is painted so no gray Chromium background flashes.
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
            preload: path_1.default.join(__dirname, "preload.js"),
        },
    });
    dashboardWindow.setMenuBarVisibility(false);
    dashboardWindow.setAutoHideMenuBar(true);
    keepOnTop(dashboardWindow);
    dashboardWindow.once("ready-to-show", () => {
        applyWindowIcon(dashboardWindow);
        dashboardWindow.show();
    });
    if (isDev) {
        dashboardWindow.loadURL("http://localhost:5173/#/dashboard");
    }
    else {
        dashboardWindow.loadFile(path_1.default.join(__dirname, "../dist/index.html"), {
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
function createFloatingWindow(feature, title) {
    const existingWindow = windows.get(feature);
    if (existingWindow && !existingWindow.isDestroyed()) {
        existingWindow.focus();
        return existingWindow;
    }
    const floatingWindow = new electron_1.BrowserWindow({
        width: 700,
        height: 550,
        minWidth: 550,
        minHeight: 420,
        frame: false,
        // thickFrame: true keeps WS_THICKFRAME on the window so Windows owns all
        // resize hit-testing and drag operations natively. Setting it to false
        // forced us to implement custom IPC-based resize which was unreliable on
        // transparent windows. With thickFrame: true the resize border is
        // invisible (covered by our dark background) but fully functional.
        thickFrame: false,
        transparent: true,
        // Use the actual background colour instead of fully-transparent #00000000.
        // On Windows, a zero-alpha backgroundColor tells DWM the entire surface has
        // no alpha before Chromium finishes its first paint, so the window never
        // gets composited and appears completely invisible. A solid base colour
        // forces DWM to composite the window correctly from the very first frame;
        // the CSS html/body backgrounds stay transparent so rounded corners still
        // show through as intended.
        backgroundColor: "#0A0E27",
        alwaysOnTop: true,
        focusable: true,
        acceptFirstMouse: true,
        icon: APP_ICON,
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
            preload: path_1.default.join(__dirname, "preload.js"),
        },
    });
    keepOnTop(floatingWindow);
    if (isDev) {
        floatingWindow.loadURL(`http://localhost:5173/#/${feature}`);
    }
    else {
        floatingWindow.loadFile(path_1.default.join(__dirname, "../dist/index.html"), {
            hash: `/${feature}`,
        });
    }
    // Show window after content loads
    floatingWindow.once("ready-to-show", () => {
        applyWindowIcon(floatingWindow);
        floatingWindow.show();
        floatingWindow.focus();
    });
    windows.set(feature, floatingWindow);
    floatingOrder.push(feature);
    layoutFloatingWindows();
    floatingWindow.on("closed", () => {
        windows.delete(feature);
        floatingMoved.delete(feature);
        windowPreExpandBounds.delete(floatingWindow.id);
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
    const { width, height } = electron_1.screen.getPrimaryDisplay().workAreaSize;
    const gap = 24;
    const margin = 32;
    const columns = 2;
    floatingOrder.forEach((id, index) => {
        const win = windows.get(id);
        if (!win || win.isDestroyed() || floatingMoved.has(id))
            return;
        const bounds = win.getBounds();
        const col = index % columns;
        const row = Math.floor(index / columns);
        const x = Math.min(margin + col * (bounds.width + gap), Math.max(margin, width - bounds.width - margin));
        const y = Math.min(margin + row * (bounds.height + gap), Math.max(margin, height - bounds.height - margin));
        win.setBounds({ x, y, width: bounds.width, height: bounds.height });
    });
}
/**
 * Track when user manually moves a window
 */
function trackWindowMovement(windowId, win) {
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
electron_1.app.whenReady().then(async () => {
    isDev = !electron_1.app.isPackaged;
    // Apply platform-specific icon to taskbar / Dock before any window opens.
    bootstrapAppIcon();
    // Create loader window
    const loaderWindow = createLoaderWindow();
    const loaderStart = Date.now();
    const loaderReadyPromise = new Promise((resolve) => {
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
        }
        else {
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
        // Register the initial hotkey (Home key by default).
        // Defer the toggle until 150 ms after the last keydown so the hotbar only
        // reacts when the key is fully released (key-repeat events arrive every
        // ~30-50 ms, so a 150 ms quiet period reliably means the key is up).
        electron_1.globalShortcut.register(currentHotkey, () => {
            if (toggleTimeout)
                clearTimeout(toggleTimeout);
            toggleTimeout = setTimeout(() => {
                toggleTimeout = null;
                if (dashboardWindow.isVisible()) {
                    dashboardWindow.hide();
                }
                else {
                    dashboardWindow.show();
                    dashboardWindow.focus();
                }
            }, 150);
        });
    }
    catch (error) {
        sendToWindow("loader", "startup-error", {
            error: error instanceof Error ? error.message : "Unknown error",
        });
    }
});
electron_1.app.on("window-all-closed", () => {
    stopServer();
    electron_1.app.quit();
});
electron_1.app.on("before-quit", () => {
    stopServer();
});
/**
 * IPC Handlers
 */
electron_1.ipcMain.handle("signal-loader-ready", () => {
    if (loaderReadyResolver) {
        loaderReadyResolver();
        loaderReadyResolver = null;
    }
    return true;
});
// Open setup window (called by loader when settings are incomplete)
electron_1.ipcMain.handle("open-setup-window", () => {
    if (!setupWindowOpen) {
        createSetupWindow();
    }
    return true;
});
// Setup complete (called by setup window after settings are saved)
electron_1.ipcMain.handle("signal-setup-complete", () => {
    const setupWindow = windows.get("setup");
    if (setupWindow && !setupWindow.isDestroyed()) {
        setupWindow.close();
    }
    // Boot into the dashboard just like the loader does after a successful start
    if (!windows.get("dashboard")) {
        const dashboardWindow = createDashboardWindow();
        electron_1.globalShortcut.register(currentHotkey, () => {
            if (toggleTimeout)
                clearTimeout(toggleTimeout);
            toggleTimeout = setTimeout(() => {
                toggleTimeout = null;
                if (dashboardWindow.isVisible()) {
                    dashboardWindow.hide();
                }
                else {
                    dashboardWindow.show();
                    dashboardWindow.focus();
                }
            }, 150);
        });
    }
    return true;
});
// Open floating window
electron_1.ipcMain.handle("open-window", (event, feature, title) => {
    createFloatingWindow(feature, title);
});
// Close window
electron_1.ipcMain.handle("close-window", (event, windowId) => {
    const window = windows.get(windowId);
    if (window && !window.isDestroyed()) {
        window.close();
    }
});
// Minimize window
electron_1.ipcMain.handle("minimize-window", (event) => {
    const window = electron_1.BrowserWindow.fromWebContents(event.sender);
    window?.minimize();
});
// Start a resize session.
// The main process owns all cursor reading via screen.getCursorScreenPoint() so
// there is no DPI coordinate mismatch between the renderer and main process.
electron_1.ipcMain.on("start-resize", (event, dir) => {
    stopActiveResize();
    const win = electron_1.BrowserWindow.fromWebContents(event.sender);
    if (!win)
        return;
    const startCursor = electron_1.screen.getCursorScreenPoint();
    const startBounds = win.getBounds();
    const [minW, minH] = win.getMinimumSize();
    const intervalId = setInterval(() => {
        if (!activeResize)
            return;
        if (activeResize.win.isDestroyed()) {
            stopActiveResize();
            return;
        }
        const cursor = electron_1.screen.getCursorScreenPoint();
        const dx = cursor.x - startCursor.x;
        const dy = cursor.y - startCursor.y;
        let { x, y, width, height } = startBounds;
        if (dir.includes("e"))
            width = Math.max(minW, width + dx);
        if (dir.includes("s"))
            height = Math.max(minH, height + dy);
        if (dir.includes("w")) {
            x = x + dx;
            width = Math.max(minW, width - dx);
        }
        if (dir.includes("n")) {
            y = y + dy;
            height = Math.max(minH, height - dy);
        }
        win.setBounds({
            x: Math.round(x),
            y: Math.round(y),
            width: Math.round(width),
            height: Math.round(height),
        });
    }, 16);
    // Safety net: stop the session after 10 s in case stop-resize IPC is never
    // received (e.g. renderer crash). We intentionally do NOT use win.blur here
    // because transparent frameless windows fire blur the instant the cursor
    // crosses a transparent pixel while dragging outward — that would kill the
    // resize session before the user has moved the mouse at all.
    const safetyTimeout = setTimeout(() => stopActiveResize(), 10000);
    activeResize = {
        win,
        dir,
        startCursor,
        startBounds,
        minW,
        minH,
        intervalId,
        safetyTimeout,
    };
});
// Stop the active resize session (sent on pointerup from renderer).
electron_1.ipcMain.on("stop-resize", () => stopActiveResize());
// Maximize/restore window — uses manual setBounds because transparent
// frameless windows can silently ignore window.maximize() on Windows.
electron_1.ipcMain.handle("maximize-window", (event) => {
    const window = electron_1.BrowserWindow.fromWebContents(event.sender);
    if (!window)
        return;
    const id = window.id;
    if (windowPreExpandBounds.has(id)) {
        // Restore to pre-expand bounds
        window.setBounds(windowPreExpandBounds.get(id));
        windowPreExpandBounds.delete(id);
    }
    else {
        // Save current bounds then expand to full work area
        windowPreExpandBounds.set(id, window.getBounds());
        const { workArea } = electron_1.screen.getPrimaryDisplay();
        window.setBounds({
            x: workArea.x,
            y: workArea.y,
            width: workArea.width,
            height: workArea.height,
        });
    }
});
// Toggle always-on-top state for floating window
electron_1.ipcMain.handle("set-window-pinned", (event, pinned) => {
    const window = electron_1.BrowserWindow.fromWebContents(event.sender);
    if (!window)
        return;
    window.setAlwaysOnTop(pinned, pinned ? "screen-saver" : "normal");
    window.setVisibleOnAllWorkspaces(pinned, { visibleOnFullScreen: pinned });
});
// Get server status
electron_1.ipcMain.handle("get-server-status", async () => {
    return await checkServerHealth();
});
// Get API base URL
electron_1.ipcMain.handle("get-api-base-url", async () => {
    return SERVER_URL;
});
// Get WebSocket base URL
electron_1.ipcMain.handle("get-ws-base-url", async () => {
    return WS_BASE_URL;
});
// Get current hotkey
electron_1.ipcMain.handle("get-hotkey", async () => {
    return currentHotkey;
});
// Set and register new hotkey
electron_1.ipcMain.handle("set-hotkey", async (_event, key) => {
    // Unregister old hotkey if it exists
    if (currentHotkey) {
        electron_1.globalShortcut.unregister(currentHotkey);
    }
    // Store the new hotkey
    currentHotkey = key;
    // Register new hotkey to toggle dashboard visibility
    const dashboardWindow = windows.get("dashboard");
    if (dashboardWindow) {
        electron_1.globalShortcut.register(currentHotkey, () => {
            if (toggleTimeout)
                clearTimeout(toggleTimeout);
            toggleTimeout = setTimeout(() => {
                toggleTimeout = null;
                if (dashboardWindow.isVisible()) {
                    dashboardWindow.hide();
                }
                else {
                    dashboardWindow.show();
                    dashboardWindow.focus();
                }
            }, 150);
        });
    }
    return true;
});
// Quit application
electron_1.ipcMain.handle("quit-app", () => {
    electron_1.app.quit();
});
