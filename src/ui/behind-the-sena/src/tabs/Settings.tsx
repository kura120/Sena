import React, { useEffect, useRef, useState } from "react";
import {
  Key,
  Settings as SettingsIcon,
  Brain,
  Database,
  ScrollText,
  BarChart2,
  Plug,
  Globe,
  Sparkles,
  type LucideIcon,
} from "lucide-react";
import { fetchJson } from "../utils/api";
import {
  LLMModelSettingsForm,
  type ModelSettings,
} from "../components/forms/LLMModelSettingsForm";
import {
  MemorySettingsForm,
  type MemorySettings,
} from "../components/forms/MemorySettingsForm";
import {
  LoggingSettingsForm,
  type LoggingSettings,
} from "../components/forms/LoggingSettingsForm";
import {
  TelemetrySettingsForm,
  type TelemetrySettings,
} from "../components/forms/TelemetrySettingsForm";
import { ExtensionSettingsForm } from "../components/forms/ExtensionSettingsForm";
import {
  PersonalitySettingsForm,
  type PersonalitySettings,
} from "../components/forms/PersonalitySettingsForm";
import { ToggleSwitch } from "../components/ToggleSwitch";
import { SectionHeader } from "../components/SectionHeader";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type LlmSettingsResponse = {
  status: string;
  data?: {
    provider?: string;
    base_url?: string;
    timeout?: number;
    allow_runtime_switch?: boolean;
    switch_cooldown?: number;
    models?: {
      fast?: string | null;
      critical?: string | null;
      code?: string | null;
      router?: string | null;
    };
  };
};

type MemorySettingsResponse = {
  status: string;
  data?: {
    provider?: string;
    embeddings_model?: string;
    short_term?: { max_messages?: number; expire_after?: number };
    long_term?: { auto_extract?: boolean; extract_interval?: number };
    retrieval?: {
      dynamic_threshold?: number;
      max_results?: number;
      reranking?: boolean;
    };
    personality?: {
      inferential_learning_enabled?: boolean;
      inferential_learning_requires_approval?: boolean;
      auto_approve_enabled?: boolean;
      auto_approve_threshold?: number;
      learning_mode?: string;
      personality_token_budget?: number;
      max_fragments_in_prompt?: number;
      compress_threshold?: number;
    };
  };
};

type LoggingSettingsResponse = {
  status: string;
  data?: {
    level?: string;
    database_level?: string;
    file?: { enabled?: boolean; path?: string };
    session?: { enabled?: boolean; path?: string };
  };
};

type TelemetrySettingsResponse = {
  status: string;
  data?: {
    enabled?: boolean;
    metrics?: { collect_interval?: number; retention_days?: number };
    performance?: {
      track_response_times?: boolean;
      track_memory_usage?: boolean;
      track_extension_performance?: boolean;
    };
  };
};

type UISettingsResponse = {
  status: string;
  data?: {
    auto_open_browser?: boolean;
    behind_the_sena_port?: number;
    sena_app_port?: number;
  };
};

type Section = {
  id: string;
  label: string;
  icon: LucideIcon;
};

