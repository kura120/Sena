import React, { useState } from "react";
import { Save, Info } from "lucide-react";
import { fetchJson } from "../../utils/api";
import { ToggleSwitch } from "../ToggleSwitch";

export type PersonalitySettings = {
  inferential_learning_enabled: boolean;
  inferential_learning_requires_approval: boolean;
  auto_approve_enabled: boolean;
  auto_approve_threshold: number;
  learning_mode: string;
  personality_token_budget: number;
  max_fragments_in_prompt: number;
  compress_threshold: number;
};

export interface PersonalitySettingsFormProps {
  value: PersonalitySettings | null;
  onChange: (value: PersonalitySettings) => void;
  onSaved?: () => void;
}

const LEARNING_MODES = [
  {
    value: "conservative",
    label: "Conservative",
    description: "Only high-confidence facts (≥90%) are suggested",
  },
  {
    value: "moderate",
    label: "Moderate",
    description:
      "Balanced inference — facts with ≥70% confidence are suggested",
  },
  {
    value: "aggressive",
    label: "Aggressive",
    description: "All inferred facts (≥50% confidence) are suggested",
  },
];

function InfoTip({ text }: { text: string }) {
  const [visible, setVisible] = useState(false);
  return (
    <span className="relative inline-flex items-center">
      <button
        type="button"
        onMouseEnter={() => setVisible(true)}
        onMouseLeave={() => setVisible(false)}
        onFocus={() => setVisible(true)}
        onBlur={() => setVisible(false)}
        className="ml-1 text-slate-500 hover:text-slate-300 transition"
        aria-label="More information"
      >
        <Info className="w-3.5 h-3.5" />
      </button>
      {visible && (
        <span className="absolute left-5 top-0 z-50 w-56 bg-slate-800 border border-slate-600 text-slate-300 text-xs rounded px-2.5 py-2 shadow-lg pointer-events-none">
          {text}
        </span>
      )}
    </span>
  );
}

