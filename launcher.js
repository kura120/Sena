#!/usr/bin/env node

/**
 * Sena Launcher
 * Starts the Python backend server and opens the UI in default browser
 */

const { spawn } = require('child_process')
const http = require('http')
const path = require('path')
const os = require('os')
const fs = require('fs')

const API_HOST = '127.0.0.1'
const API_PORT = 8000
const API_URL = `http://${API_HOST}:${API_PORT}`

let serverProcess = null
let isShuttingDown = false

/**
 * Check if the API server is healthy
 */
function isServerHealthy() {
  return new Promise((resolve) => {
    const req = http.get(API_URL + '/health', { timeout: 2000 }, (res) => {
      resolve(res.statusCode === 200)
    })
    req.on('error', () => resolve(false))
    req.setTimeout(2000, () => {
      req.abort()
      resolve(false)
    })
  })
}

/**
 * Start the Python API server
 */
function startServer() {
  return new Promise((resolve) => {
    console.log('🚀 Starting Sena API server...')

    // Determine Python executable
    const pythonCmd = process.platform === 'win32' ? 'python' : 'python3'
    const repoRoot = path.join(__dirname)

    serverProcess = spawn(pythonCmd, [
      '-m',
      'uvicorn',
      'src.api.server:app',
      '--host',
      API_HOST,
      '--port',
      `${API_PORT}`,
    ], {
      cwd: repoRoot,
      stdio: 'inherit',
      shell: true,
    })

    serverProcess.on('error', (err) => {
      console.error('❌ Failed to start server:', err.message)
      resolve(false)
    })

    serverProcess.on('exit', (code) => {
      if (!isShuttingDown) {
        console.log('⚠️  Server exited with code:', code)
      }
    })

    // Wait for server to be ready (up to 15 seconds)
    let attempts = 0
    const checkServer = setInterval(async () => {
      attempts++
      const healthy = await isServerHealthy()
      if (healthy) {
        clearInterval(checkServer)
        console.log('✅ Server is ready!')
        resolve(true)
      } else if (attempts > 30) {
        clearInterval(checkServer)
        console.error('❌ Server failed to start within timeout')
        resolve(false)
      }
    }, 500)
  })
}

/**
 * Open the UI in the default browser
 */
function openBrowser() {
  const url = API_URL
  console.log(`🌐 Opening browser to ${url}...`)

  const start =
    process.platform === 'darwin'
      ? 'open'
      : process.platform === 'win32'
        ? 'start'
        : 'xdg-open'

  spawn(start, [url], { 
    stdio: 'ignore',
    detached: true 
  }).unref()
}

/**
 * Graceful shutdown
 */
function shutdown() {
  if (isShuttingDown) return
  isShuttingDown = true

  console.log('\n👋 Shutting down Sena...')

  if (serverProcess) {
    try {
      process.kill(-serverProcess.pid)
    } catch (err) {
      // Process might already be dead
    }
  }

  process.exit(0)
}

/**
 * Main entry point
 */
async function main() {
  console.log('╔════════════════════════════════════════╗')
  console.log('║           SENA LAUNCHER                ║')
  console.log('║   Self-Evolving AI Assistant           ║')
  console.log('╚════════════════════════════════════════╝')
  console.log()

  // Handle process signals
  process.on('SIGINT', shutdown)
  process.on('SIGTERM', shutdown)

  // Check if server is already running
  console.log('📡 Checking if server is already running...')
  const alreadyRunning = await isServerHealthy()

  if (alreadyRunning) {
    console.log('✅ Server is already running!')
    openBrowser()
    return
  }

  // Start the server
  const serverStarted = await startServer()
  if (!serverStarted) {
    console.error('❌ Failed to start Sena server')
    process.exit(1)
  }

  // Open the browser
  openBrowser()

  console.log()
  console.log('✨ Sena is running! Press Ctrl+C to stop.')
}

main().catch((err) => {
  console.error('❌ Fatal error:', err)
  process.exit(1)
})
