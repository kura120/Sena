import React, { useState } from "react"
import { Save } from "lucide-react"
import { fetchJson } from "../../utils/api"
import { ToggleSwitch } from "../ToggleSwitch"

export type TelemetrySettings = {
  enabled: boolean
  metrics: {
    collect_interval: number
    retention_days: number
  }
  performance: {
    track_response_times: boolean
    track_memory_usage: boolean
    track_extension_performance: boolean
  }
}

export interface TelemetrySettingsFormProps {
  value: TelemetrySettings | null
  onChange: (value: TelemetrySettings) => void
  onSaved?: () => void
}

export function TelemetrySettingsForm({
  value,
  onChange,
  onSaved,
}: TelemetrySettingsFormProps) {
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)

  const update = (patch: Partial<TelemetrySettings>) => {
    if (!value) return
    onChange({ ...value, ...patch })
  }

  const handleSave = async () => {
    if (!value) return
    setIsSaving(true)
    setError(null)
    try {
      await fetchJson("/api/v1/settings/telemetry", {
        method: "POST",
        body: {
          enabled: value.enabled,
          collect_interval: value.metrics.collect_interval,
          retention_days: value.metrics.retention_days,
          track_response_times: value.performance.track_response_times,
          track_memory_usage: value.performance.track_memory_usage,
          track_extension_performance:
            value.performance.track_extension_performance,
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
        Loading telemetry settings…
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

      {/* Master enable */}
      <div className="bg-slate-900/50 rounded-lg border border-slate-800/70 p-4">
        <ToggleSwitch
          checked={value.enabled}
          onChange={(v) => update({ enabled: v })}
          label="Enable Telemetry"
          description="Collect performance metrics, response times, and usage statistics locally"
        />
      </div>

      {/* Metrics collection */}
      <div
        className={`bg-slate-900/50 rounded-lg border border-slate-800/70 p-4 space-y-4 transition-opacity ${
          value.enabled ? "opacity-100" : "opacity-40 pointer-events-none"
        }`}
      >
        <p className="text-sm text-slate-50 font-semibold">Metrics Collection</p>

        <div className="grid grid-cols-1 lg:grid-cols-[200px_1fr] gap-3 items-center">
          <div>
            <p className="text-xs text-slate-400 uppercase tracking-widest">
              Collect Interval
            </p>
            <p className="text-[11px] text-slate-600 mt-0.5">
              How often to snapshot metrics
            </p>
          </div>
          <div className="flex items-center gap-2">
            <input
              type="number"
              min={10}
              max={3600}
              value={value.metrics.collect_interval}
              onChange={(e) =>
                update({
                  metrics: {
                    ...value.metrics,
                    collect_interval: Number(e.target.value),
                  },
                })
              }
              className="w-28 px-3 py-2 rounded bg-slate-900 border border-slate-800 text-slate-100 text-sm"
            />
            <span className="text-xs text-slate-500">seconds</span>
          </div>

          <div>
            <p className="text-xs text-slate-400 uppercase tracking-widest">
              Retention Period
            </p>
            <p className="text-[11px] text-slate-600 mt-0.5">
              How long to keep collected metrics
            </p>
          </div>
          <div className="flex items-center gap-2">
            <input
              type="number"
              min={1}
              max={365}
              value={value.metrics.retention_days}
              onChange={(e) =>
                update({
                  metrics: {
                    ...value.metrics,
                    retention_days: Number(e.target.value),
                  },
                })
              }
              className="w-28 px-3 py-2 rounded bg-slate-900 border border-slate-800 text-slate-100 text-sm"
            />
            <span className="text-xs text-slate-500">days</span>
          </div>
        </div>
      </div>

      {/* Performance tracking */}
      <div
        className={`bg-slate-900/50 rounded-lg border border-slate-800/70 p-4 space-y-4 transition-opacity ${
          value.enabled ? "opacity-100" : "opacity-40 pointer-events-none"
        }`}
      >
        <p className="text-sm text-slate-50 font-semibold">Performance Tracking</p>

        <div className="space-y-4">
          <ToggleSwitch
            checked={value.performance.track_response_times}
            onChange={(v) =>
              update({
                performance: {
                  ...value.performance,
                  track_response_times: v,
                },
              })
            }
            label="Track Response Times"
            description="Record how long each LLM request takes end-to-end"
          />

          <ToggleSwitch
            checked={value.performance.track_memory_usage}
            onChange={(v) =>
              update({
                performance: {
                  ...value.performance,
                  track_memory_usage: v,
                },
              })
            }
            label="Track Memory Usage"
            description="Monitor memory retrieval latency and hit rates"
          />

          <ToggleSwitch
            checked={value.performance.track_extension_performance}
            onChange={(v) =>
              update({
                performance: {
                  ...value.performance,
                  track_extension_performance: v,
                },
              })
            }
            label="Track Extension Performance"
            description="Measure execution time and error rates per extension"
          />
        </div>
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
