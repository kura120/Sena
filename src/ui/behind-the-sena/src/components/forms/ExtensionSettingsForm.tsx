import React, { useCallback, useEffect, useState } from "react"
import { Plug, RefreshCw, AlertCircle } from "lucide-react"
import { fetchJson } from "../../utils/api"
import { ToggleSwitch } from "../ToggleSwitch"

type Extension = {
  name: string
  enabled: boolean
  metadata?: {
    description?: string
    version?: string
    author?: string
  }
}

type ExtensionsResponse = {
  status: string
  extensions: Extension[]
  total: number
}

type ToggleResponse = {
  status: string
  extension_name: string
  enabled: boolean
}

export function ExtensionSettingsForm() {
  const [extensions, setExtensions] = useState<Extension[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [toggling, setToggling] = useState<Set<string>>(new Set())
  const [togglingErrors, setTogglingErrors] = useState<Record<string, string>>({})

  const loadExtensions = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    try {
      const data = await fetchJson<ExtensionsResponse>("/api/v1/extensions")
      setExtensions(Array.isArray(data.extensions) ? data.extensions : [])
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load extensions")
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    void loadExtensions()
  }, [loadExtensions])

  const handleToggle = async (name: string, newEnabled: boolean) => {
    setToggling((prev) => new Set(prev).add(name))
    setTogglingErrors((prev) => {
      const next = { ...prev }
      delete next[name]
      return next
    })

    try {
      await fetchJson<ToggleResponse>(
        `/api/v1/extensions/${encodeURIComponent(name)}/toggle`,
        {
          method: "POST",
          body: { enabled: newEnabled },
        },
      )
      setExtensions((prev) =>
        prev.map((ext) =>
          ext.name === name ? { ...ext, enabled: newEnabled } : ext,
        ),
      )
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to toggle extension"
      setTogglingErrors((prev) => ({ ...prev, [name]: message }))
    } finally {
      setToggling((prev) => {
        const next = new Set(prev)
        next.delete(name)
        return next
      })
    }
  }

  if (isLoading) {
    return (
      <div className="bg-slate-900/50 rounded-lg border border-slate-800/70 p-6 flex items-center gap-3">
        <RefreshCw className="w-4 h-4 text-slate-500 animate-spin" />
        <span className="text-sm text-slate-500">Loading extensions…</span>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-slate-900/50 rounded-lg border border-slate-800/70 p-4 space-y-3">
        <div className="flex items-center gap-2 text-red-400 text-sm">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>{error}</span>
        </div>
        <button
          onClick={loadExtensions}
          className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded border border-slate-700 text-xs text-slate-300 hover:text-slate-50 hover:border-slate-500 transition"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          Retry
        </button>
      </div>
    )
  }

  if (extensions.length === 0) {
    return (
      <div className="bg-slate-900/50 rounded-lg border border-slate-800/70 p-6 text-center space-y-2">
        <Plug className="w-6 h-6 text-slate-600 mx-auto" />
        <p className="text-sm text-slate-500">No extensions loaded.</p>
        <p className="text-xs text-slate-600">
          Add extensions to{" "}
          <span className="font-mono text-slate-500">src/extensions/core/</span>{" "}
          or{" "}
          <span className="font-mono text-slate-500">src/extensions/user/</span>
          .
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-xs text-slate-500">
          {extensions.filter((e) => e.enabled).length} of {extensions.length}{" "}
          enabled
        </p>
        <button
          onClick={loadExtensions}
          className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded border border-slate-700 text-xs text-slate-300 hover:text-slate-50 hover:border-slate-500 transition"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          Refresh
        </button>
      </div>

      <div className="bg-slate-900/50 rounded-lg border border-slate-800/70 divide-y divide-slate-800/70">
        {extensions.map((ext) => {
          const isToggling = toggling.has(ext.name)
          const toggleError = togglingErrors[ext.name]

          return (
            <div key={ext.name} className="p-4 space-y-1.5">
              <ToggleSwitch
                checked={ext.enabled}
                onChange={(v) => void handleToggle(ext.name, v)}
                disabled={isToggling}
                label={ext.metadata?.description
                  ? ext.name
                  : ext.name}
                description={
                  ext.metadata?.description ??
                  "No description provided"
                }
              />

              <div className="flex items-center gap-3 pl-0.5">
                {ext.metadata?.version && (
                  <span className="text-[11px] text-slate-600 font-mono">
                    v{ext.metadata.version}
                  </span>
                )}
                {ext.metadata?.author && (
                  <span className="text-[11px] text-slate-600">
                    by {ext.metadata.author}
                  </span>
                )}
                {isToggling && (
                  <span className="text-[11px] text-slate-500 flex items-center gap-1">
                    <RefreshCw className="w-3 h-3 animate-spin" />
                    Updating…
                  </span>
                )}
                {toggleError && (
                  <span className="text-[11px] text-red-400 flex items-center gap-1">
                    <AlertCircle className="w-3 h-3" />
                    {toggleError}
                  </span>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
