"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const electron_1 = require("electron");
const child_process_1 = require("child_process");
const fs_1 = __importDefault(require("fs"));
const path_1 = __importDefault(require("path"));
// Window management
const windows = new Map();
const floatingOrder = [];
const floatingMoved = new Set();
let serverProcess = null;
let isDev = false;
let currentHotkey = 'Home';
// Server configuration
const SERVER_PORT = 8000;
const SERVER_HOST = '127.0.0.1';
const SERVER_URL = `http://${SERVER_HOST}:${SERVER_PORT}`;
/**
 * Check if server is healthy
 */
async function checkServerHealth() {
    try {
        const request = electron_1.net.request(`${SERVER_URL}/health`);
        return new Promise((resolve) => {
            request.on('response', (response) => {
                resolve(response.statusCode === 200);
            });
            request.on('error', () => {
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
            '-m', 'uvicorn',
            'src.api.server:app',
            '--host', SERVER_HOST,
            '--port', SERVER_PORT.toString()
        ], {
            cwd: projectRoot,
            stdio: ['ignore', 'pipe', 'pipe']
        });
        // Send stdout to loader window
        serverProcess.stdout?.on('data', (data) => {
            const message = data.toString();
            sendToWindow('loader', 'server-log', message);
        });
        // Send stderr to loader window
        serverProcess.stderr?.on('data', (data) => {
            const message = data.toString();
            sendToWindow('loader', 'server-log', message);
        });
        serverProcess.on('error', (error) => {
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
        // Timeout after 30 seconds
        setTimeout(() => {
            clearInterval(checkInterval);
            reject(new Error('Server startup timeout'));
        }, 30000);
    });
}
function getPythonPath(projectRoot) {
    const venvBinDir = process.platform === 'win32' ? 'Scripts' : 'bin';
    const pythonBinary = process.platform === 'win32' ? 'python.exe' : 'python';
    return path_1.default.join(projectRoot, '.venv', venvBinDir, pythonBinary);
}
function resolveProjectRoot() {
    const candidates = [
        path_1.default.resolve(__dirname, '../../../../'),
        path_1.default.resolve(__dirname, '../../../..'),
        path_1.default.resolve(process.cwd(), '../../..'),
        path_1.default.resolve(process.cwd(), '..')
    ];
    for (const candidate of candidates) {
        if (fs_1.default.existsSync(getPythonPath(candidate))) {
            return candidate;
        }
    }
    return path_1.default.resolve(__dirname, '../../../../');
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
        transparent: true,
        backgroundColor: '#00000000',
        resizable: false,
        alwaysOnTop: true,
        focusable: true,
        acceptFirstMouse: true,
        center: true,
        webPreferences: {
            nodeIntegration: false,
            contextIsolation: true,
            backgroundThrottling: false,
            preload: path_1.default.join(__dirname, 'preload.js')
        }
    });
    if (isDev) {
        loaderWindow.loadURL('http://localhost:5173/#/loader');
    }
    else {
        loaderWindow.loadFile(path_1.default.join(__dirname, '../dist/index.html'), {
            hash: '/loader'
        });
    }
    windows.set('loader', loaderWindow);
    loaderWindow.setAlwaysOnTop(true, 'screen-saver');
    loaderWindow.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true });
    loaderWindow.on('closed', () => {
        windows.delete('loader');
    });
    return loaderWindow;
}
/**
 * Create dashboard hotbar window
 */
