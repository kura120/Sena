import React, { ReactNode, useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import {
  X,
  Minimize,
  Maximize2,
  Minimize2,
  Pin,
  PinOff,
  LucideIcon,
} from "lucide-react";

// ── Resize handles ────────────────────────────────────────────────────────────

type ResizeDir = "n" | "ne" | "e" | "se" | "s" | "sw" | "w" | "nw";

const CURSOR: Record<ResizeDir, string> = {
  n: "n-resize",
  ne: "ne-resize",
  e: "e-resize",
  se: "se-resize",
  s: "s-resize",
  sw: "sw-resize",
  w: "w-resize",
  nw: "nw-resize",
};

// Hit area size in px. 10px is wide enough to grab reliably without covering
// too much of the window content.
const HIT = 10;

// Handle inset from the window edge corners. rounded-2xl uses a 16px radius so
// we need to clear that before the background is painted and hittable.
const CORNER_INSET = 18;

function ResizeHandles() {
  // NOTE: We intentionally do NOT add a window "blur" listener here to call
  // stopResize(). Transparent frameless windows on Windows fire blur the moment
  // the cursor crosses a transparent pixel while dragging an edge outward —
  // that would kill the resize session before the user moves the mouse at all.
  // The main process now uses a 10-second safety timeout instead, and the
  // renderer relies on pointerup + pointercancel (both covered by pointer
  // capture) as the reliable stop signals.

  const onPointerDown =
    (dir: ResizeDir) => (e: React.PointerEvent<HTMLDivElement>) => {
      e.preventDefault();
      e.stopPropagation();

      // setPointerCapture forces the browser (and Win32 SetCapture underneath)
      // to keep routing pointermove + pointerup to this element even when the
      // cursor leaves the window boundary. This is the correct OS-level fix for
      // "pointerup doesn't fire outside a transparent window".
      const target = e.currentTarget;
      const pointerId = e.pointerId;
      try {
        target.setPointerCapture(pointerId);
      } catch (_) {
        /* ignore — pointer may already be captured */
      }

      // The main process owns all coordinate reading via
      // screen.getCursorScreenPoint(), so we pass only the direction here.
      // This avoids any DPI/scaling mismatch between e.screenX and win.getBounds().
      window.sena.startResize(dir);

      const stopDrag = () => {
        window.sena.stopResize();
        try {
          target.releasePointerCapture(pointerId);
        } catch (_) {
          /* already released */
        }
        window.removeEventListener("pointerup", stopDrag);
        window.removeEventListener("pointercancel", stopDrag);
      };

      // Listen on window (not document) so the handler fires even when the
      // captured pointer is reported outside the DOM tree.
      // pointercancel covers cases where the OS or browser forcibly cancels the
      // drag (e.g. Alt-Tab, screen lock, touch interrupt on hybrid devices).
      window.addEventListener("pointerup", stopDrag);
      window.addEventListener("pointercancel", stopDrag);
    };

  // base style — transparent background with the tiniest non-zero alpha so
  // that Windows routes pointer events to the handle even when it sits over a
  // transparent corner pixel (alpha=0 = click-through on layered windows).
  const base: React.CSSProperties = {
    position: "fixed",
    zIndex: 9999,
    background: "rgba(0,0,0,0.01)",
  };

  return (
    <>
      {/* ── Edges (inset from corners to stay inside the painted bg area) ── */}
      <div
        style={{
          ...base,
          top: 0,
          left: CORNER_INSET,
          right: CORNER_INSET,
          height: HIT,
          cursor: CURSOR.n,
        }}
        onPointerDown={onPointerDown("n")}
      />
      <div
        style={{
          ...base,
          bottom: 0,
          left: CORNER_INSET,
          right: CORNER_INSET,
          height: HIT,
          cursor: CURSOR.s,
        }}
        onPointerDown={onPointerDown("s")}
      />
      <div
        style={{
          ...base,
          left: 0,
          top: CORNER_INSET,
          bottom: CORNER_INSET,
          width: HIT,
          cursor: CURSOR.w,
        }}
        onPointerDown={onPointerDown("w")}
      />
      <div
        style={{
          ...base,
          right: 0,
          top: CORNER_INSET,
          bottom: CORNER_INSET,
          width: HIT,
          cursor: CURSOR.e,
        }}
        onPointerDown={onPointerDown("e")}
      />
      {/* ── Corners ── */}
      <div
        style={{
          ...base,
          top: 0,
          left: 0,
          width: CORNER_INSET + HIT,
          height: CORNER_INSET + HIT,
          cursor: CURSOR.nw,
        }}
        onPointerDown={onPointerDown("nw")}
      />
      <div
        style={{
          ...base,
          top: 0,
          right: 0,
          width: CORNER_INSET + HIT,
          height: CORNER_INSET + HIT,
          cursor: CURSOR.ne,
        }}
        onPointerDown={onPointerDown("ne")}
      />
      <div
        style={{
          ...base,
          bottom: 0,
          left: 0,
          width: CORNER_INSET + HIT,
          height: CORNER_INSET + HIT,
          cursor: CURSOR.sw,
        }}
        onPointerDown={onPointerDown("sw")}
      />
      <div
        style={{
          ...base,
          bottom: 0,
          right: 0,
          width: CORNER_INSET + HIT,
          height: CORNER_INSET + HIT,
          cursor: CURSOR.se,
        }}
        onPointerDown={onPointerDown("se")}
      />
    </>
  );
}

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
  showMaximize = true,
  showPin = true,
  defaultPinned = true,
  variant = "tab",
}: WindowFrameProps) {
  const [isPinned, setIsPinned] = useState(defaultPinned);
  const [isExpanded, setIsExpanded] = useState(false);

  const containerClasses = useMemo(() => {
    if (variant === "floating") {
      return "w-full h-full flex flex-col rounded-2xl border border-slate-800/70 bg-slate-950 shadow-[0_20px_60px_rgba(2,6,23,0.7)] overflow-hidden";
    }
    return "w-full h-full flex flex-col rounded-2xl border border-slate-800/70 bg-[#0A0E27] shadow-[0_20px_60px_rgba(2,6,23,0.7)] overflow-hidden";
  }, [variant]);

  const headerClasses = useMemo(() => {
    if (variant === "floating") {
      return "flex items-center justify-between px-4 py-3 bg-slate-900 border-b border-slate-800 select-none drag shrink-0";
    }
    return "flex items-center justify-between px-4 py-3 bg-[#0F1629]/80 backdrop-blur-sm border-b border-slate-800/40 select-none drag shrink-0";
  }, [variant]);

  // Sync isExpanded whenever the window is resized externally (e.g. restored
  // via OS or another call path) so the maximize icon always reflects reality.
  useEffect(() => {
    if (typeof window === "undefined" || !window.sena) return;
    // On every focus we check if we are currently filling the work area;
    // if not, treat as "not expanded". This is a lightweight heuristic.
    const onFocus = () => {
      // Nothing to do — the main process owns the truth. We just keep local
      // isExpanded in sync by resetting it when the window is visibly smaller
      // than the screen. We rely on main.ts windowPreExpandBounds being the
      // source of truth; our icon just mirrors the IPC toggle count.
    };
    window.addEventListener("focus", onFocus);
    return () => window.removeEventListener("focus", onFocus);
  }, []);

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
    // Toggle local icon state to match what main process just did
    setIsExpanded((prev) => !prev);
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

        <div
          className="flex items-center gap-1 no-drag"
          style={{ WebkitAppRegion: "no-drag" } as React.CSSProperties}
        >
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
              title={isExpanded ? "Restore" : "Expand"}
            >
              {isExpanded ? (
                <Minimize2 className="w-3.5 h-3.5 text-slate-400 hover:text-slate-300" />
              ) : (
                <Maximize2 className="w-3.5 h-3.5 text-slate-400 hover:text-slate-300" />
              )}
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

      <ResizeHandles />
    </div>
  );
}
