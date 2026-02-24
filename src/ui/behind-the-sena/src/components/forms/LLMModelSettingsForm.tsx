import React, { useEffect, useMemo, useState } from "react";
import { Brain, RefreshCw, Save, ChevronDown, ChevronUp } from "lucide-react";
import { fetchJson } from "../../utils/api";
import { ToggleSwitch } from "../ToggleSwitch";

export type ModelSettings = {
  provider: string;
  base_url: string;
  timeout: number;
  allow_runtime_switch: boolean;
  switch_cooldown: number;
  models: {
    fast: string | null;
    critical: string | null;
    code: string | null;
    router: string | null;
  };
};

type OllamaModelsResponse = {
  status: string;
  provider: string;
  base_url: string;
  models: string[];
};

type SavePayload = {
  provider: string;
  base_url: string;
  timeout: number;
  allow_runtime_switch: boolean;
  switch_cooldown: number;
  fast: string | null;
  critical: string | null;
  code: string | null;
  router: string | null;
};

export interface LLMModelSettingsFormProps {
  value: ModelSettings | null;
  onChange: (value: ModelSettings) => void;
  onSaved?: () => void;
}

const MODEL_SLOTS = [
  {
    key: "fast" as const,
    label: "Fast",
    description: "Used for quick responses and low-latency tasks",
  },
  {
    key: "critical" as const,
    label: "Critical",
    description: "Used for reasoning and high-stakes tasks",
  },
  {
    key: "code" as const,
    label: "Code",
    description: "Used for code generation and analysis",
  },
  {
    key: "router" as const,
    label: "Router",
    description: "Used for intent classification and routing",
  },
];

