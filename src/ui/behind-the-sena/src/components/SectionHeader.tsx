import React from "react"
import { type LucideIcon } from "lucide-react"

interface SectionHeaderProps {
  icon: LucideIcon
  label: string
  /** Extra classes applied to the wrapper */
  className?: string
}

/**
 * Section heading used inside tabs and settings panels.
 * Renders a small icon + uppercase label in muted text.
 */
export const SectionHeader: React.FC<SectionHeaderProps> = ({
  icon: Icon,
  label,
  className = "",
}) => {
  return (
    <div className={`flex items-center gap-2 pb-1 ${className}`}>
      <Icon className="w-4 h-4 text-purple-500" />
      <h3 className="text-sm uppercase tracking-[0.2em] text-slate-400">
        {label}
      </h3>
    </div>
  )
}
