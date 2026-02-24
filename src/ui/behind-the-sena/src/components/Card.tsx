import React, { type ReactNode } from "react"

interface CardProps {
  children: ReactNode
  /** Extra classes applied to the card */
  className?: string
  /** Whether to apply default padding. Defaults to true. */
  padding?: boolean
  /** Visual variant */
  variant?: "default" | "inset" | "flat"
  /** Click handler — makes the card interactive */
  onClick?: () => void
}

const VARIANT_CLASSES: Record<NonNullable<CardProps["variant"]>, string> = {
  default: "bg-slate-900/50 border border-slate-800/70 rounded-lg",
  inset: "bg-slate-950/60 border border-slate-800/50 rounded-lg",
  flat: "bg-slate-900/30 border border-slate-800/40 rounded-lg",
}

/**
 * Generic container card used across all tabs and settings panels.
 * Provides consistent background, border, and border-radius tokens.
 */
export const Card: React.FC<CardProps> = ({
  children,
  className = "",
  padding = true,
  variant = "default",
  onClick,
}) => {
  const interactiveClasses = onClick
    ? "cursor-pointer hover:bg-slate-900/70 transition-colors duration-150"
    : ""

  return (
    <div
      onClick={onClick}
      className={`
        ${VARIANT_CLASSES[variant]}
        ${padding ? "p-4" : ""}
        ${interactiveClasses}
        ${className}
      `}
    >
      {children}
    </div>
  )
}