export function LLMModelSettingsForm({
  value,
  onChange,
  onSaved,
}: LLMModelSettingsFormProps) {
  const [availableModels, setAvailableModels] = useState<string[]>([]);
  const [isLoadingModels, setIsLoadingModels] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);

  const providerValue = value?.provider ?? "ollama";
  const baseUrlValue = value?.base_url ?? "http://127.0.0.1:11434";
  const timeoutValue = value?.timeout ?? 120;
  const allowRuntimeSwitch = value?.allow_runtime_switch ?? true;
  const switchCooldown = value?.switch_cooldown ?? 5;

  const sortedModels = useMemo(
    () => [...availableModels].sort((a, b) => a.localeCompare(b)),
    [availableModels],
  );

  const updateValue = (next: Partial<ModelSettings>) => {
    const merged: ModelSettings = {
      provider: next.provider ?? providerValue,
      base_url: next.base_url ?? baseUrlValue,
      timeout: next.timeout ?? timeoutValue,
      allow_runtime_switch: next.allow_runtime_switch ?? allowRuntimeSwitch,
      switch_cooldown: next.switch_cooldown ?? switchCooldown,
      models: {
        fast: next.models?.fast ?? value?.models.fast ?? null,
        critical: next.models?.critical ?? value?.models.critical ?? null,
        code: next.models?.code ?? value?.models.code ?? null,
        router: next.models?.router ?? value?.models.router ?? null,
      },
    };
    onChange(merged);
  };

  const updateModelSlot = (
    slot: keyof ModelSettings["models"],
    newValue: string,
  ) => {
    updateValue({
      models: {
        fast: value?.models.fast ?? null,
        critical: value?.models.critical ?? null,
        code: value?.models.code ?? null,
        router: value?.models.router ?? null,
        [slot]: newValue || null,
      },
    });
  };

  useEffect(() => {
    void handleRefreshModels();
  }, []);

  const handleRefreshModels = async () => {
    setIsLoadingModels(true);
    setError(null);
    try {
      const data = await fetchJson<OllamaModelsResponse>(
        "/api/v1/settings/ollama/models",
      );
      setAvailableModels(Array.isArray(data.models) ? data.models : []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load models");
    } finally {
      setIsLoadingModels(false);
    }
  };

  const handleSave = async () => {
    if (!value) return;
    setIsSaving(true);
    setError(null);
    try {
      const payload: SavePayload = {
        provider: value.provider,
        base_url: value.base_url,
        timeout: value.timeout,
        allow_runtime_switch: value.allow_runtime_switch,
        switch_cooldown: value.switch_cooldown,
        fast: value.models.fast,
        critical: value.models.critical,
        code: value.models.code,
        router: value.models.router,
      };
      await fetchJson("/api/v1/settings/llm", {
        method: "POST",
        body: payload,
      });
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
      onSaved?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save settings");
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="space-y-3">
      {/* Provider + Base URL card */}
      <div className="bg-slate-900/50 rounded-lg border border-slate-800/70 p-4 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-slate-50 font-semibold">
              Model Provider
            </p>
            <p className="text-xs text-slate-500">
              Local providers only. Choose models per role.
            </p>
          </div>
          <button
            onClick={handleRefreshModels}
            disabled={isLoadingModels}
            className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded border border-slate-700 text-xs text-slate-300 hover:text-slate-50 hover:border-slate-500 transition disabled:opacity-50"
          >
            <RefreshCw
              className={`w-3.5 h-3.5 ${isLoadingModels ? "animate-spin" : ""}`}
            />
            Refresh
          </button>
        </div>

        {error && (
          <div className="text-xs text-red-300 bg-red-500/10 border border-red-500/30 rounded px-3 py-2">
            {error}
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-[200px_1fr] gap-3 items-center">
          <p className="text-xs text-slate-400 uppercase tracking-widest">
            Provider
          </p>
          <select
            value={providerValue}
            onChange={(e) => updateValue({ provider: e.target.value })}
            className="px-3 py-2 rounded bg-slate-900 border border-slate-800 text-slate-100 text-sm"
          >
            <option value="ollama">Ollama (Local)</option>
          </select>

          <p className="text-xs text-slate-400 uppercase tracking-widest">
            Base URL
          </p>
          <input
            value={baseUrlValue}
            onChange={(e) => updateValue({ base_url: e.target.value })}
            placeholder="http://127.0.0.1:11434"
            className="px-3 py-2 rounded bg-slate-900 border border-slate-800 text-slate-100 text-sm placeholder:text-slate-600"
          />
        </div>
      </div>

      {/* Model slots card */}
      <div className="bg-slate-900/50 rounded-lg border border-slate-800/70 p-4 space-y-3">
        <p className="text-sm text-slate-50 font-semibold">Model Roles</p>

        <div className="grid grid-cols-1 lg:grid-cols-[200px_1fr] gap-3 items-center">
          {MODEL_SLOTS.map(({ key, label, description }) => (
            <React.Fragment key={key}>
              <div>
                <p className="text-xs text-slate-400 uppercase tracking-widest">
                  {label}
                </p>
                <p className="text-[11px] text-slate-600 mt-0.5">
                  {description}
                </p>
              </div>
              <select
                value={value?.models[key] ?? ""}
                onChange={(e) => updateModelSlot(key, e.target.value)}
                className="px-3 py-2 rounded bg-slate-900 border border-slate-800 text-slate-100 text-sm"
              >
                <option value="">
                  {isLoadingModels ? "Loading models…" : "Select model"}
                </option>
                {sortedModels.map((model) => (
                  <option key={model} value={model}>
                    {model}
                  </option>
                ))}
              </select>
            </React.Fragment>
          ))}
        </div>
      </div>

      {/* Advanced settings (collapsible) */}
      <div className="bg-slate-900/50 rounded-lg border border-slate-800/70 overflow-hidden">
        <button
          onClick={() => setShowAdvanced((v) => !v)}
          className="w-full flex items-center justify-between px-4 py-3 text-sm text-slate-300 hover:text-slate-50 hover:bg-slate-900/70 transition"
        >
          <span className="font-medium">Advanced</span>
          {showAdvanced ? (
            <ChevronUp className="w-4 h-4 text-slate-500" />
          ) : (
            <ChevronDown className="w-4 h-4 text-slate-500" />
          )}
        </button>

        {showAdvanced && (
          <div className="px-4 pb-4 space-y-4 border-t border-slate-800/70 pt-3">
            <div className="grid grid-cols-1 lg:grid-cols-[200px_1fr] gap-3 items-center">
              <div>
                <p className="text-xs text-slate-400 uppercase tracking-widest">
                  Timeout
                </p>
                <p className="text-[11px] text-slate-600 mt-0.5">
                  Request timeout in seconds
                </p>
              </div>
              <div className="flex items-center gap-2">
                <input
                  type="number"
                  min={1}
                  max={600}
                  value={timeoutValue}
                  onChange={(e) =>
                    updateValue({ timeout: Number(e.target.value) })
                  }
                  className="w-28 px-3 py-2 rounded bg-slate-900 border border-slate-800 text-slate-100 text-sm"
                />
                <span className="text-xs text-slate-500">seconds</span>
              </div>

              <div>
                <p className="text-xs text-slate-400 uppercase tracking-widest">
                  Switch Cooldown
                </p>
                <p className="text-[11px] text-slate-600 mt-0.5">
                  Cooldown between model switches
                </p>
              </div>
              <div className="flex items-center gap-2">
                <input
                  type="number"
                  min={0}
                  max={300}
                  value={switchCooldown}
                  onChange={(e) =>
                    updateValue({ switch_cooldown: Number(e.target.value) })
                  }
                  className="w-28 px-3 py-2 rounded bg-slate-900 border border-slate-800 text-slate-100 text-sm"
                />
                <span className="text-xs text-slate-500">seconds</span>
              </div>
            </div>

            <div className="pt-1">
              <ToggleSwitch
                checked={allowRuntimeSwitch}
                onChange={(v) => updateValue({ allow_runtime_switch: v })}
                label="Allow Runtime Model Switch"
                description="Permit switching models without restarting Sena"
              />
            </div>
          </div>
        )}
      </div>

      {/* Save bar */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-[11px] text-slate-500">
          <Brain className="w-3.5 h-3.5 text-purple-400" />
          Changes apply on next startup unless runtime switch is enabled.
        </div>
        <div className="flex items-center gap-2">
          {saved && (
            <span className="text-xs text-green-400 font-semibold">Saved</span>
          )}
          <button
            onClick={handleSave}
            disabled={!value || isSaving}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded bg-purple-500/20 text-purple-300 border border-purple-500/40 text-xs font-medium hover:bg-purple-500/30 transition disabled:opacity-50"
          >
            <Save className="w-3.5 h-3.5" />
            {isSaving ? "Saving…" : "Save"}
          </button>
        </div>
      </div>
    </div>
  );
}