export function PersonalitySettingsForm({
  value,
  onChange,
  onSaved,
}: PersonalitySettingsFormProps) {
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  const update = (patch: Partial<PersonalitySettings>) => {
    if (!value) return;
    onChange({ ...value, ...patch });
  };

  const handleSave = async () => {
    if (!value) return;
    setIsSaving(true);
    setError(null);
    try {
      await fetchJson("/api/v1/settings/memory", {
        method: "POST",
        body: {
          personality_inferential_learning_enabled:
            value.inferential_learning_enabled,
          personality_inferential_learning_requires_approval:
            value.inferential_learning_requires_approval,
          personality_auto_approve_enabled: value.auto_approve_enabled,
          personality_auto_approve_threshold: value.auto_approve_threshold,
          personality_learning_mode: value.learning_mode,
          personality_token_budget: value.personality_token_budget,
          personality_max_fragments_in_prompt: value.max_fragments_in_prompt,
          personality_compress_threshold: value.compress_threshold,
        },
      });
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
      onSaved?.();
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Failed to save personality settings",
      );
    } finally {
      setIsSaving(false);
    }
  };

  if (!value) {
    return (
      <div className="bg-slate-900/50 rounded-lg border border-slate-800/70 p-4 text-sm text-slate-500">
        Loading personality settings…
      </div>
    );
  }

  const thresholdPct = Math.round(value.auto_approve_threshold * 100);

  return (
    <div className="space-y-3">
      {error && (
        <div className="text-xs text-red-300 bg-red-500/10 border border-red-500/30 rounded px-3 py-2">
          {error}
        </div>
      )}

      {/* Privacy & Learning */}
      <div className="bg-slate-900/50 rounded-lg border border-slate-800/70 p-4 space-y-4">
        <p className="text-sm text-slate-50 font-semibold">
          Privacy & Learning
        </p>

        <ToggleSwitch
          checked={value.inferential_learning_enabled}
          onChange={(v) => update({ inferential_learning_enabled: v })}
          label="Inferential Learning"
          description="Allow Sena to infer personal preferences and facts from your conversations"
        />

        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-1">
            <span className="text-sm text-slate-200">
              Require Approval for Inferred Facts
            </span>
            <InfoTip text="When enabled, Sena will suggest inferred personality facts for your review before adding them to its memory. Recommended for privacy." />
          </div>
          <ToggleSwitch
            checked={value.inferential_learning_requires_approval}
            onChange={(v) =>
              update({ inferential_learning_requires_approval: v })
            }
            label=""
            description="Show inferred fragments as 'pending' until you manually approve or reject them"
            disabled={!value.inferential_learning_enabled}
          />
        </div>
      </div>

      {/* Learning Mode */}
      <div className="bg-slate-900/50 rounded-lg border border-slate-800/70 p-4 space-y-3">
        <div className="flex items-center gap-2">
          <p className="text-sm text-slate-50 font-semibold">Learning Mode</p>
          <InfoTip text="Controls the minimum confidence threshold for Sena to suggest personality fragments from conversations." />
        </div>

        <div className="space-y-2">
          {LEARNING_MODES.map((mode) => (
            <label
              key={mode.value}
              className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-all ${
                value.learning_mode === mode.value
                  ? "border-purple-500/60 bg-purple-500/10"
                  : "border-slate-700/60 hover:border-slate-600 bg-slate-900/30"
              } ${!value.inferential_learning_enabled ? "opacity-40 pointer-events-none" : ""}`}
            >
              <input
                type="radio"
                name="learning_mode"
                value={mode.value}
                checked={value.learning_mode === mode.value}
                onChange={() => update({ learning_mode: mode.value })}
                disabled={!value.inferential_learning_enabled}
                className="mt-0.5 accent-purple-500"
              />
              <div className="min-w-0">
                <p className="text-sm text-slate-200 font-medium">
                  {mode.label}
                </p>
                <p className="text-xs text-slate-500 mt-0.5">
                  {mode.description}
                </p>
              </div>
            </label>
          ))}
        </div>
      </div>

      {/* Auto-Approval */}
      <div className="bg-slate-900/50 rounded-lg border border-slate-800/70 p-4 space-y-4">
        <div className="flex items-center gap-2">
          <p className="text-sm text-slate-50 font-semibold">Auto-Approval</p>
          <InfoTip text="When enabled, highly-confident inferred facts are automatically approved without requiring manual review." />
        </div>

        <ToggleSwitch
          checked={value.auto_approve_enabled}
          onChange={(v) => update({ auto_approve_enabled: v })}
          label="Enable Auto-Approval"
          description="Automatically approve inferred facts above the confidence threshold"
          disabled={
            !value.inferential_learning_enabled ||
            value.inferential_learning_requires_approval
          }
        />

        {value.inferential_learning_requires_approval && (
          <p className="text-xs text-yellow-400/80 bg-yellow-500/10 border border-yellow-600/30 rounded px-3 py-2">
            Auto-approval is disabled while &quot;Require Approval&quot; is
            turned on. Disable approval requirement to enable auto-approval.
          </p>
        )}

        {/* Threshold slider */}
        <div
          className={`space-y-2 transition-opacity ${
            !value.auto_approve_enabled ||
            value.inferential_learning_requires_approval
              ? "opacity-40 pointer-events-none"
              : ""
          }`}
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs text-slate-400 uppercase tracking-widest">
                Confidence Threshold
              </p>
              <p className="text-[11px] text-slate-600 mt-0.5">
                Facts above this score are auto-approved
              </p>
            </div>
            <span
              className={`text-sm font-semibold tabular-nums ${
                thresholdPct >= 85
                  ? "text-emerald-400"
                  : thresholdPct >= 70
                    ? "text-yellow-400"
                    : "text-red-400"
              }`}
            >
              {thresholdPct}%
            </span>
          </div>
          <input
            type="range"
            min={0.5}
            max={1.0}
            step={0.05}
            value={value.auto_approve_threshold}
            onChange={(e) =>
              update({ auto_approve_threshold: Number(e.target.value) })
            }
            disabled={
              !value.auto_approve_enabled ||
              value.inferential_learning_requires_approval
            }
            className="w-full accent-purple-500"
          />
          <div className="flex justify-between text-[10px] text-slate-600">
            <span>50% (permissive)</span>
            <span>85% (recommended)</span>
            <span>100% (strict)</span>
          </div>
        </div>
      </div>

      {/* System Prompt Tuning */}
      <div className="bg-slate-900/50 rounded-lg border border-slate-800/70 p-4 space-y-4">
        <div className="flex items-center gap-2">
          <p className="text-sm text-slate-50 font-semibold">
            System Prompt Tuning
          </p>
          <InfoTip text="Controls how much of the personality context is injected into every LLM request. Lower values save tokens; higher values include more personality detail." />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-[220px_1fr] gap-3 items-center">
          <div>
            <p className="text-xs text-slate-400 uppercase tracking-widest">
              Token Budget
            </p>
            <p className="text-[11px] text-slate-600 mt-0.5">
              Max tokens reserved for personality block
            </p>
          </div>
          <div className="flex items-center gap-2">
            <input
              type="number"
              min={64}
              max={2048}
              step={64}
              value={value.personality_token_budget}
              onChange={(e) =>
                update({ personality_token_budget: Number(e.target.value) })
              }
              className="w-28 px-3 py-2 rounded bg-slate-900 border border-slate-800 text-slate-100 text-sm"
            />
            <span className="text-xs text-slate-500">tokens</span>
          </div>

          <div>
            <p className="text-xs text-slate-400 uppercase tracking-widest">
              Max Fragments in Prompt
            </p>
            <p className="text-[11px] text-slate-600 mt-0.5">
              Cap on personality facts injected per request
            </p>
          </div>
          <div className="flex items-center gap-2">
            <input
              type="number"
              min={1}
              max={50}
              value={value.max_fragments_in_prompt}
              onChange={(e) =>
                update({ max_fragments_in_prompt: Number(e.target.value) })
              }
              className="w-28 px-3 py-2 rounded bg-slate-900 border border-slate-800 text-slate-100 text-sm"
            />
            <span className="text-xs text-slate-500">fragments</span>
          </div>

          <div>
            <p className="text-xs text-slate-400 uppercase tracking-widest">
              Compression Threshold
            </p>
            <p className="text-[11px] text-slate-600 mt-0.5">
              Compress into a summary when fragment count exceeds this
            </p>
          </div>
          <div className="flex items-center gap-2">
            <input
              type="number"
              min={5}
              max={200}
              value={value.compress_threshold}
              onChange={(e) =>
                update({ compress_threshold: Number(e.target.value) })
              }
              className="w-28 px-3 py-2 rounded bg-slate-900 border border-slate-800 text-slate-100 text-sm"
            />
            <span className="text-xs text-slate-500">fragments</span>
          </div>
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
  );
}
