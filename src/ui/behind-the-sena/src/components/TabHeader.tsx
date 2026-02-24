import React, { type ReactNode } from "react"
import { type LucideIcon } from "lucide-react"

interface TabHeaderProps {
  title: string
  subtitle?: string
  icon?: LucideIcon
  action?: ReactNode
  /** Extra classes applied to the header container */
  className?: string
}

/**
 * Consistent header block rendered at the top of every tab.
 * Contains an optional icon, title, subtitle, and an action slot
 * (e.g. a refresh button).
 */
export const TabHeader: React.FC<TabHeaderProps> = ({
  title,
  subtitle,
  icon: Icon,
  action,
  className = "",
}) => {
  return (
    <div
      className={`px-6 pt-6 pb-4 flex items-start justify-between gap-4 ${className}`}
    >
      <div className="flex items-center gap-3 min-w-0">
        {Icon && (
          <div className="p-2 bg-purple-500/15 rounded-lg flex-shrink-0">
            <Icon className="w-4 h-4 text-purple-400" />
          </div>
        )}
        <div className="min-w-0">
          <h2 className="text-base font-semibold text-slate-50 leading-tight truncate">
            {title}
          </h2>
          {subtitle && (
            <p className="text-xs text-slate-400 mt-0.5 leading-snug">
              {subtitle}
            </p>
          )}
        </div>
      </div>

      {action && (
        <div className="flex items-center gap-2 flex-shrink-0">{action}</div>
      )}
    </div>
  )
}
