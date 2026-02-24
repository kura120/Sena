import React, { type ReactNode } from "react"

interface TabLayoutProps {
  children: ReactNode
  /** Extra classes applied to the root element */
  className?: string
  /** Whether the root element itself scrolls. Defaults to false —
   *  most tabs manage their own internal scroll. */
  scrollable?: boolean
}

/**
 * Root wrapper for every tab window.
 * Provides the consistent full-height flex-column dark background.
 */
export const TabLayout: React.FC<TabLayoutProps> = ({
  children,
  className = "",
  scrollable = false,
}) => {
  return (
    <div
      className={`h-full flex flex-col bg-[#0A0E27] text-slate-50 ${
        scrollable ? "overflow-y-auto" : "overflow-hidden"
      } ${className}`}
    >
      {children}
    </div>
  )
}
