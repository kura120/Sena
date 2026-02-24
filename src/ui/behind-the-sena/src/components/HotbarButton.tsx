import React, { useState, useRef } from "react";
import { createPortal } from "react-dom";
import { motion, AnimatePresence } from "framer-motion";
import { LucideIcon } from "lucide-react";

export interface HotbarButtonProps {
  icon: LucideIcon;
  label: string;
  color?: string;
  strokeColor?: string;
  onClick?: () => void;
  isActive?: boolean;
}

export function HotbarButton({
  icon: Icon,
  label,
  color = "bg-purple-500",
  strokeColor = "border-transparent",
  onClick,
  isActive = false,
}: HotbarButtonProps) {
  const [isHovered, setIsHovered] = useState(false);
  const [tooltipRect, setTooltipRect] = useState<DOMRect | null>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);

  const handleMouseEnter = () => {
    if (buttonRef.current) {
      setTooltipRect(buttonRef.current.getBoundingClientRect());
    }
    setIsHovered(true);
  };

  const handleMouseLeave = () => {
    setIsHovered(false);
    setTooltipRect(null);
  };

  const tooltip =
    isHovered && tooltipRect
      ? createPortal(
          <AnimatePresence>
            <motion.div
              key="tooltip"
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 4 }}
              transition={{ duration: 0.15 }}
              style={{
                position: "fixed",
                left: `${tooltipRect.left + tooltipRect.width / 2}px`,
                top: `${tooltipRect.top - 8}px`,
                transform: "translate(-50%, -100%)",
                zIndex: 9999,
                pointerEvents: "none",
              }}
              className="px-2.5 py-1 bg-slate-900/95 text-slate-50 text-xs font-medium rounded-lg shadow-xl border border-slate-700/80 whitespace-nowrap"
            >
              {label}
            </motion.div>
          </AnimatePresence>,
          document.body,
        )
      : null;

  return (
    <div className="relative">
      {tooltip}

      <motion.button
        ref={buttonRef}
        className={`
          relative w-9 h-9 rounded-xl
          ${color} ${strokeColor}
          border flex items-center justify-center
          shadow-md
          transition-all duration-200
          ${isActive ? "ring-2 ring-white/80 ring-offset-2 ring-offset-slate-950" : ""}
        `}
        whileHover={{
          scale: 1.1,
          y: -2,
          transition: { type: "spring", stiffness: 400, damping: 10 },
        }}
        whileTap={{
          scale: 0.95,
          transition: { type: "spring", stiffness: 400, damping: 10 },
        }}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
        onClick={onClick}
      >
        {/* Glow effect */}
        <motion.div
          className={`absolute inset-0 rounded-xl ${color} blur-xl opacity-0`}
          animate={{ opacity: isHovered ? 0.45 : 0 }}
          transition={{ duration: 0.2 }}
        />

        {/* Icon */}
        <Icon className="w-4 h-4 text-white relative z-10" />
      </motion.button>
    </div>
  );
}