function createDashboardWindow() {
    const { width, height } = electron_1.screen.getPrimaryDisplay().workAreaSize;
    const dashboardWindow = new electron_1.BrowserWindow({
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
        ...(process.platform === 'win32' ? {
            titleBarStyle: 'hidden',
            titleBarOverlay: false
        } : {}),
        webPreferences: {
            nodeIntegration: false,
            contextIsolation: true,
            preload: path_1.default.join(__dirname, 'preload.js')
        }
    });
    dashboardWindow.setMenuBarVisibility(false);
    dashboardWindow.setAutoHideMenuBar(true);
    dashboardWindow.setAlwaysOnTop(true, 'screen-saver');
    dashboardWindow.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true });
    if (isDev) {
        dashboardWindow.loadURL('http://localhost:5173/#/dashboard');
    }
    else {
        dashboardWindow.loadFile(path_1.default.join(__dirname, '../dist/index.html'), {
            hash: '/dashboard'
        });
    }
    windows.set('dashboard', dashboardWindow);
    dashboardWindow.on('closed', () => {
        windows.delete('dashboard');
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
        frame: false,
        transparent: true,
        backgroundColor: '#00000000',
        alwaysOnTop: true,
        focusable: true,
        acceptFirstMouse: true,
        show: false,
        ...(process.platform === 'win32' ? {
            titleBarStyle: 'hidden',
            titleBarOverlay: false
        } : {}),
        webPreferences: {
            nodeIntegration: false,
            contextIsolation: true,
            preload: path_1.default.join(__dirname, 'preload.js')
        }
    });
    floatingWindow.setAlwaysOnTop(true, 'screen-saver');
    floatingWindow.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true });
    if (isDev) {
        floatingWindow.loadURL(`http://localhost:5173/#/${feature}`);
    }
    else {
        floatingWindow.loadFile(path_1.default.join(__dirname, '../dist/index.html'), {
            hash: `/${feature}`
        });
    }
    // Show window after content loads
    floatingWindow.once('ready-to-show', () => {
        floatingWindow.show();
        floatingWindow.focus();
    });
    windows.set(feature, floatingWindow);
    floatingOrder.push(feature);
    layoutFloatingWindows();
    floatingWindow.on('closed', () => {
        windows.delete(feature);
        floatingMoved.delete(feature);
        const index = floatingOrder.indexOf(feature);
        if (index >= 0) {
            floatingOrder.splice(index, 1);
            layoutFloatingWindows();
        }
        // Notify dashboard that this window closed
        sendToWindow('dashboard', 'window-closed', feature);
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
    win.on('will-move', () => {
        isMoving = true;
    });
    win.on('moved', () => {
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
    // Create loader window
    const loaderWindow = createLoaderWindow();
    const loaderStart = Date.now();
    try {
        // Check if server is already running
        const isRunning = await checkServerHealth();
        if (!isRunning) {
            sendToWindow('loader', 'startup-step', { step: 'Starting Python server...' });
            await startServer();
        }
        else {
            sendToWindow('loader', 'startup-step', { step: 'Server already running' });
        }
        // Wait a moment for UI effect
        await new Promise(resolve => setTimeout(resolve, 1000));
        sendToWindow('loader', 'startup-step', { step: 'Server ready!' });
        await new Promise(resolve => setTimeout(resolve, 500));
        // Keep loader visible for at least 5 seconds
        const elapsed = Date.now() - loaderStart;
        if (elapsed < 5000) {
            await new Promise(resolve => setTimeout(resolve, 5000 - elapsed));
        }
        // Close loader and open dashboard
        loaderWindow.close();
        const dashboardWindow = createDashboardWindow();
        // Register the initial hotkey (Home key by default)
        electron_1.globalShortcut.register(currentHotkey, () => {
            if (dashboardWindow.isVisible()) {
                dashboardWindow.hide();
            }
            else {
                dashboardWindow.show();
                dashboardWindow.focus();
            }
        });
    }
    catch (error) {
        sendToWindow('loader', 'startup-error', {
            error: error instanceof Error ? error.message : 'Unknown error'
        });
    }
});
electron_1.app.on('window-all-closed', () => {
    stopServer();
    electron_1.app.quit();
});
electron_1.app.on('before-quit', () => {
    stopServer();
});
/**
 * IPC Handlers
 */
// Open floating window
electron_1.ipcMain.handle('open-window', (event, feature, title) => {
    createFloatingWindow(feature, title);
});
// Close window
electron_1.ipcMain.handle('close-window', (event, windowId) => {
    const window = windows.get(windowId);
    if (window && !window.isDestroyed()) {
        window.close();
    }
});
// Minimize window
electron_1.ipcMain.handle('minimize-window', (event) => {
    const window = electron_1.BrowserWindow.fromWebContents(event.sender);
    window?.minimize();
});
// Maximize/restore window
electron_1.ipcMain.handle('maximize-window', (event) => {
    const window = electron_1.BrowserWindow.fromWebContents(event.sender);
    if (window?.isMaximized()) {
        window.restore();
    }
    else {
        window?.maximize();
    }
});
// Toggle always-on-top state for floating window
electron_1.ipcMain.handle('set-window-pinned', (event, pinned) => {
    const window = electron_1.BrowserWindow.fromWebContents(event.sender);
    if (!window)
        return;
    window.setAlwaysOnTop(pinned, pinned ? 'screen-saver' : 'normal');
    window.setVisibleOnAllWorkspaces(pinned, { visibleOnFullScreen: pinned });
});
// Get server status
electron_1.ipcMain.handle('get-server-status', async () => {
    return await checkServerHealth();
});
// Get current hotkey
electron_1.ipcMain.handle('get-hotkey', async () => {
    return currentHotkey;
});
// Set and register new hotkey
electron_1.ipcMain.handle('set-hotkey', async (_event, key) => {
    // Unregister old hotkey if it exists
    if (currentHotkey) {
        electron_1.globalShortcut.unregister(currentHotkey);
    }
    // Store the new hotkey
    currentHotkey = key;
    // Register new hotkey to toggle dashboard visibility
    const dashboardWindow = windows.get('dashboard');
    if (dashboardWindow) {
        electron_1.globalShortcut.register(currentHotkey, () => {
            if (dashboardWindow.isVisible()) {
                dashboardWindow.hide();
            }
            else {
                dashboardWindow.show();
                dashboardWindow.focus();
            }
        });
    }
    return true;
});
// Quit application
electron_1.ipcMain.handle('quit-app', () => {
    electron_1.app.quit();
});
