import React from "react"
import { type LucideIcon } from "lucide-react"

interface EmptyStateProps {
  icon?: LucideIcon
  message: string
  description?: string
  action?: React.ReactNode
  /** Extra classes applied to the root container */
  className?: string
}

/**
 * Empty state placeholder shown when a list or data set has no items.
 * Renders a centred icon, message, optional description, and optional action.
 */
export const EmptyState: React.FC<EmptyStateProps> = ({
  icon: Icon,
  message,
  description,
  action,
  className = "",
}) => {
  return (
    <div
      className={`flex flex-col items-center justify-center gap-3 py-16 px-6 text-center ${className}`}
    >
      {Icon && (
        <div className="p-3 bg-slate-800/60 rounded-full">
          <Icon className="w-6 h-6 text-slate-500" />
        </div>
      )}

      <div className="space-y-1">
        <p className="text-sm font-medium text-slate-400">{message}</p>
        {description && (
          <p className="text-xs text-slate-600 max-w-xs leading-relaxed">
            {description}
          </p>
        )}
      </div>

      {action && <div className="mt-1">{action}</div>}
    </div>
  )
}
