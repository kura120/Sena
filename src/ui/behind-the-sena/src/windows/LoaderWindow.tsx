import React, { useEffect, useRef, useState } from "react";
import { CheckCircle2, Circle, Loader2 } from "lucide-react";
import { buildApiUrl, fetchJson, getApiBaseUrl } from "../utils/api";

interface BootStep {
  id: string;
  label: string;
  status: "pending" | "loading" | "completed";
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

export function LoaderWindow() {
  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [isChecking, setIsChecking] = useState(true);
  const [serverLines, setServerLines] = useState<string[]>([]);
  const [awaitingSetup, setAwaitingSetup] = useState(false);
  const outputRef = useRef<HTMLDivElement>(null);
  const autoAdvanceRef = useRef<NodeJS.Timeout | null>(null);
  const healthCheckRef = useRef<NodeJS.Timeout | null>(null);
  const settingsReadyRef = useRef(false);
  const setupWindowOpenRef = useRef(false);
  const hasSignaledRef = useRef(false);
  const totalSteps = 4;
  const progress = Math.min(currentStepIndex, totalSteps);
  const progressPercent = Math.min((progress / totalSteps) * 100, 100);
  const statusLabel = awaitingSetup
    ? "Setup required"
    : isChecking
      ? "Starting"
      : "Ready";

  const bootSteps: BootStep[] = [
    {
      id: "core",
      label: "Initializing Core",
      status: currentStepIndex > 0 ? "completed" : "loading",
    },
    {
      id: "config",
      label: "Loading Config",
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

  const isSettingsComplete = (data: LlmSettingsResponse): boolean => {
    return (
      isPopulated(data.data?.provider) &&
      isPopulated(data.data?.models?.fast) &&
      isPopulated(data.data?.models?.critical) &&
      isPopulated(data.data?.models?.code)
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

  /**
   * Check whether LLM settings are complete.
   * If not, open the dedicated setup window (once) and return false.
   * If complete, mark settings as ready and return true.
   */
  const ensureSettingsGate = async (): Promise<boolean> => {
    if (settingsReadyRef.current) return true;

    try {
      const data = await fetchJson<LlmSettingsResponse>("/api/v1/settings/llm");

      if (isSettingsComplete(data)) {
        settingsReadyRef.current = true;
        setAwaitingSetup(false);
        return true;
      }

      // Settings are incomplete — open the setup window if not already open
      if (!setupWindowOpenRef.current) {
        setupWindowOpenRef.current = true;
        setAwaitingSetup(true);
        void window.sena.openSetupWindow?.();
      }
      return false;
    } catch {
      // Server may not be ready yet — don't open setup window on network errors
      return false;
    }
  };

  useEffect(() => {
    let mounted = true;

    window.sena.onStartupStep((data) => {
      if (!mounted) return;
      const stepMessage = data.step.toLowerCase();
      if (stepMessage.includes("config")) setCurrentStepIndex(1);
      else if (stepMessage.includes("llm") || stepMessage.includes("service"))
        setCurrentStepIndex(2);
      else if (stepMessage.includes("memory")) setCurrentStepIndex(3);
      else if (stepMessage.includes("ready")) setCurrentStepIndex(4);
    });

    window.sena.onStartupError((data) => {
      if (!mounted) return;
      setError(data.error);
      setIsChecking(false);
    });

    const sanitizeLogLine = (value: string) =>
      value
        .replace(/\x1b\[[0-9;]*m/g, "")
        .replace(/[^\x09\x0A\x0D\x20-\x7E]/g, "")
        .trim();

    window.sena.onServerLog((message) => {
      if (!mounted) return;
      const nextLines = message
        .split(/\r?\n/)
        .map((line) => sanitizeLogLine(line))
        .filter((line) => line.length > 0);
      if (nextLines.length === 0) return;
      setServerLines((prev) => {
        const merged = [...prev, ...nextLines];
        return merged.slice(-10);
      });
    });

    autoAdvanceRef.current = setInterval(() => {
      if (!mounted) return;
      setCurrentStepIndex((prev) => {
        if (prev < 3) return prev + 1;
        return prev;
      });
    }, 1000);

    const checkHealth = async () => {
      try {
        const settingsReady = await ensureSettingsGate();
        if (!settingsReady) {
          return;
        }

        // Once settings are ready, also wait for the health endpoint
        const baseUrl = await getApiBaseUrl();
        const response = await fetch(buildApiUrl(baseUrl, "/health"), {
          signal: AbortSignal.timeout(2000),
        });
        if (!mounted) return;

        if (response.ok) {
          finalizeReady();
          return;
        }

        if (response.status === 503) {
          const data = await response.json().catch(() => null);
          const mem0Connected = data?.components?.memory?.mem0_connected;
          if (mem0Connected === false) {
            setError(
              "mem0 is unavailable. Start mem0 or switch memory provider.",
            );
          }
        }
      } catch {
        // Server not ready yet, keep checking
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
  }, [serverLines]);

  return (
    <div className="w-full h-full flex items-center justify-center bg-transparent">
      <div className="relative w-[520px] rounded-[28px] border border-white/10 bg-gradient-to-br from-[#08163b] via-[#050e24] to-[#020712] p-6 shadow-[0_25px_70px_rgba(2,6,19,0.75)] overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-b from-white/10 via-transparent to-transparent opacity-20 pointer-events-none" />
        <div className="absolute right-6 top-6 w-20 h-20 bg-emerald-400/10 blur-3xl rounded-full opacity-40" />
        <div className="relative space-y-5">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-3">
              <img
                src="/assets/sena-logo.png"
                alt="Sena"
                className="w-10 h-10 object-contain"
              />
              <div>
                <p className="text-base text-white font-medium tracking-tight">
                  Sena
                </p>
                <p className="text-[11px] text-slate-400 tracking-[0.2em] uppercase">
                  Boot sequence
                </p>
              </div>
            </div>
            <span className="px-2 py-1 text-[11px] rounded-full bg-white/5 text-slate-200/90">
              {statusLabel}
            </span>
          </div>

          <div className="flex gap-4">
            <div className="space-y-3 flex-1">
              {bootSteps.map((step, index) => (
                <div key={step.id} className="relative pl-8">
                  {index < bootSteps.length - 1 && (
                    <span className="absolute left-[14px] top-6 bottom-[-8px] w-px bg-white/15" />
                  )}
                  <div className="flex items-center gap-3">
                    <div className="w-5 h-5 rounded-full bg-white/5 flex items-center justify-center">
                      {step.status === "completed" ? (
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                      ) : step.status === "loading" ? (
                        <Loader2 className="w-3.5 h-3.5 text-blue-300 animate-spin" />
                      ) : (
                        <Circle className="w-3.5 h-3.5 text-slate-600" />
                      )}
                    </div>
                    <div className="flex flex-col gap-0.5">
                      <span
                        className={`text-sm font-medium ${step.status === "pending" ? "text-slate-400" : "text-slate-50"}`}
                      >
                        {step.label}
                      </span>
                      <span className="text-[11px] text-slate-500">
                        {step.status === "completed"
                          ? "Ready"
                          : step.status === "loading"
                            ? "In progress"
                            : "Waiting"}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            <div className="space-y-2 w-[260px]">
              <div className="text-[11px] text-slate-400 uppercase tracking-[0.2em]">
                Server output
              </div>
              <div
                ref={outputRef}
                className="rounded-md bg-slate-950/80 border border-slate-800/80 px-3 py-2 text-[11px] text-slate-200 font-mono h-[190px] overflow-y-auto"
              >
                {serverLines.length === 0 ? (
                  <div className="text-slate-500">
                    Waiting for server logs...
                  </div>
                ) : (
                  serverLines.map((line, index) => (
                    <div
                      key={`${line}-${index}`}
                      className="whitespace-pre-wrap break-words"
                    >
                      {line}
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>

          <div className="space-y-3">
            <div className="h-1.5 rounded-full bg-white/8">
              <div
                className="h-full rounded-full bg-gradient-to-r from-emerald-400 via-cyan-400 to-blue-400 transition-all duration-500"
                style={{ width: `${progressPercent}%` }}
              />
            </div>
            <div className="flex items-center justify-between text-[11px] text-slate-400">
              <span>Progress</span>
              <span>
                {Math.min(progress, totalSteps)}/{totalSteps}
              </span>
            </div>
            <p className="text-[11px] text-slate-400">
              {error ? (
                <span className="text-red-300">{error}</span>
              ) : awaitingSetup ? (
                "Complete setup in the configuration window to continue."
              ) : (
                "Sena will open automatically once services report healthy."
              )}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
