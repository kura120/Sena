import React, { type ReactNode } from "react"
import { type LucideIcon, Loader } from "lucide-react"

interface PrimaryButtonProps {
  onClick?: () => void
  disabled?: boolean
  loading?: boolean
  children: ReactNode
  icon?: LucideIcon
  /** Extra classes appended to the button */
  className?: string
  type?: "button" | "submit" | "reset"
}

/**
 * Primary purple action button used across all tabs and forms.
 * Handles loading state with a spinner automatically.
 */
export const PrimaryButton: React.FC<PrimaryButtonProps> = ({
  onClick,
  disabled = false,
  loading = false,
  children,
  icon: Icon,
  className = "",
  type = "button",
}) => {
  const isDisabled = disabled || loading

  return (
    <button
      type={type}
      onClick={onClick}
      disabled={isDisabled}
      className={`
        inline-flex items-center gap-1.5 px-3 py-1.5 rounded
        bg-purple-500/20 text-purple-300 border border-purple-500/40
        text-xs font-medium
        hover:bg-purple-500/30 active:bg-purple-500/40
        transition-colors duration-150
        disabled:opacity-50 disabled:cursor-not-allowed
        ${className}
      `}
    >
      {loading ? (
        <Loader className="w-3.5 h-3.5 animate-spin" />
      ) : (
        Icon && <Icon className="w-3.5 h-3.5" />
      )}
      {children}
    </button>
  )
}
