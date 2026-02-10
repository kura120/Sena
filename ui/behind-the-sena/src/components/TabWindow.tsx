import React, { ReactNode, useState } from 'react'
import { motion } from 'framer-motion'
import { X, Minimize, Pin, PinOff, LucideIcon } from 'lucide-react'

interface TabWindowProps {
  title: string
  icon: LucideIcon
  windowId: string
  children: ReactNode
  onClose?: () => void
}

/**
 * Modular tab window component matching reference UI style:
 * - Thin border strokes
 * - Corner curves (rounded-lg)
 * - Icon + title in header
 */
export function TabWindow({ title, icon: Icon, windowId, children, onClose }: TabWindowProps) {
  const [isPinned, setIsPinned] = useState(true)

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

  const handleTogglePin = async () => {
    const next = !isPinned
    setIsPinned(next)
    await window.sena.setWindowPinned(next)
  }

  return (
    <div className="w-full h-full flex flex-col rounded-2xl border border-slate-800/70 bg-[#0A0E27] shadow-[0_20px_60px_rgba(2,6,23,0.7)] overflow-hidden">
      {/* Header with icon + title */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center justify-between px-4 py-3 bg-[#0F1629]/80 backdrop-blur-sm border-b border-slate-800/40 select-none drag"
      >
        <div className="flex items-center gap-2.5">
          <Icon className="w-4 h-4 text-purple-400" />
          <h1 className="text-sm font-medium text-slate-200">{title}</h1>
        </div>
        
        {/* Window controls */}
        <div className="flex items-center gap-1 no-drag">
          <button
            onClick={handleMinimize}
            className="w-7 h-7 rounded-md flex items-center justify-center hover:bg-slate-700/30 transition-colors"
            title="Minimize"
          >
            <Minimize className="w-3.5 h-3.5 text-slate-400 hover:text-slate-300" />
          </button>
          <button
            onClick={handleTogglePin}
            className={`w-7 h-7 rounded-md flex items-center justify-center transition-colors ${
              isPinned ? 'hover:bg-emerald-500/10' : 'hover:bg-slate-700/30'
            }`}
            title={isPinned ? 'Disable topmost' : 'Keep window on top'}
          >
            {isPinned ? (
              <Pin className="w-3.5 h-3.5 text-emerald-400" />
            ) : (
              <PinOff className="w-3.5 h-3.5 text-slate-400" />
            )}
          </button>
          <button
            onClick={handleClose}
            className="w-7 h-7 rounded-md flex items-center justify-center hover:bg-red-500/20 text-slate-400 hover:text-red-400 transition-colors"
            title="Close"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      </motion.div>

      {/* Content area */}
      <div className="flex-1 overflow-hidden">
        {children}
      </div>
    </div>
  )
}

/**
 * Factory function to create tab components
 * Usage: const tab = Components.createTab(title, icon, content)
 */
export const Components = {
  createTab: (title: string, icon: LucideIcon, windowId: string, content: ReactNode) => {
    return (
      <TabWindow title={title} icon={icon} windowId={windowId}>
        {content}
      </TabWindow>
    )
  }
}
