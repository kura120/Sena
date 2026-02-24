import React, { useState } from "react"
import { Save } from "lucide-react"
import { fetchJson } from "../../utils/api"
import { ToggleSwitch } from "../ToggleSwitch"

export type LoggingSettings = {
  level: string
  database_level: string
  file: {
    enabled: boolean
    path: string
  }
  session: {
    enabled: boolean
    path: string
  }
}

export interface LoggingSettingsFormProps {
  value: LoggingSettings | null
  onChange: (value: LoggingSettings) => void
  onSaved?: () => void
}

const LOG_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

const LEVEL_COLORS: Record<string, string> = {
  DEBUG: "text-slate-400",
  INFO: "text-blue-400",
  WARNING: "text-yellow-400",
  ERROR: "text-red-400",
  CRITICAL: "text-red-600",
}

export function LoggingSettingsForm({
  value,
  onChange,
  onSaved,
}: LoggingSettingsFormProps) {
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)

  const update = (patch: Partial<LoggingSettings>) => {
    if (!value) return
    onChange({ ...value, ...patch })
  }

  const handleSave = async () => {
    if (!value) return
    setIsSaving(true)
    setError(null)
    try {
      await fetchJson("/api/v1/settings/logging", {
        method: "POST",
        body: {
          level: value.level,
          database_level: value.database_level,
          file_enabled: value.file.enabled,
          session_enabled: value.session.enabled,
        },
      })
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
      onSaved?.()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save settings")
    } finally {
      setIsSaving(false)
    }
  }

  if (!value) {
    return (
      <div className="bg-slate-900/50 rounded-lg border border-slate-800/70 p-4 text-sm text-slate-500">
        Loading logging settings…
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {error && (
        <div className="text-xs text-red-300 bg-red-500/10 border border-red-500/30 rounded px-3 py-2">
          {error}
        </div>
      )}

      {/* Log levels */}
      <div className="bg-slate-900/50 rounded-lg border border-slate-800/70 p-4 space-y-4">
        <p className="text-sm text-slate-50 font-semibold">Log Levels</p>

        <div className="grid grid-cols-1 lg:grid-cols-[200px_1fr] gap-3 items-center">
          <div>
            <p className="text-xs text-slate-400 uppercase tracking-widest">Application Level</p>
            <p className="text-[11px] text-slate-600 mt-0.5">Controls verbosity of Sena's own logs</p>
          </div>
          <select
            value={value.level}
            onChange={(e) => update({ level: e.target.value })}
            className="px-3 py-2 rounded bg-slate-900 border border-slate-800 text-slate-100 text-sm"
          >
            {LOG_LEVELS.map((lvl) => (
              <option key={lvl} value={lvl}>
                <span className={LEVEL_COLORS[lvl]}>{lvl}</span>
              </option>
            ))}
          </select>

          <div>
            <p className="text-xs text-slate-400 uppercase tracking-widest">Database Level</p>
            <p className="text-[11px] text-slate-600 mt-0.5">SQLAlchemy / aiosqlite log verbosity</p>
          </div>
          <select
            value={value.database_level}
            onChange={(e) => update({ database_level: e.target.value })}
            className="px-3 py-2 rounded bg-slate-900 border border-slate-800 text-slate-100 text-sm"
          >
            {LOG_LEVELS.map((lvl) => (
              <option key={lvl} value={lvl}>
                {lvl}
              </option>
            ))}
          </select>
        </div>

        {/* Level indicator legend */}
        <div className="flex items-center gap-3 flex-wrap pt-1">
          {LOG_LEVELS.map((lvl) => (
            <span
              key={lvl}
              className={`text-[11px] font-mono font-semibold ${LEVEL_COLORS[lvl]}`}
            >
              {lvl}
            </span>
          ))}
          <span className="text-[11px] text-slate-600 ml-auto">
            Higher levels capture fewer events
          </span>
        </div>
      </div>

      {/* File logging */}
      <div className="bg-slate-900/50 rounded-lg border border-slate-800/70 p-4 space-y-4">
        <ToggleSwitch
          checked={value.file.enabled}
          onChange={(v) => update({ file: { ...value.file, enabled: v } })}
          label="File Logging"
          description="Write logs to a persistent file on disk"
        />

        {value.file.enabled && (
          <div className="grid grid-cols-1 lg:grid-cols-[200px_1fr] gap-3 items-center">
            <div>
              <p className="text-xs text-slate-400 uppercase tracking-widest">Log File Path</p>
              <p className="text-[11px] text-slate-600 mt-0.5">Relative to app data directory</p>
            </div>
            <input
              value={value.file.path}
              readOnly
              className="px-3 py-2 rounded bg-slate-950 border border-slate-800 text-slate-500 text-sm font-mono cursor-not-allowed"
              title="Path is system-managed and cannot be changed here"
            />
          </div>
        )}
      </div>

      {/* Session logging */}
      <div className="bg-slate-900/50 rounded-lg border border-slate-800/70 p-4 space-y-4">
        <ToggleSwitch
          checked={value.session.enabled}
          onChange={(v) =>
            update({ session: { ...value.session, enabled: v } })
          }
          label="Session Logging"
          description="Write a separate log file per application session"
        />

        {value.session.enabled && (
          <div className="grid grid-cols-1 lg:grid-cols-[200px_1fr] gap-3 items-center">
            <div>
              <p className="text-xs text-slate-400 uppercase tracking-widest">Session Log Directory</p>
              <p className="text-[11px] text-slate-600 mt-0.5">Relative to app data directory</p>
            </div>
            <input
              value={value.session.path}
              readOnly
              className="px-3 py-2 rounded bg-slate-950 border border-slate-800 text-slate-500 text-sm font-mono cursor-not-allowed"
              title="Path is system-managed and cannot be changed here"
            />
          </div>
        )}
      </div>

      {/* Save bar */}
      <div className="flex items-center justify-end gap-2">
        {saved && (
          <span className="text-xs text-green-400 font-semibold">Saved</span>
        )}
        <button
          onClick={handleSave}
          disabled={isSaving}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded bg-purple-500/20 text-purple-300 border border-purple-500/40 text-xs font-medium hover:bg-purple-500/30 transition disabled:opacity-50"
        >
          <Save className="w-3.5 h-3.5" />
          {isSaving ? "Saving…" : "Save"}
        </button>
      </div>
    </div>
  )
}
