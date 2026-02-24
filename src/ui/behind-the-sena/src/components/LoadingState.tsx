import React from "react"
import { Loader } from "lucide-react"

interface LoadingStateProps {
  message?: string
  /** Extra classes applied to the root container */
  className?: string
  /** Size of the spinner: sm = 16px, md = 24px, lg = 32px */
  size?: "sm" | "md" | "lg"
}

const SIZE_CLASSES = {
  sm: "w-4 h-4",
  md: "w-6 h-6",
  lg: "w-8 h-8",
}

/**
 * Centered loading spinner with an optional message.
 * Used as a consistent loading placeholder across all tabs.
 */
export const LoadingState: React.FC<LoadingStateProps> = ({
  message,
  className = "",
  size = "md",
}) => {
  return (
    <div
      className={`flex flex-col items-center justify-center gap-3 py-16 px-6 text-center ${className}`}
    >
      <Loader
        className={`${SIZE_CLASSES[size]} text-purple-400 animate-spin`}
      />
      {message && (
        <p className="text-sm text-slate-500">{message}</p>
      )}
    </div>
  )
}
