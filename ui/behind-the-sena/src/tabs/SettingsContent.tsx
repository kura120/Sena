import React, { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Key, Settings as SettingsIcon } from 'lucide-react'

export const SettingsContent: React.FC = () => {
  const [hotkeyDisplay, setHotkeyDisplay] = useState<string>('Home')
  const [isListening, setIsListening] = useState<boolean>(false)
  const [isSaved, setIsSaved] = useState<boolean>(false)

  useEffect(() => {
    // Load saved hotkey
    loadHotkey()
  }, [])

  const loadHotkey = async () => {
    try {
      const hotkey = await window.sena.getHotkey()
      setHotkeyDisplay(hotkey || 'Home')
    } catch (error) {
      console.error('Failed to load hotkey:', error)
    }
  }

  const startListening = () => {
    setIsListening(true)
  }

  const handleKeyDown = async (e: KeyboardEvent) => {
    if (!isListening) return

    e.preventDefault()
    const keyName = e.key.length === 1 ? e.key.toUpperCase() : e.key

    try {
      await window.sena.setHotkey(keyName)
      setHotkeyDisplay(keyName)
      setIsListening(false)
      setIsSaved(true)
      setTimeout(() => setIsSaved(false), 2000)
    } catch (error) {
      console.error('Failed to set hotkey:', error)
    }
  }

  useEffect(() => {
    if (isListening) {
      window.addEventListener('keydown', handleKeyDown)
      return () => window.removeEventListener('keydown', handleKeyDown)
    }
  }, [isListening])

  return (
    <div className="w-full h-full flex flex-col bg-slate-950 p-4 overflow-y-auto">
      {/* Header */}
      <div className="flex items-center gap-2 mb-4">
        <SettingsIcon className="w-5 h-5 text-purple-500" />
        <h2 className="text-lg font-bold text-slate-50">Settings</h2>
      </div>

      {/* Hotkey Section - Single Line */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-slate-900/50 rounded-lg border border-slate-800/70 p-3 flex items-center gap-3 mb-3"
      >
        <div className="p-1.5 bg-purple-500/20 rounded">
          <Key className="w-4 h-4 text-purple-500" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-xs text-slate-400">Hotbar Toggle</p>
          <p className="text-xs text-slate-500">Click to change key</p>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          <motion.button
            whileHover={!isListening ? { scale: 1.02 } : {}}
            whileTap={!isListening ? { scale: 0.98 } : {}}
            onClick={startListening}
            disabled={isListening}
            className={`
              px-3 py-1 rounded border font-mono font-semibold text-sm transition-all
              ${isListening
                ? 'bg-purple-500/30 text-purple-300 border-purple-500/50'
                : 'bg-slate-800/70 text-slate-50 border-slate-700 hover:border-purple-500/50 hover:bg-slate-700'
              }
            `}
          >
            {isListening ? '...' : hotkeyDisplay}
          </motion.button>
          {isSaved && (
            <motion.span
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="text-xs text-green-400 font-semibold"
            >
              ✓
            </motion.span>
          )}
        </div>
      </motion.div>

      {/* Info */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-2"
      >
        <p className="text-xs text-blue-300">
          💡 Toggle hotbar on/off from anywhere using your chosen key
        </p>
      </motion.div>
    </div>
  )
}