const SECTIONS: Section[] = [
  { id: "general", label: "General", icon: SettingsIcon },
  { id: "models", label: "Models", icon: Brain },
  { id: "memory", label: "Memory", icon: Database },
  { id: "personality", label: "Personality", icon: Sparkles },
  { id: "logging", label: "Logging", icon: ScrollText },
  { id: "telemetry", label: "Telemetry", icon: BarChart2 },
  { id: "extensions", label: "Extensions", icon: Plug },
];

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export const Settings: React.FC = () => {
  // ---- hotkey state ----
  const [hotkeyDisplay, setHotkeyDisplay] = useState<string>("Home");
  const [isListening, setIsListening] = useState<boolean>(false);
  const [isHotkeySaved, setIsHotkeySaved] = useState<boolean>(false);

  // ---- general / UI settings ----
  const [autoOpenBrowser, setAutoOpenBrowser] = useState<boolean>(false);
  const [isSavingUi, setIsSavingUi] = useState(false);
  const [uiSaved, setUiSaved] = useState(false);

  // ---- section settings ----
  const [modelSettings, setModelSettings] = useState<ModelSettings | null>(
    null,
  );
  const [memorySettings, setMemorySettings] = useState<MemorySettings | null>(
    null,
  );
  const [loggingSettings, setLoggingSettings] =
    useState<LoggingSettings | null>(null);
  const [telemetrySettings, setTelemetrySettings] =
    useState<TelemetrySettings | null>(null);
  const [personalitySettings, setPersonalitySettings] =
    useState<PersonalitySettings | null>(null);

  // ---- nav state ----
  const [activeSection, setActiveSection] = useState<string>("general");

  const containerRef = useRef<HTMLDivElement | null>(null);
  const sectionRefs = useRef<Record<string, HTMLDivElement | null>>({});

  // ---------------------------------------------------------------------------
  // Load on mount
  // ---------------------------------------------------------------------------

  useEffect(() => {
    void loadHotkey();
  }, []);
  useEffect(() => {
    void loadModelSettings();
  }, []);
  useEffect(() => {
    void loadMemorySettings();
  }, []);
  useEffect(() => {
    void loadLoggingSettings();
  }, []);
  useEffect(() => {
    void loadTelemetrySettings();
  }, []);
  useEffect(() => {
    void loadUISettings();
  }, []);
  useEffect(() => {
    void loadPersonalitySettings();
  }, []);

  // ---- hotkey ----
  const loadHotkey = async () => {
    try {
      const hotkey = await window.sena.getHotkey();
      setHotkeyDisplay(hotkey || "Home");
    } catch {
      // IPC unavailable in dev browser mode — silently skip
    }
  };

  // ---- LLM ----
  const loadModelSettings = async () => {
    try {
      const data = await fetchJson<LlmSettingsResponse>("/api/v1/settings/llm");
      setModelSettings({
        provider: data.data?.provider ?? "ollama",
        base_url: data.data?.base_url ?? "http://127.0.0.1:11434",
        timeout: data.data?.timeout ?? 120,
        allow_runtime_switch: data.data?.allow_runtime_switch ?? true,
        switch_cooldown: data.data?.switch_cooldown ?? 5,
        models: {
          fast: data.data?.models?.fast ?? null,
          critical: data.data?.models?.critical ?? null,
          code: data.data?.models?.code ?? null,
          router: data.data?.models?.router ?? null,
        },
      });
    } catch (err) {
      console.error("Failed to load LLM settings:", err);
    }
  };

  // ---- Memory ----
  const loadMemorySettings = async () => {
    try {
      const data = await fetchJson<MemorySettingsResponse>(
        "/api/v1/settings/memory",
      );
      const d = data.data;
      setMemorySettings({
        provider: d?.provider ?? "mem0",
        embeddings_model: d?.embeddings_model ?? "nomic-embed-text:latest",
        short_term: {
          max_messages: d?.short_term?.max_messages ?? 20,
          expire_after: d?.short_term?.expire_after ?? 3600,
        },
        long_term: {
          auto_extract: d?.long_term?.auto_extract ?? true,
          extract_interval: d?.long_term?.extract_interval ?? 10,
        },
        retrieval: {
          dynamic_threshold: d?.retrieval?.dynamic_threshold ?? 0.6,
          max_results: d?.retrieval?.max_results ?? 5,
          reranking: d?.retrieval?.reranking ?? true,
        },
      });
    } catch (err) {
      console.error("Failed to load memory settings:", err);
    }
  };

  // ---- Personality ----
  const loadPersonalitySettings = async () => {
    try {
      const data = await fetchJson<MemorySettingsResponse>(
        "/api/v1/settings/memory",
      );
      const p = data.data?.personality;
      setPersonalitySettings({
        inferential_learning_enabled: p?.inferential_learning_enabled ?? true,
        inferential_learning_requires_approval:
          p?.inferential_learning_requires_approval ?? true,
        auto_approve_enabled: p?.auto_approve_enabled ?? false,
        auto_approve_threshold: p?.auto_approve_threshold ?? 0.85,
        learning_mode: p?.learning_mode ?? "moderate",
        personality_token_budget: p?.personality_token_budget ?? 512,
        max_fragments_in_prompt: p?.max_fragments_in_prompt ?? 10,
        compress_threshold: p?.compress_threshold ?? 20,
      });
    } catch (err) {
      console.error("Failed to load personality settings:", err);
    }
  };

  // ---- Logging ----
  const loadLoggingSettings = async () => {
    try {
      const data = await fetchJson<LoggingSettingsResponse>(
        "/api/v1/settings/logging",
      );
      const d = data.data;
      setLoggingSettings({
        level: d?.level ?? "INFO",
        database_level: d?.database_level ?? "WARNING",
        file: {
          enabled: d?.file?.enabled ?? true,
          path: d?.file?.path ?? "data/logs/sena.log",
        },
        session: {
          enabled: d?.session?.enabled ?? true,
          path: d?.session?.path ?? "data/logs/sessions",
        },
      });
    } catch (err) {
      console.error("Failed to load logging settings:", err);
    }
  };

  // ---- Telemetry ----
  const loadTelemetrySettings = async () => {
    try {
      const data = await fetchJson<TelemetrySettingsResponse>(
        "/api/v1/settings/telemetry",
      );
      const d = data.data;
      setTelemetrySettings({
        enabled: d?.enabled ?? true,
        metrics: {
          collect_interval: d?.metrics?.collect_interval ?? 60,
          retention_days: d?.metrics?.retention_days ?? 30,
        },
        performance: {
          track_response_times: d?.performance?.track_response_times ?? true,
          track_memory_usage: d?.performance?.track_memory_usage ?? true,
          track_extension_performance:
            d?.performance?.track_extension_performance ?? true,
        },
      });
    } catch (err) {
      console.error("Failed to load telemetry settings:", err);
    }
  };

  // ---- UI settings (auto_open_browser) ----
  const loadUISettings = async () => {
    try {
      const data = await fetchJson<UISettingsResponse>("/api/v1/settings/ui");
      setAutoOpenBrowser(data.data?.auto_open_browser ?? false);
    } catch (err) {
      console.error("Failed to load UI settings:", err);
    }
  };

  const handleSaveUiSettings = async (newValue: boolean) => {
    setIsSavingUi(true);
    try {
      await fetchJson("/api/v1/settings/ui", {
        method: "POST",
        body: { auto_open_browser: newValue },
      });
      setAutoOpenBrowser(newValue);
      setUiSaved(true);
      setTimeout(() => setUiSaved(false), 2000);
    } catch (err) {
      console.error("Failed to save UI settings:", err);
    } finally {
      setIsSavingUi(false);
    }
  };

  // ---------------------------------------------------------------------------
  // Hotkey
  // ---------------------------------------------------------------------------

  const startListening = () => setIsListening(true);

  const handleKeyDown = async (e: KeyboardEvent) => {
    if (!isListening) return;
    e.preventDefault();
    const keyName = e.key.length === 1 ? e.key.toUpperCase() : e.key;
    try {
      await window.sena.setHotkey(keyName);
      setHotkeyDisplay(keyName);
      setIsListening(false);
      setIsHotkeySaved(true);
      setTimeout(() => setIsHotkeySaved(false), 2000);
    } catch {
      setIsListening(false);
    }
  };

  useEffect(() => {
    if (isListening) {
      window.addEventListener("keydown", handleKeyDown);
      return () => window.removeEventListener("keydown", handleKeyDown);
    }
  }, [isListening]);

  // ---------------------------------------------------------------------------
  // Scroll-spy nav
  // ---------------------------------------------------------------------------

  const registerSectionRef = (id: string) => (node: HTMLDivElement | null) => {
    sectionRefs.current[id] = node;
  };

  const handleScrollTo = (id: string) => {
    const node = sectionRefs.current[id];
    if (node && containerRef.current) {
      node.scrollIntoView({ behavior: "smooth", block: "start" });
      setActiveSection(id);
    }
  };

  // Update active section while scrolling
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const onScroll = () => {
      const entries = Object.entries(sectionRefs.current);
      for (let i = entries.length - 1; i >= 0; i--) {
        const [id, el] = entries[i];
        if (!el) continue;
        const rect = el.getBoundingClientRect();
        const containerRect = container.getBoundingClientRect();
        if (rect.top - containerRect.top <= 32) {
          setActiveSection(id);
          break;
        }
      }
    };

    container.addEventListener("scroll", onScroll, { passive: true });
    return () => container.removeEventListener("scroll", onScroll);
  }, []);

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  return (
    <div className="w-full h-full flex bg-slate-950 text-slate-50">
      {/* ---- Sidebar ---- */}
      <aside className="w-56 border-r border-slate-800/80 p-4 space-y-4 flex-shrink-0">
        <div className="flex items-center gap-2">
          <SettingsIcon className="w-5 h-5 text-purple-500" />
          <h2 className="text-lg font-bold">Settings</h2>
        </div>

        <nav className="space-y-1">
          {SECTIONS.map((section) => {
            const Icon = section.icon;
            const isActive = activeSection === section.id;
            return (
              <button
                key={section.id}
                onClick={() => handleScrollTo(section.id)}
                className={`w-full flex items-center gap-2 px-3 py-2 rounded text-sm transition ${
                  isActive
                    ? "bg-purple-500/15 text-purple-300 border border-purple-500/30"
                    : "text-slate-300 hover:bg-slate-900/70"
                }`}
              >
                <Icon className="w-4 h-4" />
                {section.label}
              </button>
            );
          })}
        </nav>
      </aside>

      {/* ---- Main scroll area ---- */}
      <div ref={containerRef} className="flex-1 overflow-y-auto p-6 space-y-10">
        {/* ================================================================
            GENERAL
        ================================================================ */}
        <section
          ref={registerSectionRef("general")}
          id="general"
          className="space-y-4"
        >
          <SectionHeader icon={SettingsIcon} label="General" />

          {/* Hotbar toggle */}
          <div className="bg-slate-900/50 rounded-lg border border-slate-800/70 p-4 flex items-center gap-3">
            <div className="p-2 bg-purple-500/20 rounded">
              <Key className="w-4 h-4 text-purple-500" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm text-slate-200">Hotbar Toggle</p>
              <p className="text-xs text-slate-500">
                Global keyboard shortcut to show / hide Sena
              </p>
            </div>
            <div className="flex items-center gap-2 flex-shrink-0">
              <button
                onClick={startListening}
                disabled={isListening}
                className={`px-3 py-1 rounded border font-mono font-semibold text-sm transition-all ${
                  isListening
                    ? "bg-purple-500/30 text-purple-300 border-purple-500/50"
                    : "bg-slate-800/70 text-slate-50 border-slate-700 hover:border-purple-500/50 hover:bg-slate-700"
                }`}
              >
                {isListening ? "…" : hotkeyDisplay}
              </button>
              {isHotkeySaved && (
                <span className="text-xs text-green-400 font-semibold">
                  Saved
                </span>
              )}
            </div>
          </div>

          {/* Auto open browser */}
          <div className="bg-slate-900/50 rounded-lg border border-slate-800/70 p-4 space-y-1">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-purple-500/20 rounded flex-shrink-0">
                <Globe className="w-4 h-4 text-purple-500" />
              </div>
              <div className="flex-1">
                <ToggleSwitch
                  checked={autoOpenBrowser}
                  onChange={(v) => void handleSaveUiSettings(v)}
                  disabled={isSavingUi}
                  label="Open Browser on Startup"
                  description="Automatically open the UI in your default browser when Sena starts"
                />
              </div>
              {uiSaved && (
                <span className="text-xs text-green-400 font-semibold flex-shrink-0">
                  Saved
                </span>
              )}
            </div>
          </div>
        </section>

        {/* ================================================================
            MODELS
        ================================================================ */}
        <section
          ref={registerSectionRef("models")}
          id="models"
          className="space-y-4"
        >
          <SectionHeader icon={Brain} label="Models" />
          <LLMModelSettingsForm
            value={modelSettings}
            onChange={setModelSettings}
            onSaved={loadModelSettings}
          />
        </section>

        {/* ================================================================
            MEMORY
        ================================================================ */}
        <section
          ref={registerSectionRef("memory")}
          id="memory"
          className="space-y-4"
        >
          <SectionHeader icon={Database} label="Memory" />
          <MemorySettingsForm
            value={memorySettings}
            onChange={setMemorySettings}
            onSaved={loadMemorySettings}
          />
        </section>

        {/* ================================================================
            PERSONALITY
        ================================================================ */}
        <section
          ref={registerSectionRef("personality")}
          id="personality"
          className="space-y-4"
        >
          <SectionHeader icon={Sparkles} label="Personality" />
          <PersonalitySettingsForm
            value={personalitySettings}
            onChange={setPersonalitySettings}
            onSaved={loadPersonalitySettings}
          />
        </section>

        {/* ================================================================
            LOGGING
        ================================================================ */}
        <section
          ref={registerSectionRef("logging")}
          id="logging"
          className="space-y-4"
        >
          <SectionHeader icon={ScrollText} label="Logging" />
          <LoggingSettingsForm
            value={loggingSettings}
            onChange={setLoggingSettings}
            onSaved={loadLoggingSettings}
          />
        </section>

        {/* ================================================================
            TELEMETRY
        ================================================================ */}
        <section
          ref={registerSectionRef("telemetry")}
          id="telemetry"
          className="space-y-4"
        >
          <SectionHeader icon={BarChart2} label="Telemetry" />
          <TelemetrySettingsForm
            value={telemetrySettings}
            onChange={setTelemetrySettings}
            onSaved={loadTelemetrySettings}
          />
        </section>

        {/* ================================================================
            EXTENSIONS
        ================================================================ */}
        <section
          ref={registerSectionRef("extensions")}
          id="extensions"
          className="space-y-4 pb-8"
        >
          <SectionHeader icon={Plug} label="Extensions" />
          <ExtensionSettingsForm />
        </section>
      </div>
    </div>
  );
};
