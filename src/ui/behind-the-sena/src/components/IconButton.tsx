import React from "react"
import { type LucideIcon, Loader } from "lucide-react"

interface IconButtonProps {
  icon: LucideIcon
  onClick?: () => void
  disabled?: boolean
  loading?: boolean
  label?: string
  /** Visual style variant */
  variant?: "default" | "danger" | "success" | "ghost"
  /** Extra classes appended to the button */
  className?: string
  type?: "button" | "submit" | "reset"
}

const VARIANT_CLASSES: Record<NonNullable<IconButtonProps["variant"]>, string> =
  {
    default:
      "text-slate-400 hover:text-slate-200 hover:bg-slate-700/40 border-transparent",
    danger:
      "text-slate-400 hover:text-red-400 hover:bg-red-500/10 border-transparent",
    success:
      "text-slate-400 hover:text-green-400 hover:bg-green-500/10 border-transparent",
    ghost:
      "text-slate-500 hover:text-slate-300 hover:bg-slate-800/60 border-transparent",
  }

/**
 * Small icon-only button used for actions like refresh, copy, delete, etc.
 * Shows a spinner in place of the icon when loading.
 * Renders an accessible tooltip via the `title` attribute.
 */
export const IconButton: React.FC<IconButtonProps> = ({
  icon: Icon,
  onClick,
  disabled = false,
  loading = false,
  label,
  variant = "default",
  className = "",
  type = "button",
}) => {
  const isDisabled = disabled || loading

  return (
    <button
      type={type}
      onClick={onClick}
      disabled={isDisabled}
      title={label}
      aria-label={label}
      className={`
        w-7 h-7 rounded-md flex items-center justify-center
        border transition-colors duration-150
        disabled:opacity-50 disabled:cursor-not-allowed
        ${VARIANT_CLASSES[variant]}
        ${className}
      `}
    >
      {loading ? (
        <Loader className="w-3.5 h-3.5 animate-spin text-slate-400" />
      ) : (
        <Icon className="w-3.5 h-3.5" />
      )}
    </button>
  )
}
