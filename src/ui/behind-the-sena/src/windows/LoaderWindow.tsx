import React, { useEffect, useRef, useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  Circle,
  Loader2,
  Terminal,
} from "lucide-react";
import { buildApiUrl, fetchJson, getApiBaseUrl } from "../utils/api";

interface BootStep {
  id: string;
  label: string;
  detail: string;
  status: "pending" | "loading" | "completed" | "error";
}

interface LogLine {
  text: string;
  level: "info" | "warn" | "error" | "success" | "debug";
  timestamp: string;
}

interface LlmSettingsResponse {
  status: string;
  data?: {
    provider?: string;
    base_url?: string;
    models?: {
      fast?: string | null;
      critical?: string | null;
      code?: string | null;
    };
  };
}

function classifyLine(raw: string): LogLine["level"] {
  const lower = raw.toLowerCase();
  if (
    lower.includes("error") ||
    lower.includes("failed") ||
    lower.includes("fatal") ||
    lower.includes("panic") ||
    lower.includes("exception") ||
    lower.includes("traceback") ||
    lower.includes("critical")
  )
    return "error";
  if (
    lower.includes("warn") ||
    lower.includes("warning") ||
    lower.includes("missing") ||
    lower.includes("not found") ||
    lower.includes("unavailable")
  )
    return "warn";
  if (
    lower.includes("ready") ||
    lower.includes("success") ||
    lower.includes("passed") ||
    lower.includes("started") ||
    lower.includes("initialized") ||
    lower.includes("connected") ||
    lower.includes("complete")
  )
    return "success";
  if (lower.includes("debug") || lower.includes("trace")) return "debug";
  return "info";
}

function levelColor(level: LogLine["level"]): string {
  switch (level) {
    case "error":
      return "text-red-400";
    case "warn":
      return "text-yellow-400";
    case "success":
      return "text-emerald-400";
    case "debug":
      return "text-slate-500";
    default:
      return "text-slate-300";
  }
}

function levelPrefix(level: LogLine["level"]): string {
  switch (level) {
    case "error":
      return "ERR";
    case "warn":
      return "WRN";
    case "success":
      return "OK ";
    case "debug":
      return "DBG";
    default:
      return "INF";
  }
}

function levelPrefixColor(level: LogLine["level"]): string {
  switch (level) {
    case "error":
      return "text-red-500 font-bold";
    case "warn":
      return "text-yellow-500 font-semibold";
    case "success":
      return "text-emerald-500 font-semibold";
    case "debug":
      return "text-slate-600";
    default:
      return "text-slate-500";
  }
}

