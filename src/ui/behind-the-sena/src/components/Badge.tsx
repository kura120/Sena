import React, { type ReactNode } from "react"

interface BadgeProps {
  children: ReactNode
  variant?: "purple" | "green" | "red" | "blue" | "yellow" | "slate"
  /** Extra classes applied to the badge */
  className?: string
}

const VARIANT_CLASSES: Record<NonNullable<BadgeProps["variant"]>, string> = {
  purple: "bg-purple-900/40 border-purple-700/60 text-purple-400",
  green:  "bg-green-900/30 border-green-700/50 text-green-400",
  red:    "bg-red-900/30 border-red-700/50 text-red-400",
  blue:   "bg-blue-900/30 border-blue-700/50 text-blue-400",
  yellow: "bg-yellow-900/20 border-yellow-700/40 text-yellow-400",
  slate:  "bg-slate-800/60 border-slate-700/60 text-slate-400",
}

/**
 * Small inline label / tag badge.
 * Used for categories, statuses, tags, and similar metadata labels.
 */
export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = "slate",
  className = "",
}) => {
  return (
    <span
      className={`
        inline-flex items-center px-2 py-0.5
        text-xs font-semibold
        border rounded
        ${VARIANT_CLASSES[variant]}
        ${className}
      `}
    >
      {children}
    </span>
  )
}
