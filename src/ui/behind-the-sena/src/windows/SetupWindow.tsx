import React, { useState } from "react";
import { Settings, X } from "lucide-react";
import {
  LLMModelSettingsForm,
  type ModelSettings,
} from "../components/forms/LLMModelSettingsForm";

const defaultModelSettings: ModelSettings = {
  provider: "ollama",
  base_url: "http://127.0.0.1:11434",
  timeout: 120,
  allow_runtime_switch: true,
  switch_cooldown: 5,
  models: {
    fast: null,
    critical: null,
    code: null,
    router: null,
  },
  reasoning_model: null,
  reasoning_enabled: false,
};

export function SetupWindow() {
  const [modelSettings, setModelSettings] =
    useState<ModelSettings>(defaultModelSettings);
  const [isDone, setIsDone] = useState(false);

  const handleSaved = () => {
    setIsDone(true);
    // Signal to main process that setup is complete
    window.sena.signalSetupComplete?.();
  };

  return (
    <div className="w-full h-full flex flex-col bg-transparent select-none">
      {/* Custom title bar — draggable */}
      <div
        className="flex items-center justify-between px-4 py-2.5 border-b border-white/10 bg-[#060d20]/90 backdrop-blur-sm"
        style={{ WebkitAppRegion: "drag" } as React.CSSProperties}
      >
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-purple-500/20 flex items-center justify-center">
            <Settings className="w-4 h-4 text-purple-400" />
          </div>
          <div>
            <p className="text-sm text-slate-100 font-medium leading-tight">
              Sena — Initial Setup
            </p>
            <p className="text-[10px] text-slate-500 leading-tight">
              Configure your LLM provider and models
            </p>
          </div>
        </div>

        <button
          onClick={() => window.sena.closeWindow?.("setup")}
          className="w-7 h-7 rounded-md flex items-center justify-center text-slate-500 hover:text-slate-200 hover:bg-white/10 transition"
          style={{ WebkitAppRegion: "no-drag" } as React.CSSProperties}
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Content area */}
      <div className="flex-1 overflow-y-auto bg-gradient-to-br from-[#08163b] via-[#050e24] to-[#020712]">
        <div className="p-6 space-y-5">
          {/* Header info */}
          <div className="space-y-2">
            <h1 className="text-lg text-slate-50 font-semibold tracking-tight">
              Welcome to Sena
            </h1>
            <p className="text-sm text-slate-400 leading-relaxed">
              Before Sena can start, you need to select a provider and assign
              models to each role. Make sure your local LLM provider (e.g.
              Ollama) is running, then pick models below.
            </p>
          </div>

          {/* Divider */}
          <div className="h-px bg-white/5" />

          {/* Role descriptions */}
          <div className="grid grid-cols-3 gap-3">
            <RoleCard
              title="Fast"
              description="Quick responses, lightweight tasks, and low-latency interactions."
              color="emerald"
            />
            <RoleCard
              title="Critical"
              description="Complex reasoning, important decisions, and deep analysis."
              color="amber"
            />
            <RoleCard
              title="Code"
              description="Code generation, debugging, refactoring, and technical tasks."
              color="blue"
            />
          </div>

          {/* Divider */}
          <div className="h-px bg-white/5" />

          {/* The actual settings form */}
          <LLMModelSettingsForm
            value={modelSettings}
            onChange={setModelSettings}
            onSaved={handleSaved}
          />

          {/* Done state */}
          {isDone && (
            <div className="rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-300 font-medium text-center">
              Settings saved! Sena is continuing startup…
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/* ── Tiny helper ── */

function RoleCard({
  title,
  description,
  color,
}: {
  title: string;
  description: string;
  color: "emerald" | "amber" | "blue";
}) {
  const dotColor = {
    emerald: "bg-emerald-400",
    amber: "bg-amber-400",
    blue: "bg-blue-400",
  }[color];

  return (
    <div className="rounded-lg border border-white/5 bg-white/[0.02] p-3 space-y-1.5">
      <div className="flex items-center gap-2">
        <span className={`w-2 h-2 rounded-full ${dotColor}`} />
        <span className="text-xs text-slate-200 font-semibold uppercase tracking-wider">
          {title}
        </span>
      </div>
      <p className="text-[11px] text-slate-500 leading-relaxed">
        {description}
      </p>
    </div>
  );
}