export function LoaderWindow() {
  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [stepDetails, setStepDetails] = useState<Record<string, string>>({});
  const [errors, setErrors] = useState<string[]>([]);
  const [isChecking, setIsChecking] = useState(true);
  const [logLines, setLogLines] = useState<LogLine[]>([]);
  const [awaitingSetup, setAwaitingSetup] = useState(false);
  const [hasFatalError, setHasFatalError] = useState(false);
  // Shows "Continue anyway" button after too many consecutive health failures
  const [showContinueAnyway, setShowContinueAnyway] = useState(false);

  const outputRef = useRef<HTMLDivElement>(null);
  const autoAdvanceRef = useRef<NodeJS.Timeout | null>(null);
  const healthCheckRef = useRef<NodeJS.Timeout | null>(null);
  const settingsReadyRef = useRef(false);
  const setupWindowOpenRef = useRef(false);
  const hasSignaledRef = useRef(false);
  // Consecutive health-check failures — used to surface "Continue anyway"
  const healthFailCountRef = useRef(0);

  const totalSteps = 4;
  const progress = Math.min(currentStepIndex, totalSteps);
  const progressPercent = Math.min((progress / totalSteps) * 100, 100);

  const statusLabel = hasFatalError
    ? "Failed"
    : awaitingSetup
      ? "Setup required"
      : isChecking
        ? "Starting"
        : "Ready";

  const bootSteps: BootStep[] = [
    {
      id: "core",
      label: "Initializing Core",
      detail: stepDetails["core"] ?? "Loading runtime & config...",
      status:
        hasFatalError && currentStepIndex === 0
          ? "error"
          : currentStepIndex > 0
            ? "completed"
            : "loading",
    },
    {
      id: "config",
      label: "Loading Config",
      detail: stepDetails["config"] ?? "Reading settings.yaml...",
      status:
        currentStepIndex > 1
          ? "completed"
          : currentStepIndex === 1
            ? "loading"
            : "pending",
    },
    {
      id: "llm",
      label: "Connecting LLM",
      detail: stepDetails["llm"] ?? "Starting Ollama & loading models...",
      status:
        currentStepIndex > 2
          ? "completed"
          : currentStepIndex === 2
            ? "loading"
            : "pending",
    },
    {
      id: "memory",
      label: "Starting Memory",
      detail:
        stepDetails["memory"] ?? "Initializing short & long-term memory...",
      status:
        currentStepIndex > 3
          ? "completed"
          : currentStepIndex === 3
            ? "loading"
            : "pending",
    },
  ];

  const isPopulated = (value?: string | null) =>
    Boolean(value && value.trim().length > 0);

  // Only the fast model is required to start — critical and code are optional.
  // Requiring all three blocked startup when only the fast model was configured.
  const isSettingsComplete = (data: LlmSettingsResponse): boolean => {
    return (
      isPopulated(data.data?.provider) && isPopulated(data.data?.models?.fast)
    );
  };

  const signalReady = () => {
    void window.sena.signalLoaderReady?.();
  };

  const finalizeReady = () => {
    if (hasSignaledRef.current) return;
    hasSignaledRef.current = true;
    setCurrentStepIndex(4);
    setIsChecking(false);
    setAwaitingSetup(false);
    if (autoAdvanceRef.current) clearInterval(autoAdvanceRef.current);
    if (healthCheckRef.current) clearInterval(healthCheckRef.current);
    signalReady();
  };

  const pushLog = (text: string) => {
    const now = new Date();
    const ts = `${now.getHours().toString().padStart(2, "0")}:${now.getMinutes().toString().padStart(2, "0")}:${now.getSeconds().toString().padStart(2, "0")}`;
    const level = classifyLine(text);
    setLogLines((prev) => {
      const next = [...prev, { text, level, timestamp: ts }];
      return next.slice(-120); // keep last 120 lines
    });
  };

  const ensureSettingsGate = async (): Promise<boolean> => {
    if (settingsReadyRef.current) return true;
    try {
      const data = await fetchJson<LlmSettingsResponse>("/api/v1/settings/llm");
      if (isSettingsComplete(data)) {
        settingsReadyRef.current = true;
        setAwaitingSetup(false);
        return true;
      }
      if (!setupWindowOpenRef.current) {
        setupWindowOpenRef.current = true;
        setAwaitingSetup(true);
        void window.sena.openSetupWindow?.();
      }
      return false;
    } catch {
      return false;
    }
  };

  useEffect(() => {
    let mounted = true;

    window.sena.onStartupStep((data) => {
      if (!mounted) return;
      const msg = data.step.toLowerCase();

      if (msg.includes("config")) {
        setCurrentStepIndex(1);
        setStepDetails((p) => ({ ...p, config: data.step }));
      } else if (
        msg.includes("llm") ||
        msg.includes("service") ||
        msg.includes("ollama")
      ) {
        setCurrentStepIndex(2);
        setStepDetails((p) => ({ ...p, llm: data.step }));
      } else if (msg.includes("memory")) {
        setCurrentStepIndex(3);
        setStepDetails((p) => ({ ...p, memory: data.step }));
      } else if (msg.includes("ready")) {
        setCurrentStepIndex(4);
      }

      pushLog(data.step);
    });

    window.sena.onStartupError((data) => {
      if (!mounted) return;
      setErrors((prev) => [...prev, data.error]);
      setHasFatalError(true);
      setIsChecking(false);
      pushLog(`ERROR: ${data.error}`);
    });

    const sanitize = (value: string) =>
      value
        .replace(/\x1b\[[0-9;]*m/g, "")
        .replace(/[^\x09\x0A\x0D\x20-\x7E]/g, "")
        .trim();

    window.sena.onServerLog((message) => {
      if (!mounted) return;
      message
        .split(/\r?\n/)
        .map((l) => sanitize(l))
        .filter((l) => l.length > 0)
        .forEach((l) => pushLog(l));
    });

    autoAdvanceRef.current = setInterval(() => {
      if (!mounted) return;
      setCurrentStepIndex((prev) => (prev < 3 ? prev + 1 : prev));
    }, 1000);

    const checkHealth = async () => {
      try {
        const settingsReady = await ensureSettingsGate();
        if (!settingsReady) return;

        const baseUrl = await getApiBaseUrl();
        // Timeout raised to 30 s — the first call triggers Sena/Ollama
        // initialisation which can take 10-30 s on large models.
        const response = await fetch(buildApiUrl(baseUrl, "/health"), {
          signal: AbortSignal.timeout(30000),
        });
        if (!mounted) return;

        if (response.ok) {
          // Reset failure counter on success
          healthFailCountRef.current = 0;
          finalizeReady();
          return;
        }

        if (response.status === 503) {
          healthFailCountRef.current += 1;

          // Parse the 503 body so we can surface the real reason.
          const body = await response.json().catch(() => null);

          // Build a human-readable message from the detail object.
          const detail = body?.detail ?? body;
          const errorCode: string =
            typeof detail === "object" && detail?.error
              ? String(detail.error)
              : "SERVICE_UNAVAILABLE";
          const errorMsg: string =
            typeof detail === "object" && detail?.message
              ? String(detail.message)
              : typeof detail === "string"
                ? detail
                : "Sena is not ready yet.";

          // Push once per distinct failure (de-bounce at 5 failures) so the
          // log panel doesn't flood, but still shows something is wrong.
          if (healthFailCountRef.current % 5 === 1) {
            pushLog(`ERROR: [${errorCode}] ${errorMsg}`);
          }

          // Legacy mem0 check kept for backwards compatibility
          const mem0Connected = body?.components?.memory?.mem0_connected;
          if (mem0Connected === false) {
            setErrors((prev) => [
              ...prev,
              "mem0 is unavailable. Start mem0 or switch memory provider.",
            ]);
          }

          // After ~10 s of consecutive 503s, offer the user a way out.
          if (healthFailCountRef.current >= 20 && !showContinueAnyway) {
            setShowContinueAnyway(true);
          }
        }
      } catch {
        // fetch threw (connection refused or AbortSignal) — keep trying
        healthFailCountRef.current += 1;
        if (healthFailCountRef.current >= 20 && !showContinueAnyway) {
          setShowContinueAnyway(true);
        }
      }
    };

    void checkHealth();
    healthCheckRef.current = setInterval(checkHealth, 500);

    return () => {
      mounted = false;
      if (autoAdvanceRef.current) clearInterval(autoAdvanceRef.current);
      if (healthCheckRef.current) clearInterval(healthCheckRef.current);
      window.sena.removeListener("startup-step");
      window.sena.removeListener("startup-error");
      window.sena.removeListener("server-log");
    };
  }, []);

  useEffect(() => {
    if (outputRef.current) {
      outputRef.current.scrollTop = outputRef.current.scrollHeight;
    }
  }, [logLines]);

  const errorLines = logLines.filter((l) => l.level === "error");

  return (
    <div className="relative w-full h-full rounded-[28px] border border-white/10 bg-gradient-to-br from-[#08163b] via-[#050e24] to-[#020712] p-5 shadow-[0_25px_70px_rgba(2,6,19,0.75)] overflow-hidden flex flex-col gap-4">
      {/* Background accents */}
      <div className="absolute inset-0 bg-gradient-to-b from-white/10 via-transparent to-transparent opacity-20 pointer-events-none" />
      <div className="absolute right-8 top-8 w-24 h-24 bg-emerald-400/10 blur-3xl rounded-full opacity-40" />
      <div className="absolute left-8 bottom-8 w-20 h-20 bg-blue-400/8 blur-3xl rounded-full opacity-30" />

      {/* Header */}
      <div className="relative flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <img
            src="/assets/sena-logo.png"
            alt="Sena"
            className="w-9 h-9 object-contain"
          />
          <div>
            <p className="text-sm text-white font-semibold tracking-tight">
              Sena
            </p>
            <p className="text-[10px] text-slate-400 tracking-[0.2em] uppercase">
              Boot sequence
            </p>
          </div>
        </div>
        <span
          className={`px-2.5 py-1 text-[10px] rounded-full font-medium ${
            hasFatalError
              ? "bg-red-500/15 text-red-300 border border-red-500/25"
              : awaitingSetup
                ? "bg-yellow-500/15 text-yellow-300 border border-yellow-500/25"
                : isChecking
                  ? "bg-blue-500/15 text-blue-300 border border-blue-500/25"
                  : "bg-emerald-500/15 text-emerald-300 border border-emerald-500/25"
          }`}
        >
          {statusLabel}
        </span>
      </div>

      {/* Steps + Log output side-by-side */}
      <div className="relative flex gap-3 flex-1 min-h-0">
        {/* Boot steps */}
        <div className="flex flex-col gap-3 w-[180px] shrink-0">
          {bootSteps.map((step, index) => (
            <div key={step.id} className="relative pl-7">
              {index < bootSteps.length - 1 && (
                <span className="absolute left-[12px] top-5 bottom-[-8px] w-px bg-white/10" />
              )}
              <div className="flex flex-col gap-0.5">
                <div className="flex items-center gap-2">
                  <div className="absolute left-0 w-5 h-5 rounded-full bg-white/5 flex items-center justify-center">
                    {step.status === "completed" ? (
                      <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                    ) : step.status === "error" ? (
                      <AlertCircle className="w-3 h-3 text-red-400" />
                    ) : step.status === "loading" ? (
                      <Loader2 className="w-3 h-3 text-blue-300 animate-spin" />
                    ) : (
                      <Circle className="w-3 h-3 text-slate-600" />
                    )}
                  </div>
                  <span
                    className={`text-[12px] font-medium leading-tight ${
                      step.status === "pending"
                        ? "text-slate-500"
                        : step.status === "error"
                          ? "text-red-300"
                          : "text-slate-100"
                    }`}
                  >
                    {step.label}
                  </span>
                </div>
                <span className="text-[10px] text-slate-500 leading-snug pl-0">
                  {step.status === "completed"
                    ? "Done"
                    : step.status === "loading"
                      ? step.detail
                      : step.status === "error"
                        ? "Failed"
                        : "Waiting"}
                </span>
              </div>
            </div>
          ))}
        </div>

        {/* Log output panel */}
        <div className="flex flex-col gap-1.5 flex-1 min-w-0 min-h-0">
          <div className="flex items-center gap-1.5">
            <Terminal className="w-3 h-3 text-slate-500" />
            <span className="text-[10px] text-slate-500 uppercase tracking-[0.15em]">
              Server output
            </span>
            {logLines.length > 0 && (
              <span className="ml-auto text-[10px] text-slate-600">
                {logLines.length} line{logLines.length !== 1 ? "s" : ""}
              </span>
            )}
          </div>
          <div
            ref={outputRef}
            className="flex-1 rounded-lg bg-black/40 border border-slate-800/60 px-2.5 py-2 font-mono overflow-y-auto text-[10.5px] leading-relaxed"
            style={{ minHeight: 0 }}
          >
            {logLines.length === 0 ? (
              <div className="text-slate-600 italic">
                Waiting for server logs...
              </div>
            ) : (
              logLines.map((line, i) => (
                <div
                  key={i}
                  className={`flex gap-1.5 whitespace-pre-wrap break-all ${levelColor(line.level)}`}
                >
                  <span
                    className={`shrink-0 select-none ${levelPrefixColor(line.level)}`}
                  >
                    {levelPrefix(line.level)}
                  </span>
                  <span className="text-slate-600 shrink-0 select-none">
                    {line.timestamp}
                  </span>
                  <span className="min-w-0">{line.text}</span>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Error summary panel — only shown when there are errors */}
      {errorLines.length > 0 && (
        <div className="relative shrink-0 rounded-lg border border-red-500/25 bg-red-500/8 px-3 py-2.5 max-h-[90px] overflow-y-auto">
          <div className="flex items-center gap-1.5 mb-1.5">
            <AlertCircle className="w-3 h-3 text-red-400 shrink-0" />
            <span className="text-[10px] text-red-400 font-semibold uppercase tracking-wider">
              {errorLines.length} error{errorLines.length !== 1 ? "s" : ""}{" "}
              detected
            </span>
          </div>
          {errorLines.map((l, i) => (
            <p
              key={i}
              className="text-[10.5px] text-red-300 font-mono leading-snug"
            >
              {l.text}
            </p>
          ))}
        </div>
      )}

      {/* "Continue anyway" banner — shown after repeated health failures */}
      {showContinueAnyway && isChecking && !hasFatalError && (
        <div className="relative shrink-0 rounded-lg border border-yellow-500/30 bg-yellow-500/8 px-3 py-2.5 flex items-start gap-3">
          <AlertCircle className="w-4 h-4 text-yellow-400 shrink-0 mt-0.5" />
          <div className="flex-1 min-w-0">
            <p className="text-[10.5px] text-yellow-300 font-medium leading-snug">
              Sena is taking longer than expected to initialise.
            </p>
            <p className="text-[10px] text-yellow-500 mt-0.5 leading-snug">
              Check the output panel for details (e.g. Ollama not running or
              model not installed). You can continue to the dashboard and fix
              settings there.
            </p>
          </div>
          <button
            onClick={finalizeReady}
            className="shrink-0 px-2.5 py-1 rounded bg-yellow-500/20 border border-yellow-500/40 text-yellow-300 text-[10.5px] font-medium hover:bg-yellow-500/30 transition"
          >
            Continue anyway
          </button>
        </div>
      )}

      {/* Progress bar + status */}
      <div className="relative shrink-0 space-y-2">
        <div className="h-1 rounded-full bg-white/8 overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-500 ${
              hasFatalError
                ? "bg-red-500"
                : "bg-gradient-to-r from-emerald-400 via-cyan-400 to-blue-400"
            }`}
            style={{ width: `${progressPercent}%` }}
          />
        </div>
        <div className="flex items-center justify-between">
          <p className="text-[10.5px] text-slate-400">
            {hasFatalError ? (
              <span className="text-red-400">
                Startup failed — check the output above for details
              </span>
            ) : awaitingSetup ? (
              "Complete setup in the configuration window to continue."
            ) : showContinueAnyway ? (
              <span className="text-yellow-400">
                Health check failing — see output panel or click Continue
                anyway.
              </span>
            ) : isChecking ? (
              "Sena will open automatically once all services are healthy."
            ) : (
              <span className="text-emerald-400">
                All services ready — opening Sena...
              </span>
            )}
          </p>
          <span className="text-[10px] text-slate-600">
            {Math.min(progress, totalSteps)}/{totalSteps}
          </span>
        </div>
      </div>
    </div>
  );
}
