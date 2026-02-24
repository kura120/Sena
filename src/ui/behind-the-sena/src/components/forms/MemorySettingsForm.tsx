import React, { useState } from "react"
import { Save } from "lucide-react"
import { fetchJson } from "../../utils/api"
import { ToggleSwitch } from "../ToggleSwitch"

export type MemorySettings = {
  provider: string
  embeddings_model: string
  short_term: {
    max_messages: number
    expire_after: number
  }
  long_term: {
    auto_extract: boolean
    extract_interval: number
  }
  retrieval: {
    dynamic_threshold: number
    max_results: number
    reranking: boolean
  }
}

export interface MemorySettingsFormProps {
  value: MemorySettings | null
  onChange: (value: MemorySettings) => void
  onSaved?: () => void
}

export function MemorySettingsForm({
  value,
  onChange,
  onSaved,
}: MemorySettingsFormProps) {
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)

  const update = (patch: Partial<MemorySettings>) => {
    if (!value) return
    onChange({ ...value, ...patch })
  }

  const handleSave = async () => {
    if (!value) return
    setIsSaving(true)
    setError(null)
    try {
      await fetchJson("/api/v1/settings/memory", {
        method: "POST",
        body: {
          provider: value.provider,
          embeddings_model: value.embeddings_model,
          short_term_max_messages: value.short_term.max_messages,
          short_term_expire_after: value.short_term.expire_after,
          long_term_auto_extract: value.long_term.auto_extract,
          long_term_extract_interval: value.long_term.extract_interval,
          retrieval_threshold: value.retrieval.dynamic_threshold,
          retrieval_max_results: value.retrieval.max_results,
          retrieval_reranking: value.retrieval.reranking,
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
        Loading memory settings…
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

      {/* Provider + Embeddings */}
      <div className="bg-slate-900/50 rounded-lg border border-slate-800/70 p-4 space-y-4">
        <p className="text-sm text-slate-50 font-semibold">Provider</p>

        <div className="grid grid-cols-1 lg:grid-cols-[200px_1fr] gap-3 items-center">
          <div>
            <p className="text-xs text-slate-400 uppercase tracking-widest">Provider</p>
            <p className="text-[11px] text-slate-600 mt-0.5">Memory backend</p>
          </div>
          <select
            value={value.provider}
            onChange={(e) => update({ provider: e.target.value })}
            className="px-3 py-2 rounded bg-slate-900 border border-slate-800 text-slate-100 text-sm"
          >
            <option value="mem0">mem0</option>
            <option value="local">Local (SQLite)</option>
          </select>

          <div>
            <p className="text-xs text-slate-400 uppercase tracking-widest">Embeddings Model</p>
            <p className="text-[11px] text-slate-600 mt-0.5">Ollama model for vector embeddings</p>
          </div>
          <input
            value={value.embeddings_model}
            onChange={(e) => update({ embeddings_model: e.target.value })}
            placeholder="nomic-embed-text:latest"
            className="px-3 py-2 rounded bg-slate-900 border border-slate-800 text-slate-100 text-sm placeholder:text-slate-600"
          />
        </div>
      </div>

      {/* Short-term memory */}
      <div className="bg-slate-900/50 rounded-lg border border-slate-800/70 p-4 space-y-4">
        <p className="text-sm text-slate-50 font-semibold">Short-Term Memory</p>

        <div className="grid grid-cols-1 lg:grid-cols-[200px_1fr] gap-3 items-center">
          <div>
            <p className="text-xs text-slate-400 uppercase tracking-widest">Max Messages</p>
            <p className="text-[11px] text-slate-600 mt-0.5">Conversation context buffer size</p>
          </div>
          <div className="flex items-center gap-2">
            <input
              type="number"
              min={1}
              max={200}
              value={value.short_term.max_messages}
              onChange={(e) =>
                update({
                  short_term: {
                    ...value.short_term,
                    max_messages: Number(e.target.value),
                  },
                })
              }
              className="w-28 px-3 py-2 rounded bg-slate-900 border border-slate-800 text-slate-100 text-sm"
            />
            <span className="text-xs text-slate-500">messages</span>
          </div>

          <div>
            <p className="text-xs text-slate-400 uppercase tracking-widest">Expire After</p>
            <p className="text-[11px] text-slate-600 mt-0.5">How long to keep context (0 = never)</p>
          </div>
          <div className="flex items-center gap-2">
            <input
              type="number"
              min={0}
              value={value.short_term.expire_after}
              onChange={(e) =>
                update({
                  short_term: {
                    ...value.short_term,
                    expire_after: Number(e.target.value),
                  },
                })
              }
              className="w-28 px-3 py-2 rounded bg-slate-900 border border-slate-800 text-slate-100 text-sm"
            />
            <span className="text-xs text-slate-500">seconds</span>
          </div>
        </div>
      </div>

      {/* Long-term memory */}
      <div className="bg-slate-900/50 rounded-lg border border-slate-800/70 p-4 space-y-4">
        <p className="text-sm text-slate-50 font-semibold">Long-Term Memory</p>

        <ToggleSwitch
          checked={value.long_term.auto_extract}
          onChange={(v) =>
            update({ long_term: { ...value.long_term, auto_extract: v } })
          }
          label="Auto-Extract Learnings"
          description="Automatically extract facts and learnings from conversations"
        />

        <div className="grid grid-cols-1 lg:grid-cols-[200px_1fr] gap-3 items-center">
          <div>
            <p className="text-xs text-slate-400 uppercase tracking-widest">Extract Interval</p>
            <p className="text-[11px] text-slate-600 mt-0.5">Run extraction every N messages</p>
          </div>
          <div className="flex items-center gap-2">
            <input
              type="number"
              min={1}
              max={100}
              value={value.long_term.extract_interval}
              onChange={(e) =>
                update({
                  long_term: {
                    ...value.long_term,
                    extract_interval: Number(e.target.value),
                  },
                })
              }
              disabled={!value.long_term.auto_extract}
              className="w-28 px-3 py-2 rounded bg-slate-900 border border-slate-800 text-slate-100 text-sm disabled:opacity-40"
            />
            <span className="text-xs text-slate-500">messages</span>
          </div>
        </div>
      </div>

      {/* Retrieval */}
      <div className="bg-slate-900/50 rounded-lg border border-slate-800/70 p-4 space-y-4">
        <p className="text-sm text-slate-50 font-semibold">Retrieval</p>

        <div className="grid grid-cols-1 lg:grid-cols-[200px_1fr] gap-3 items-center">
          <div>
            <p className="text-xs text-slate-400 uppercase tracking-widest">Similarity Threshold</p>
            <p className="text-[11px] text-slate-600 mt-0.5">Minimum relevance score (0–1)</p>
          </div>
          <div className="flex items-center gap-3">
            <input
              type="range"
              min={0}
              max={1}
              step={0.05}
              value={value.retrieval.dynamic_threshold}
              onChange={(e) =>
                update({
                  retrieval: {
                    ...value.retrieval,
                    dynamic_threshold: Number(e.target.value),
                  },
                })
              }
              className="flex-1 accent-purple-500"
            />
            <span className="text-xs text-slate-300 w-10 text-right tabular-nums">
              {value.retrieval.dynamic_threshold.toFixed(2)}
            </span>
          </div>

          <div>
            <p className="text-xs text-slate-400 uppercase tracking-widest">Max Results</p>
            <p className="text-[11px] text-slate-600 mt-0.5">Maximum memories returned per query</p>
          </div>
          <div className="flex items-center gap-2">
            <input
              type="number"
              min={1}
              max={50}
              value={value.retrieval.max_results}
              onChange={(e) =>
                update({
                  retrieval: {
                    ...value.retrieval,
                    max_results: Number(e.target.value),
                  },
                })
              }
              className="w-28 px-3 py-2 rounded bg-slate-900 border border-slate-800 text-slate-100 text-sm"
            />
            <span className="text-xs text-slate-500">results</span>
          </div>
        </div>

        <ToggleSwitch
          checked={value.retrieval.reranking}
          onChange={(v) =>
            update({ retrieval: { ...value.retrieval, reranking: v } })
          }
          label="Re-ranking"
          description="Re-rank retrieved memories by contextual relevance before using them"
        />
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
