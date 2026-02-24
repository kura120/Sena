import React from "react"
import { motion } from "framer-motion"
import { type LucideIcon } from "lucide-react"

interface StatCardProps {
  label: string
  value: string | number
  icon: LucideIcon
  /** Tailwind text-color class for the icon and value, e.g. "text-blue-400" */
  color?: string
  /** Tailwind bg class for the card background tint, e.g. "bg-blue-500/10" */
  bg?: string
  /** Framer Motion entrance delay in seconds */
  delay?: number
  /** Optional sub-label shown below the value */
  subLabel?: string
}

/**
 * Compact stat display card used in Memory, Telemetry, and similar tabs.
 * Animates in on mount with an optional stagger delay.
 */
export const StatCard: React.FC<StatCardProps> = ({
  label,
  value,
  icon: Icon,
  color = "text-purple-400",
  bg = "bg-purple-500/10",
  delay = 0,
  subLabel,
}) => {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay, duration: 0.25 }}
      className={`${bg} border border-slate-800/60 rounded-xl p-4 backdrop-blur-sm`}
    >
      <div className="flex items-start justify-between mb-2">
        <Icon className={`w-5 h-5 ${color}`} />
      </div>
      <div className={`text-2xl font-bold ${color} mb-0.5 tabular-nums leading-tight`}>
        {value}
      </div>
      <div className="text-xs text-slate-400 leading-snug">{label}</div>
      {subLabel && (
        <div className="text-[11px] text-slate-600 mt-1 leading-snug">
          {subLabel}
        </div>
      )}
    </motion.div>
  )
}
