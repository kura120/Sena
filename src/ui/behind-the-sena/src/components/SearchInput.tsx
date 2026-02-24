import React from "react"
import { Search, X } from "lucide-react"

interface SearchInputProps {
  value: string
  onChange: (value: string) => void
  placeholder?: string
  onClear?: () => void
  /** Extra classes applied to the wrapper div */
  className?: string
  disabled?: boolean
  autoFocus?: boolean
}

/**
 * Search input with a leading search icon and optional clear button.
 * Replaces the legacy SearchBox component — use this going forward.
 */
export const SearchInput: React.FC<SearchInputProps> = ({
  value,
  onChange,
  placeholder = "Search…",
  onClear,
  className = "",
  disabled = false,
  autoFocus = false,
}) => {
  const handleClear = () => {
    onChange("")
    onClear?.()
  }

  return (
    <div className={`relative flex items-center ${className}`}>
      <Search className="absolute left-3 w-4 h-4 text-slate-500 pointer-events-none" />

      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        disabled={disabled}
        autoFocus={autoFocus}
        className="
          w-full pl-9 pr-8 py-2
          bg-slate-900/80 border border-slate-700/60 rounded-lg
          text-sm text-slate-100 placeholder:text-slate-500
          focus:outline-none focus:ring-2 focus:ring-purple-500/40 focus:border-purple-500/50
          disabled:opacity-50 disabled:cursor-not-allowed
          transition-colors duration-150
        "
      />

      {value && (
        <button
          type="button"
          onClick={handleClear}
          className="absolute right-2.5 p-0.5 text-slate-500 hover:text-slate-300 transition-colors rounded"
          aria-label="Clear search"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      )}
    </div>
  )
}
