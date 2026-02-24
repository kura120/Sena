import React, { useState } from 'react'
import { motion } from 'framer-motion'
import { LucideIcon } from 'lucide-react'

export interface HotbarButtonProps {
  icon: LucideIcon
  label: string
  color?: string
  strokeColor?: string
  onClick?: () => void
  isActive?: boolean
}

export function HotbarButton({
  icon: Icon,
  label,
  color = 'bg-purple-500',
  strokeColor = 'border-transparent',
  onClick,
  isActive = false
}: HotbarButtonProps) {
  const [isHovered, setIsHovered] = useState(false)
  const [mousePosition, setMousePosition] = useState({ x: 0, y: 0 })

  const handleMouseMove = (e: React.MouseEvent<HTMLButtonElement>) => {
    setMousePosition({
      x: e.clientX,
      y: e.clientY
    })
  }

  return (
    <div className="relative">
      <motion.button
        className={`
          relative w-9 h-9 rounded-xl
          ${color} ${strokeColor}
          border flex items-center justify-center
          shadow-md
          transition-all duration-200
          ${isActive ? 'ring-2 ring-white/80 ring-offset-2 ring-offset-slate-950' : ''}
        `}
        whileHover={{ scale: 1.1, y: -3, transition: { type: 'spring', stiffness: 400, damping: 10 } }}
        whileTap={{ scale: 0.95, transition: { type: 'spring', stiffness: 400, damping: 10 } }}
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
        onMouseMove={handleMouseMove}
        onClick={onClick}
      >
        {/* Glow effect */}
        <motion.div
          className={`absolute inset-0 rounded-xl ${color} blur-xl opacity-0`}
          animate={{ opacity: isHovered ? 0.45 : 0 }}
          transition={{ duration: 0.2 }}
        />
        
        {/* Icon */}
        <Icon className="w-4 h-4 text-white relative z-10" />
      </motion.button>

      {/* Tooltip */}
      {isHovered && (
        <motion.div
          initial={{ opacity: 0, y: 5 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 5 }}
          transition={{ duration: 0.15 }}
          className="fixed z-50 px-3 py-1.5 bg-slate-900/95 text-slate-50 text-sm font-medium rounded-xl shadow-xl border border-slate-700 whitespace-nowrap max-w-xs"
          style={{
            left: `${Math.min(mousePosition.x + 12, window.innerWidth - 200)}px`,
            top: `${Math.min(mousePosition.y + 12, window.innerHeight - 48)}px`,
            pointerEvents: 'none'
          }}
        >
          {label}
        </motion.div>
      )}
    </div>
  )
}
