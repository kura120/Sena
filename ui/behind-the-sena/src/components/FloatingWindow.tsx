import React, { ReactNode } from 'react'
import { motion } from 'framer-motion'
import { X, Minimize, Maximize2 } from 'lucide-react'

interface FloatingWindowProps {
  title: string
  windowId: string
  children: ReactNode
  onClose?: () => void
}

export function FloatingWindow({ title, windowId, children, onClose }: FloatingWindowProps) {
  const handleClose = async () => {
    if (onClose) {
      onClose()
    } else {
      await window.sena.closeWindow(windowId)
    }
  }

  const handleMinimize = async () => {
    await window.sena.minimizeWindow()
  }

  const handleMaximize = async () => {
    await window.sena.maximizeWindow()
  }

  return (
    <div className="w-full h-full flex flex-col rounded-2xl border border-slate-800/70 bg-slate-950 shadow-[0_20px_60px_rgba(2,6,23,0.7)] overflow-hidden -mt-8 pt-8">
      {/* Custom title bar */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center justify-between px-4 py-3 bg-slate-900 border-b border-slate-800 select-none drag"
      >
        <h1 className="text-sm font-semibold text-slate-50">{title}</h1>
        
        {/* Window controls */}
        <div className="flex items-center gap-2 no-drag">
          <button
            onClick={handleMinimize}
            className="w-8 h-8 rounded-lg flex items-center justify-center hover:bg-slate-800 transition-colors"
          >
            <Minimize className="w-4 h-4 text-slate-400" />
          </button>
          <button
            onClick={handleMaximize}
            className="w-8 h-8 rounded-lg flex items-center justify-center hover:bg-slate-800 transition-colors"
          >
            <Maximize2 className="w-4 h-4 text-slate-400" />
          </button>
          <button
            onClick={handleClose}
            className="w-8 h-8 rounded-lg flex items-center justify-center hover:bg-red-500/20 text-slate-400 hover:text-red-400 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </motion.div>

      {/* Window content */}
      <div className="flex-1 overflow-hidden">
        {children}
      </div>
    </div>
  )
}
