import React, { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { 
  MessageSquare, 
  Brain, 
  Puzzle, 
  Activity, 
  FileText,
  Settings,
  Power
} from 'lucide-react'
import { HotbarButton } from '../components/HotbarButton'

interface DashboardWindowProps {}

export function DashboardWindow({}: DashboardWindowProps) {
  const [activeWindows, setActiveWindows] = useState<string[]>([])
  const [time, setTime] = useState(() =>
    new Date().toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: false
    })
  )

  useEffect(() => {
    const interval = setInterval(() => {
      setTime(
        new Date().toLocaleTimeString('en-US', {
          hour: '2-digit',
          minute: '2-digit',
          hour12: false
        })
      )
    }, 1000)

    // Listen for window close events
    const handleWindowClosed = (windowId: string) => {
      setActiveWindows(prev => prev.filter(id => id !== windowId))
    }
    window.sena.onWindowClosed(handleWindowClosed)

    return () => {
      clearInterval(interval)
      window.sena.removeListener('window-closed')
    }
  }, [])

  const buttons = [
    { 
      id: 'chat', 
      icon: MessageSquare, 
      label: 'Chat Interface',
      color: 'bg-blue-500',
      strokeColor: 'border-blue-700'
    },
    { 
      id: 'memory', 
      icon: Brain, 
      label: 'Memory System',
      color: 'bg-purple-500',
      strokeColor: 'border-purple-700'
    },
    { 
      id: 'extensions', 
      icon: Puzzle, 
      label: 'Extensions',
      color: 'bg-green-500',
      strokeColor: 'border-green-700'
    },
    { 
      id: 'telemetry', 
      icon: Activity, 
      label: 'Telemetry & Metrics',
      color: 'bg-orange-500',
      strokeColor: 'border-orange-700'
    },
    { 
      id: 'logs', 
      icon: FileText, 
      label: 'System Logs',
      color: 'bg-red-500',
      strokeColor: 'border-red-700'
    },
    
  ]

  const handleButtonClick = async (id: string, label: string) => {
    if (activeWindows.includes(id)) {
      await window.sena.closeWindow(id)
      setActiveWindows(prev => prev.filter(w => w !== id))
    } else {
      await window.sena.openWindow(id, label)
      setActiveWindows(prev => [...prev, id])
    }
  }

  const handleSettings = async () => {
    if (activeWindows.includes('settings')) {
      await window.sena.closeWindow('settings')
      setActiveWindows(prev => prev.filter(w => w !== 'settings'))
    } else {
      await window.sena.openWindow('settings', 'Settings')
      setActiveWindows(prev => [...prev, 'settings'])
    }
  }

  const handleQuit = async () => {
    await window.sena.quitApp()
  }

  return (
    <div className="w-full h-full flex items-end justify-center pb-4">
      {/* Main hotbar container */}
      <motion.div
        initial={{ y: 100, opacity: 0, scale: 0.75 }}
        animate={{ y: 0, opacity: 1, scale: 1 }}
        transition={{ duration: 0.6, ease: 'easeOut' }}
        className="bg-slate-900/90 backdrop-blur-2xl rounded-lg border border-slate-800/70 shadow-2xl px-3 py-2 overflow-visible"
      >
        <div className="flex items-center justify-between gap-4 w-[420px]">
          {/* Clock/Time */}
          <div className="px-2.5 py-1 bg-slate-800/70 rounded-lg border border-slate-700/60">
            <span className="text-slate-50 text-sm font-medium tabular-nums">
              {time}
            </span>
          </div>

          {/* Feature buttons */}
          <div className="flex items-center gap-1.5">
            {buttons.map((button, index) => (
              <motion.div
                key={button.id}
                initial={{ scale: 0, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                transition={{
                  delay: 0.08 * index,
                  duration: 0.25,
                  ease: 'easeOut'
                }}
              >
                <HotbarButton
                  icon={button.icon}
                  label={button.label}
                  color={button.color}
                  strokeColor={button.strokeColor}
                  isActive={activeWindows.includes(button.id)}
                  onClick={() => handleButtonClick(button.id, button.label)}
                />
              </motion.div>
            ))}
          </div>

          {/* Settings */}
          <div className="pl-2.5 border-l border-slate-800/60 flex items-center gap-2">
            <HotbarButton
              icon={Settings}
              label="Settings"
              color="bg-slate-700"
              strokeColor="border-slate-800"
              isActive={activeWindows.includes('settings')}
              onClick={handleSettings}
            />
            <HotbarButton
              icon={Power}
              label="Turn Off"
              color="bg-red-600"
              strokeColor="border-red-800"
              onClick={handleQuit}
            />
          </div>
        </div>
      </motion.div>
    </div>
  )
}
