import React, { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { RefreshCw, Zap, AlertCircle } from 'lucide-react'

type Extension = {
  name: string
  enabled: boolean
  metadata?: { description?: string; [key: string]: any }
}

export const ExtensionsContent: React.FC = () => {
  const [exts, setExts] = useState<Extension[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    void fetchExts()
  }, [])

  async function fetchExts() {
    setLoading(true)
    setError(null)
    try {
      console.log('Fetching extensions from /api/v1/extensions...')
      const res = await fetch('http://127.0.0.1:8000/api/v1/extensions')
      
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}: ${res.statusText}`)
      }

      const data = await res.json()
      console.log('Extensions response:', data)

      // Handle different response formats
      const extensionsList = data.extensions || data.data || data.items || []
      
      if (Array.isArray(extensionsList) && extensionsList.length > 0) {
        setExts(extensionsList)
        setError(null)
      } else {
        setExts([])
        setError('No extensions loaded or invalid API response')
      }
    } catch (e) {
      const errorMsg = e instanceof Error ? e.message : String(e)
      console.error('Failed to fetch extensions:', errorMsg)
      setError(errorMsg)
      setExts([])
    } finally {
      setLoading(false)
    }
  }

  async function reload(name: string) {
    try {
      await fetch(`http://127.0.0.1:8000/api/v1/extensions/${encodeURIComponent(name)}/reload`, {
        method: 'POST',
      })
      void fetchExts()
    } catch (e) {
      console.error('Failed to reload extension:', e)
    }
  }

  async function toggle(name: string, enabled: boolean) {
    try {
      await fetch(`http://127.0.0.1:8000/api/v1/extensions/${encodeURIComponent(name)}/toggle`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled }),
      })
      void fetchExts()
    } catch (e) {
      console.error('Failed to toggle extension:', e)
    }
  }

  return (
    <div className="h-full flex flex-col bg-[#0A0E27]">
      <div className="px-6 pt-6 pb-4 flex items-center justify-between">
        <div>
          <p className="text-xs text-slate-400">{exts.length} extensions available</p>
        </div>
        <button
          onClick={fetchExts}
          disabled={loading}
          className="p-2 bg-[#0F1629]/60 border border-slate-800/40 text-slate-300 rounded-lg hover:bg-[#0F1629] transition disabled:opacity-50 backdrop-blur-sm"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {error && (
        <div className="mx-6 mb-4 border border-red-700/40 bg-red-900/20 rounded-lg p-3 flex gap-2.5 backdrop-blur-sm">
          <AlertCircle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
          <div>
            <h3 className="font-medium text-red-300 text-sm">Error loading extensions</h3>
            <p className="text-xs text-red-400 mt-1">{error}</p>
          </div>
        </div>
      )}

      {loading && exts.length === 0 && (
        <div className="text-center py-8 text-slate-500 text-sm">Loading extensions...</div>
      )}

      <div className="flex-1 overflow-y-auto px-6 pb-6">
        <div className="grid gap-3">
          {exts.length === 0 && !loading && !error && (
            <div className="text-center py-8 text-slate-500 text-sm">No extensions found</div>
          )}

          {exts.map((ext, idx) => (
            <div
              key={ext.name}
              className="border border-slate-700/40 rounded-lg p-3.5 bg-[#0F1629]/40 hover:bg-[#0F1629]/60 transition backdrop-blur-sm"
            >
              <div className="flex items-start justify-between">
              <div className="flex items-start gap-3 flex-1">
                <div className="w-9 h-9 bg-purple-900/30 border border-purple-700/40 rounded-lg flex items-center justify-center mt-0.5">
                  <Zap className="w-4 h-4 text-purple-400" />
                </div>
                <div className="flex-1">
                  <h3 className="font-medium text-white text-sm">{ext.name}</h3>
                  <p className="text-xs text-slate-400 mt-1">
                    {ext.metadata?.description || 'No description available'}
                  </p>
                  {ext.enabled && (
                    <div className="flex items-center gap-1 mt-2">
                      <div className="w-1.5 h-1.5 rounded-full bg-green-500"></div>
                      <span className="text-[10px] text-green-400 font-medium">Active</span>
                    </div>
                  )}
                </div>
              </div>
              <div className="flex gap-1.5">
                <button
                  onClick={() => reload(ext.name)}
                  className="p-1.5 hover:bg-slate-700/30 rounded-md transition"
                  title="Reload extension"
                >
                  <RefreshCw className="w-3.5 h-3.5 text-slate-500 hover:text-slate-300" />
                </button>
                <button
                  onClick={() => toggle(ext.name, !ext.enabled)}
                  className={`px-2.5 py-1 rounded-md font-medium text-xs transition ${
                    ext.enabled
                      ? 'bg-red-900/30 border border-red-700/40 text-red-400 hover:bg-red-900/50'
                      : 'bg-green-900/30 border border-green-700/40 text-green-400 hover:bg-green-900/50'
                  }`}
                >
                  {ext.enabled ? 'Disable' : 'Enable'}
                </button>
              </div>
            </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
