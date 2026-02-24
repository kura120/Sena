import React, { ReactNode, useMemo, useState } from "react";
import { motion } from "framer-motion";
import {
  X,
  Minimize,
  Maximize2,
  Pin,
  PinOff,
  LucideIcon,
} from "lucide-react";

export interface WindowFrameProps {
  title: string;
  windowId: string;
  children: ReactNode;
  icon?: LucideIcon;
  onClose?: () => void;
  showMinimize?: boolean;
  showMaximize?: boolean;
  showPin?: boolean;
  defaultPinned?: boolean;
  variant?: "tab" | "floating";
}

export function WindowFrame({
  title,
  windowId,
  children,
  icon: Icon,
  onClose,
  showMinimize = true,
  showMaximize = false,
  showPin = true,
  defaultPinned = true,
  variant = "tab",
}: WindowFrameProps) {
  const [isPinned, setIsPinned] = useState(defaultPinned);

  const containerClasses = useMemo(() => {
    if (variant === "floating") {
      return "w-full h-full flex flex-col rounded-2xl border border-slate-800/70 bg-slate-950 shadow-[0_20px_60px_rgba(2,6,23,0.7)] overflow-hidden -mt-8 pt-8";
    }
    return "w-full h-full flex flex-col rounded-2xl border border-slate-800/70 bg-[#0A0E27] shadow-[0_20px_60px_rgba(2,6,23,0.7)] overflow-hidden";
  }, [variant]);

  const headerClasses = useMemo(() => {
    if (variant === "floating") {
      return "flex items-center justify-between px-4 py-3 bg-slate-900 border-b border-slate-800 select-none drag";
    }
    return "flex items-center justify-between px-4 py-3 bg-[#0F1629]/80 backdrop-blur-sm border-b border-slate-800/40 select-none drag";
  }, [variant]);

  const handleClose = async () => {
    if (onClose) {
      onClose();
      return;
    }
    await window.sena.closeWindow(windowId);
  };

  const handleMinimize = async () => {
    await window.sena.minimizeWindow();
  };

  const handleMaximize = async () => {
    await window.sena.maximizeWindow();
  };

  const handleTogglePin = async () => {
    const next = !isPinned;
    setIsPinned(next);
    await window.sena.setWindowPinned(next);
  };

  return (
    <div className={containerClasses}>
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className={headerClasses}
      >
        <div className="flex items-center gap-2.5">
          {Icon && <Icon className="w-4 h-4 text-purple-400" />}
          <h1 className="text-sm font-medium text-slate-200">{title}</h1>
        </div>

        <div className="flex items-center gap-1 no-drag">
          {showMinimize && (
            <button
              onClick={handleMinimize}
              className="w-7 h-7 rounded-md flex items-center justify-center hover:bg-slate-700/30 transition-colors"
              title="Minimize"
            >
              <Minimize className="w-3.5 h-3.5 text-slate-400 hover:text-slate-300" />
            </button>
          )}

          {showMaximize && (
            <button
              onClick={handleMaximize}
              className="w-7 h-7 rounded-md flex items-center justify-center hover:bg-slate-700/30 transition-colors"
              title="Maximize"
            >
              <Maximize2 className="w-3.5 h-3.5 text-slate-400 hover:text-slate-300" />
            </button>
          )}

          {showPin && (
            <button
              onClick={handleTogglePin}
              className={`w-7 h-7 rounded-md flex items-center justify-center transition-colors ${
                isPinned ? "hover:bg-emerald-500/10" : "hover:bg-slate-700/30"
              }`}
              title={isPinned ? "Disable topmost" : "Keep window on top"}
            >
              {isPinned ? (
                <Pin className="w-3.5 h-3.5 text-emerald-400" />
              ) : (
                <PinOff className="w-3.5 h-3.5 text-slate-400" />
              )}
            </button>
          )}

          <button
            onClick={handleClose}
            className="w-7 h-7 rounded-md flex items-center justify-center hover:bg-red-500/20 text-slate-400 hover:text-red-400 transition-colors"
            title="Close"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      </motion.div>

      <div className="flex-1 overflow-hidden">{children}</div>
    </div>
  );
}
