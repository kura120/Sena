import React, { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import { RefreshCw, Filter, ChevronRight, ChevronDown } from "lucide-react";
import { fetchJson } from "../utils/api";
import { TabLayout } from "../components/TabLayout";

const LEVEL_OPTIONS = [
  { value: "all", label: "All Levels" },
  { value: "debug", label: "Debug" },
  { value: "info", label: "Info" },
  { value: "warning", label: "Warning" },
  { value: "error", label: "Error" },
];

type LogMetadata = Record<string, unknown>;

interface LogEntry {
  id: string;
  timestamp: string;
  level: "debug" | "info" | "warning" | "error";
  source: string;
  message: string;
  event?: string | null;
  metadata?: LogMetadata | null;
  kind?: "chat";
  children?: LogEntry[];
}

export const Logs: React.FC = () => {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<string>("all");
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [copyState, setCopyState] = useState<"idle" | "copied" | "error">(
    "idle",
  );
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());

  const userSelectedRef = useRef(false);
  const selectedSnapshotRef = useRef<LogEntry | null>(null);

  useEffect(() => {
    void fetchLogs();

    if (autoRefresh) {
      const interval = setInterval(() => void fetchLogs(), 3000);
      return () => clearInterval(interval);
    }
  }, [filter, autoRefresh]);

  const normalizePayload = (value: string) => {
    return value
      .replace(/\bNone\b/g, "null")
      .replace(/\bTrue\b/g, "true")
      .replace(/\bFalse\b/g, "false")
      .replace(
        /'([^']*)'/g,
        (_match, group) => `"${group.replace(/"/g, '\\"')}"`,
      );
  };

  const parseRequestPayload = (
    value: string,
  ): Record<string, unknown> | null => {
    const normalized = normalizePayload(value);
    try {
      const parsed = JSON.parse(normalized);
      return parsed && typeof parsed === "object" ? parsed : null;
    } catch {
      return null;
    }
  };

  const extractSessionId = (entry: LogEntry) => {
    if (entry.metadata && typeof entry.metadata.session_id === "string") {
      return entry.metadata.session_id as string;
    }
    const sessionMatch = entry.message.match(/session=([^,\s]+)/);
    if (sessionMatch) return sessionMatch[1];
    if (entry.metadata && typeof entry.metadata.request_payload === "object") {
      const payload = entry.metadata.request_payload as Record<string, unknown>;
      if (typeof payload.session_id === "string") return payload.session_id;
    }
    return null;
  };

  const levelRank = { debug: 0, info: 1, warning: 2, error: 3 };
  const maxLevel = (a: LogEntry["level"], b: LogEntry["level"]) =>
    levelRank[a] >= levelRank[b] ? a : b;

  const buildChatSummary = (metadata: LogMetadata | null) => {
    const payload = metadata?.request_payload;
    if (
      payload &&
      typeof payload === "object" &&
      typeof (payload as any).message === "string"
    ) {
      return `Chat: ${truncate((payload as any).message as string, 120)}`;
    }
    const sessionId = metadata?.session_id;
    if (typeof sessionId === "string") {
      return `Chat session ${sessionId}`;
    }
    return "Chat request";
  };

  const groupChatLogs = (entries: LogEntry[]) => {
    const sorted = [...entries].sort((a, b) =>
      a.timestamp.localeCompare(b.timestamp),
    );
    const grouped: LogEntry[] = [];
    let current: {
      start: LogEntry;
      entries: LogEntry[];
      metadata: LogMetadata;
      level: LogEntry["level"];
      sessionId: string | null;
    } | null = null;

    const finalize = () => {
      if (!current) return;
      const summary = buildChatSummary(current.metadata);
      grouped.push({
        id: `chat-${current.sessionId || current.start.timestamp}`,
        timestamp: current.start.timestamp,
        level: current.level,
        source: "chat",
        message: summary,
        event: "chat",
        metadata: current.metadata,
        kind: "chat",
        children: current.entries,
      });
      current = null;
    };

    for (const entry of sorted) {
      const isChat = entry.source.includes("src.api.routes.chat");
      if (!isChat) {
        finalize();
        grouped.push(entry);
        continue;
      }

      const isStart = entry.message.includes("=== CHAT REQUEST START ===");
      const isEnd =
        entry.message.includes("=== CHAT REQUEST COMPLETE ===") ||
        entry.message.includes("=== CHAT REQUEST FAILED ===");

      if (isStart) {
        finalize();
        current = {
          start: entry,
          entries: [entry],
          metadata: {},
          level: entry.level,
          sessionId: null,
        };
      } else if (!current) {
        current = {
          start: entry,
          entries: [entry],
          metadata: {},
          level: entry.level,
          sessionId: null,
        };
      } else {
        current.entries.push(entry);
      }

      if (current) {
        current.level = maxLevel(current.level, entry.level);
        if (entry.metadata) {
          current.metadata = { ...current.metadata, ...entry.metadata };
        }
        if (entry.message.startsWith("Request payload:")) {
          const rawPayload = entry.message
            .replace("Request payload:", "")
            .trim();
          const parsedPayload = parseRequestPayload(rawPayload);
          current.metadata.request_payload = parsedPayload || rawPayload;
        }
        const sessionId = extractSessionId({
          ...entry,
          metadata: current.metadata,
        });
        if (sessionId) {
          current.sessionId = sessionId;
          current.metadata.session_id = sessionId;
        }
      }

      if (isEnd) {
        finalize();
      }
    }

    finalize();
    return grouped.sort((a, b) => b.timestamp.localeCompare(a.timestamp));
  };

  async function fetchLogs() {
    try {
      const data = await fetchJson<any>("/api/v1/logs", {
        query: filter !== "all" ? { level: filter } : undefined,
      });

      const rawList = (data.data || data.logs || []).map((log: any) => ({
        id: log.raw || `${log.timestamp}-${log.message}-${log.source}`,
        timestamp: log.timestamp || new Date().toLocaleTimeString(),
        level: (log.level || "info").toLowerCase(),
        source: log.source || "system",
        message: log.message,
        event: log.event || null,
        metadata: log.metadata || null,
      }));

      const logList = groupChatLogs(rawList);
      setLogs(logList);

      const selectedStillExists = selectedId
        ? logList.some(
            (entry) =>
              entry.id === selectedId ||
              entry.children?.some((c) => c.id === selectedId),
          )
        : false;

      if (
        !selectedStillExists &&
        !userSelectedRef.current &&
        logList.length > 0
      ) {
        setSelectedId(logList[0].id);
      }
    } catch (e) {
      console.error("Failed to fetch logs:", e);
    } finally {
      setLoading(false);
    }
  }

  // Search top-level entries first, then children of grouped entries
  const selectedLog =
    logs.find((log) => log.id === selectedId) ||
    logs
      .flatMap((log) => log.children ?? [])
      .find((c) => c.id === selectedId) ||
    selectedSnapshotRef.current;

  const levelDot = {
    debug: "bg-slate-500",
    info: "bg-blue-500",
    warning: "bg-orange-500",
    error: "bg-red-500",
  };

  const levelBadge = {
    debug: "text-slate-300 bg-slate-500/10 border-slate-500/30",
    info: "text-blue-300 bg-blue-500/10 border-blue-500/30",
    warning: "text-orange-300 bg-orange-500/10 border-orange-500/30",
    error: "text-red-300 bg-red-500/10 border-red-500/30",
  };

  const truncate = (value: string, limit = 140) => {
    if (!value) return "";
    return value.length > limit ? `${value.slice(0, limit)}...` : value;
  };

  const tryParseJson = (value: string) => {
    try {
      const parsed = JSON.parse(value);
      if (parsed && typeof parsed === "object") {
        return JSON.stringify(parsed, null, 2);
      }
    } catch {
      return null;
    }
    return null;
  };

  const getMessageText = (value: string) => tryParseJson(value) || value;
  const isJsonMessage = (value: string) => Boolean(tryParseJson(value));

  const getDetailMessage = (entry: LogEntry) => {
    if (
      entry.kind === "chat" &&
      entry.metadata?.request_payload &&
      typeof entry.metadata.request_payload === "object"
    ) {
      const payload = entry.metadata.request_payload as Record<string, unknown>;
      if (typeof payload.message === "string") {
        return payload.message;
      }
    }
    return entry.message;
  };

  const handleCopy = async () => {
    if (!selectedLog) return;
    const detailMessage = getMessageText(getDetailMessage(selectedLog));
    const trace = [
      selectedLog.timestamp,
      selectedLog.level,
      selectedLog.source,
      "Message",
      detailMessage,
    ].join("\n");
    try {
      await navigator.clipboard.writeText(trace);
      setCopyState("copied");
      setTimeout(() => setCopyState("idle"), 1500);
    } catch {
      setCopyState("error");
      setTimeout(() => setCopyState("idle"), 2000);
    }
  };

  const toggleExpand = (id: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const selectEntry = (entry: LogEntry) => {
    userSelectedRef.current = true;
    setSelectedId(entry.id);
    selectedSnapshotRef.current = entry;
  };

  return (
    <TabLayout>
      {/* Header */}
      <div className="px-4 pt-4 pb-3">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold text-slate-50">Logs</h2>
            <p className="text-xs text-slate-400 mt-0.5">
              {logs.length} {logs.length === 1 ? "entry" : "entries"}
            </p>
          </div>

          <div className="flex items-center gap-2">
            {/* Auto-refresh toggle */}
            <button
              onClick={() => setAutoRefresh(!autoRefresh)}
              className={`px-2 py-1 rounded text-xs font-medium transition ${
                autoRefresh
                  ? "bg-purple-500/20 text-purple-400 border border-purple-500/50"
                  : "bg-slate-800 text-slate-400 border border-slate-700"
              }`}
            >
              Auto {autoRefresh ? "ON" : "OFF"}
            </button>

            {/* Filter dropdown */}
            <div className="relative">
              <Filter className="absolute left-2 top-1/2 transform -translate-y-1/2 w-3 h-3 text-slate-400" />
              <select
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
                className="pl-7 pr-3 py-1 bg-slate-800 border border-slate-700 text-slate-300 rounded text-xs hover:bg-slate-700 transition appearance-none cursor-pointer"
              >
                {LEVEL_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Manual refresh */}
            <button
              onClick={fetchLogs}
              disabled={loading}
              className="p-1 bg-slate-800 border border-slate-700 text-slate-300 rounded hover:bg-slate-700 transition disabled:opacity-50"
            >
              <RefreshCw
                className={`w-4 h-4 ${loading ? "animate-spin" : ""}`}
              />
            </button>
          </div>
        </div>
      </div>

      {/* Scrollable logs container */}
      <div className="flex-1 min-h-0 px-4 pb-4">
        <div className="h-full grid grid-cols-1 lg:grid-cols-[1.1fr_1fr] gap-4">
          {/* ── Left panel: log list ── */}
          <div className="bg-slate-900 rounded-lg border border-slate-800 overflow-hidden flex flex-col">
            <div className="px-3 py-2 text-[11px] text-slate-400 border-b border-slate-800/70">
              Showing latest {logs.length} entries
            </div>
            <div className="flex-1 min-h-0 overflow-y-auto">
              {logs.length === 0 ? (
                <div className="flex items-center justify-center h-32 text-slate-500 text-sm">
                  No logs to display
                </div>
              ) : (
                <div className="divide-y divide-slate-800/70">
                  {logs.map((msg) => {
                    const isGrouped = (msg.children?.length ?? 0) > 0;
                    const isExpanded = expandedIds.has(msg.id);
                    const isSelected = msg.id === selectedId;

                    return (
                      <React.Fragment key={msg.id}>
                        {/* ── Parent / single row ── */}
                        <div
                          className={`transition-colors ${
                            isSelected && !isGrouped ? "bg-slate-800/70" : ""
                          }`}
                        >
                          <div className="flex items-stretch">
                            {/* Expand chevron — only for grouped entries */}
                            {isGrouped ? (
                              <button
                                onClick={() => toggleExpand(msg.id)}
                                className="flex items-center justify-center w-7 flex-shrink-0 text-slate-500 hover:text-slate-200 transition-colors"
                                title={isExpanded ? "Collapse" : "Expand"}
                              >
                                {isExpanded ? (
                                  <ChevronDown className="w-3.5 h-3.5" />
                                ) : (
                                  <ChevronRight className="w-3.5 h-3.5" />
                                )}
                              </button>
                            ) : (
                              /* Spacer to keep alignment consistent */
                              <span className="w-7 flex-shrink-0" />
                            )}

                            {/* Row content — click to select */}
                            <button
                              onClick={() => selectEntry(msg)}
                              className={`flex-1 min-w-0 text-left py-2 pr-3 transition-colors ${
                                isSelected
                                  ? "bg-slate-800/70"
                                  : "hover:bg-slate-800/40"
                              }`}
                            >
                              <div className="flex items-center gap-2 flex-wrap">
                                <span
                                  className={`w-2 h-2 rounded-full flex-shrink-0 ${levelDot[msg.level]}`}
                                />
                                <span className="text-[11px] text-slate-400 font-mono flex-shrink-0">
                                  {msg.timestamp}
                                </span>
                                <span
                                  className={`text-[10px] uppercase tracking-widest px-1.5 py-0.5 rounded border flex-shrink-0 ${
                                    levelBadge[msg.level]
                                  }`}
                                >
                                  {msg.level}
                                </span>
                                {msg.event && (
                                  <span className="text-[10px] uppercase tracking-widest text-purple-300/80 flex-shrink-0">
                                    {msg.event}
                                  </span>
                                )}
                                <span className="text-[11px] text-slate-500 truncate">
                                  {msg.source}
                                </span>
                                {/* Child count badge */}
                                {isGrouped && (
                                  <span className="ml-auto text-[10px] font-mono text-slate-500 bg-slate-800 border border-slate-700 px-1.5 py-0.5 rounded flex-shrink-0">
                                    {msg.children!.length}
                                  </span>
                                )}
                              </div>
                              <div className="mt-1 text-xs text-slate-200 font-mono break-words">
                                {truncate(msg.message)}
                              </div>
                            </button>
                          </div>
                        </div>

                        {/* ── Children (rendered inline when expanded) ── */}
                        {isGrouped && isExpanded && (
                          <div className="border-l-2 border-slate-700/60 ml-7">
                            {msg.children!.map((child, idx) => {
                              const childIsSelected = child.id === selectedId;
                              const isLast = idx === msg.children!.length - 1;
                              return (
                                <button
                                  key={child.id}
                                  onClick={() => selectEntry(child)}
                                  className={`w-full text-left py-1.5 pr-3 pl-3 transition-colors ${
                                    childIsSelected
                                      ? "bg-slate-800/60 border-l-2 border-purple-500/60 -ml-0.5"
                                      : "hover:bg-slate-800/30"
                                  } ${!isLast ? "border-b border-slate-800/40" : ""}`}
                                >
                                  <div className="flex items-center gap-2 flex-wrap">
                                    <span
                                      className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${levelDot[child.level]}`}
                                    />
                                    <span className="text-[10px] text-slate-500 font-mono flex-shrink-0">
                                      {child.timestamp}
                                    </span>
                                    <span
                                      className={`text-[10px] uppercase tracking-widest px-1 py-0.5 rounded border flex-shrink-0 ${
                                        levelBadge[child.level]
                                      }`}
                                    >
                                      {child.level}
                                    </span>
                                    {child.event && (
                                      <span className="text-[10px] uppercase tracking-widest text-purple-300/70 flex-shrink-0">
                                        {child.event}
                                      </span>
                                    )}
                                    <span className="text-[10px] text-slate-600 truncate">
                                      {child.source}
                                    </span>
                                  </div>
                                  <div className="mt-0.5 text-[11px] text-slate-300 font-mono break-words">
                                    {truncate(child.message, 120)}
                                  </div>
                                </button>
                              );
                            })}
                          </div>
                        )}
                      </React.Fragment>
                    );
                  })}
                </div>
              )}
            </div>
          </div>

          {/* ── Right panel: log details ── */}
          <div className="bg-slate-900 rounded-lg border border-slate-800 overflow-hidden flex flex-col">
            <div className="px-3 py-2 text-[11px] text-slate-400 border-b border-slate-800/70">
              Log details
            </div>
            <div className="flex-1 min-h-0 overflow-y-auto px-4 py-3 space-y-4">
              {!selectedLog ? (
                <div className="text-sm text-slate-500">
                  Select a log entry to view details.
                </div>
              ) : (
                <>
                  <div className="flex items-center gap-2 flex-wrap">
                    <span
                      className={`w-2 h-2 rounded-full ${levelDot[selectedLog.level]}`}
                    />
                    <span className="text-xs text-slate-400 font-mono">
                      {selectedLog.timestamp}
                    </span>
                    <span
                      className={`text-[10px] uppercase tracking-widest px-1.5 py-0.5 rounded border ${
                        levelBadge[selectedLog.level]
                      }`}
                    >
                      {selectedLog.level}
                    </span>
                    {selectedLog.event && (
                      <span className="text-[10px] uppercase tracking-widest text-purple-300/80">
                        {selectedLog.event}
                      </span>
                    )}
                    <span className="text-xs text-slate-500">
                      {selectedLog.source}
                    </span>
                    {/* If this is a grouped parent, show child count */}
                    {selectedLog.kind === "chat" &&
                      selectedLog.children &&
                      selectedLog.children.length > 0 && (
                        <span className="ml-auto text-[10px] font-mono text-slate-500 bg-slate-800 border border-slate-700 px-1.5 py-0.5 rounded">
                          {selectedLog.children.length} sub-entries
                        </span>
                      )}
                  </div>

                  <div>
                    <div className="flex items-center justify-between">
                      <p className="text-xs text-slate-400 uppercase tracking-widest">
                        Message
                      </p>
                      <div className="flex items-center gap-2">
                        {isJsonMessage(getDetailMessage(selectedLog)) && (
                          <span className="text-[10px] uppercase tracking-widest text-emerald-300/80">
                            json
                          </span>
                        )}
                        <button
                          onClick={handleCopy}
                          className="px-2 py-1 text-[10px] rounded border border-slate-700 text-slate-300 hover:text-slate-50 hover:border-slate-500 transition"
                        >
                          {copyState === "copied"
                            ? "Copied"
                            : copyState === "error"
                              ? "Failed"
                              : "Copy"}
                        </button>
                      </div>
                    </div>
                    <div className="mt-2 rounded-md bg-slate-950/80 border border-slate-800/80 px-3 py-2">
                      {isJsonMessage(getDetailMessage(selectedLog)) ? (
                        <pre className="text-xs text-slate-100 font-mono whitespace-pre-wrap break-words">
                          {getMessageText(getDetailMessage(selectedLog))}
                        </pre>
                      ) : (
                        <div className="prose prose-invert max-w-none text-slate-100 text-sm">
                          <ReactMarkdown>
                            {getDetailMessage(selectedLog)}
                          </ReactMarkdown>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Chat timeline — shown when the grouped parent is selected */}
                  {selectedLog.kind === "chat" && selectedLog.children && (
                    <div>
                      <p className="text-xs text-slate-400 uppercase tracking-widest mb-2">
                        Timeline
                      </p>
                      <div className="rounded-md bg-slate-950/70 border border-slate-800/70 overflow-hidden">
                        {selectedLog.children.map((entry, idx) => (
                          <div
                            key={entry.id}
                            className={`flex items-start gap-3 px-3 py-2 text-[11px] ${
                              idx !== selectedLog.children!.length - 1
                                ? "border-b border-slate-800/50"
                                : ""
                            }`}
                          >
                            <span
                              className={`mt-0.5 w-1.5 h-1.5 rounded-full flex-shrink-0 ${levelDot[entry.level]}`}
                            />
                            <span className="text-slate-500 font-mono flex-shrink-0">
                              {entry.timestamp}
                            </span>
                            <span
                              className={`text-[10px] uppercase tracking-widest px-1 py-0.5 rounded border flex-shrink-0 ${levelBadge[entry.level]}`}
                            >
                              {entry.level}
                            </span>
                            <span className="text-slate-200 font-mono break-words min-w-0">
                              {entry.message}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {selectedLog.metadata &&
                    Object.keys(selectedLog.metadata).length > 0 && (
                      <div>
                        <p className="text-xs text-slate-400 uppercase tracking-widest">
                          Metadata
                        </p>
                        <div className="mt-2 rounded-md bg-slate-950/70 border border-slate-800/70 px-3 py-2 text-[11px] text-slate-200">
                          <div className="grid grid-cols-2 gap-x-4 gap-y-1">
                            {Object.entries(selectedLog.metadata)
                              .filter(([key]) => key !== "request_payload")
                              .map(([key, value]) => (
                                <div
                                  key={key}
                                  className="flex items-center justify-between gap-2"
                                >
                                  <span className="text-slate-500">{key}</span>
                                  <span className="font-mono text-slate-100">
                                    {value === null
                                      ? "n/a"
                                      : typeof value === "object"
                                        ? JSON.stringify(value)
                                        : String(value)}
                                  </span>
                                </div>
                              ))}
                          </div>
                        </div>
                      </div>
                    )}

                  {selectedLog.metadata?.request_payload && (
                    <div>
                      <p className="text-xs text-slate-400 uppercase tracking-widest">
                        Request payload
                      </p>
                      <div className="mt-2 rounded-md bg-slate-950/80 border border-slate-800/80 px-3 py-2">
                        <pre className="text-xs text-slate-100 font-mono whitespace-pre-wrap break-words">
                          {typeof selectedLog.metadata.request_payload ===
                          "string"
                            ? selectedLog.metadata.request_payload
                            : JSON.stringify(
                                selectedLog.metadata.request_payload,
                                null,
                                2,
                              )}
                        </pre>
                      </div>
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        </div>
      </div>
    </TabLayout>
  );
};
