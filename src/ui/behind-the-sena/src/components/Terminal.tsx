import React from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { AlertCircle, Info, CheckCircle, XCircle } from 'lucide-react'

export interface LogMessage {
  id: string
  timestamp: string
  level: 'debug' | 'info' | 'warning' | 'error'
  source: string
  message: string
}

interface TerminalProps {
  messages: LogMessage[]
  maxHeight?: string
}

const levelConfig = {
  debug: { icon: Info, color: 'text-slate-400', bg: 'bg-slate-400/10', border: 'border-slate-400/30' },
  info: { icon: CheckCircle, color: 'text-blue-400', bg: 'bg-blue-400/10', border: 'border-blue-400/30' },
  warning: { icon: AlertCircle, color: 'text-orange-400', bg: 'bg-orange-400/10', border: 'border-orange-400/30' },
  error: { icon: XCircle, color: 'text-red-400', bg: 'bg-red-400/10', border: 'border-red-400/30' }
}

export function Terminal({ messages, maxHeight = '600px' }: TerminalProps) {
  return (
    <div 
      className="bg-slate-900 rounded-lg border border-slate-800 overflow-hidden flex flex-col h-full"
    >
      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        <AnimatePresence initial={false}>
          {messages.map((msg, index) => {
            const config = levelConfig[msg.level]
            const Icon = config.icon

            return (
              <motion.div
                key={msg.id}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, height: 0 }}
                transition={{ duration: 0.2, delay: index * 0.02 }}
                className={`flex items-start gap-3 p-3 rounded-lg ${config.bg} border ${config.border}`}
              >
                <Icon className={`w-5 h-5 ${config.color} flex-shrink-0 mt-0.5`} />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs font-mono text-slate-400">
                      {msg.timestamp}
                    </span>
                    <span className={`text-xs font-medium ${config.color}`}>
                      {msg.level.toUpperCase()}
                    </span>
                    <span className="text-xs text-slate-500">
                      {msg.source}
                    </span>
                  </div>
                  <p className="text-sm text-slate-200 font-mono break-words">
                    {msg.message}
                  </p>
                </div>
              </motion.div>
            )
          })}
        </AnimatePresence>

        {messages.length === 0 && (
          <div className="flex items-center justify-center h-32 text-slate-500">
            No messages to display
          </div>
        )}
      </div>
    </div>
  )
}
