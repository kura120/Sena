import React, { useEffect, useRef, useState, useCallback } from "react";
import { TabLayout } from "../components/TabLayout";
import ReactMarkdown from "react-markdown";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";
import { motion, AnimatePresence } from "framer-motion";
import {
  Send,
  Loader,
  User,
  Bot,
  Plus,
  Trash2,
  Pencil,
  Check,
  X,
  ChevronDown,
  ChevronUp,
  Brain,
  Sparkles,
  PanelLeftClose,
  PanelLeft,
} from "lucide-react";
import { fetchJson } from "../utils/api";
import {
  openWebSocket,
  closeWebSocket,
  sendSubscription,
  WebSocketMessage,
} from "../utils/websocket";

// ─── Types ────────────────────────────────────────────────────────────────────

type ChatMessage = {
  id: string;
  role: "user" | "sena";
  timestamp: string;
  content: string;
  thinkingStages?: ThinkingStage[];
};

type ThinkingStage = {
  stage: string;
  details: string;
  timestamp: string;
};

type ChatSession = {
  id: string;
  title: string;
  messages: ChatMessage[];
  createdAt: string;
};

// ─── Storage keys ─────────────────────────────────────────────────────────────

const SESSIONS_KEY = "sena-chat-sessions";
const ACTIVE_KEY = "sena-chat-active-session";

// ─── Defaults ─────────────────────────────────────────────────────────────────

const makeWelcomeMessage = (): ChatMessage => ({
  id: "welcome",
  role: "sena",
  timestamp: new Date().toLocaleTimeString(),
  content: "Hello! I'm Sena. How can I assist you today?",
});

const makeSession = (index: number): ChatSession => ({
  id: `session-${Date.now()}-${index}`,
  title: `Session ${index}`,
  messages: [makeWelcomeMessage()],
  createdAt: new Date().toISOString(),
});

// ─── Processing stage label map ───────────────────────────────────────────────

const STAGE_LABELS: Record<string, string> = {
  intent_classification: "Classifying intent",
  memory_retrieval: "Retrieving memories",
  extension_check: "Checking extensions",
  extension_execution: "Running extensions",
  llm_processing: "Generating response",
  llm_streaming: "Streaming response",
  post_processing: "Post-processing",
  memory_storage: "Storing to memory",
  complete: "Done",
  error: "Error",
};

// ─── Helpers ─────────────────────────────────────────────────────────────────

function loadSessions(): ChatSession[] {
  try {
    const raw = localStorage.getItem(SESSIONS_KEY);
    if (raw) {
      const parsed = JSON.parse(raw) as ChatSession[];
      if (Array.isArray(parsed) && parsed.length > 0) return parsed;
    }
  } catch {
    // ignore
  }
  return [makeSession(1)];
}

function saveSessions(sessions: ChatSession[], activeId: string) {
  try {
    const trimmed = sessions.map((s) => ({
      ...s,
      messages: s.messages.slice(-200),
    }));
    localStorage.setItem(SESSIONS_KEY, JSON.stringify(trimmed));
    localStorage.setItem(ACTIVE_KEY, activeId);
  } catch {
    // ignore
  }
}

// ─── Sub-components ───────────────────────────────────────────────────────────

type ThinkingPanelProps = {
  stages: ThinkingStage[];
  isLive: boolean;
};

const ThinkingPanel: React.FC<ThinkingPanelProps> = ({ stages, isLive }) => {
  const [open, setOpen] = useState(true);

  // Auto-collapse when thinking is done
  useEffect(() => {
    if (!isLive && stages.length > 0) {
      const t = setTimeout(() => setOpen(false), 1200);
      return () => clearTimeout(t);
    }
  }, [isLive, stages.length]);

  if (stages.length === 0) return null;

  return (
    <div className="mt-2 rounded-lg border border-slate-700/60 bg-slate-900/60 text-xs overflow-hidden">
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center gap-2 px-3 py-2 text-slate-400 hover:text-slate-200 transition-colors"
      >
        <Brain className="w-3.5 h-3.5 text-purple-400 flex-shrink-0" />
        <span className="font-medium">
          {isLive ? "Sena is thinking…" : "Thought process"}
        </span>
        {isLive && (
          <span className="flex gap-0.5 ml-1">
            {[0, 0.15, 0.3].map((delay, i) => (
              <motion.span
                key={i}
                className="w-1 h-1 rounded-full bg-purple-400"
                animate={{ opacity: [0.3, 1, 0.3] }}
                transition={{ repeat: Infinity, duration: 1, delay }}
              />
            ))}
          </span>
        )}
        <span className="ml-auto">
          {open ? (
            <ChevronUp className="w-3.5 h-3.5" />
          ) : (
            <ChevronDown className="w-3.5 h-3.5" />
          )}
        </span>
      </button>

      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="px-3 pb-3 space-y-1.5 border-t border-slate-700/40">
              {stages.map((s, i) => (
                <div key={i} className="flex items-start gap-2 pt-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-purple-400/60 mt-1 flex-shrink-0" />
                  <div className="min-w-0">
                    <span className="text-slate-300 font-medium">
                      {STAGE_LABELS[s.stage] ?? s.stage}
                    </span>
                    {s.details && s.details !== s.stage && (
                      <span className="text-slate-500 ml-1.5">{s.details}</span>
                    )}
                  </div>
                  <span className="ml-auto text-slate-600 flex-shrink-0 text-[10px]">
                    {s.timestamp}
                  </span>
                </div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

// ─── Main component ───────────────────────────────────────────────────────────

export const Chat: React.FC = () => {
  const [sessions, setSessions] = useState<ChatSession[]>(loadSessions);
  const [activeSessionId, setActiveSessionId] = useState<string>(
    () => localStorage.getItem(ACTIVE_KEY) || loadSessions()[0]?.id || "",
  );
  const [sidebarOpen, setSidebarOpen] = useState(true);

  // Input / sending
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  // Thinking stages (live during current request)
  const [liveStages, setLiveStages] = useState<ThinkingStage[]>([]);

  // Rename session
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState("");

  // Edit last message
  const [editingMessageId, setEditingMessageId] = useState<string | null>(null);
  const [editValue, setEditValue] = useState("");

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const renameInputRef = useRef<HTMLInputElement>(null);

  // ── Derived ─────────────────────────────────────────────────────────────────

  const activeSession =
    sessions.find((s) => s.id === activeSessionId) ?? sessions[0];
  const messages = activeSession?.messages ?? [];

  // The last user message (for edit affordance)
  const lastUserMsg = [...messages].reverse().find((m) => m.role === "user");

  // ── Persist on change ────────────────────────────────────────────────────────

  useEffect(() => {
    if (sessions.length > 0) {
      saveSessions(sessions, activeSessionId);
    }
  }, [sessions, activeSessionId]);

  // ── Scroll to bottom ─────────────────────────────────────────────────────────

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, activeSessionId, loading]);

  // ── Keep active session valid ─────────────────────────────────────────────────

  useEffect(() => {
    if (
      !sessions.find((s) => s.id === activeSessionId) &&
      sessions.length > 0
    ) {
      setActiveSessionId(sessions[0].id);
    }
  }, [sessions, activeSessionId]);

  // ── Focus rename input ────────────────────────────────────────────────────────

  useEffect(() => {
    if (renamingId) {
      setTimeout(() => renameInputRef.current?.focus(), 50);
    }
  }, [renamingId]);

  // ── WebSocket for thinking stages ─────────────────────────────────────────────

  useEffect(() => {
    let socket: WebSocket | null = null;

    const handleMessage = (payload: WebSocketMessage) => {
      if (payload.type === "processing_update") {
        const data = payload.data as
          | { stage?: string; details?: string }
          | undefined;
        if (
          data?.stage &&
          data.stage !== "complete" &&
          data.stage !== "error"
        ) {
          setLiveStages((prev) => [
            ...prev,
            {
              stage: data.stage!,
              details: data.details ?? "",
              timestamp: new Date().toLocaleTimeString(undefined, {
                hour: "2-digit",
                minute: "2-digit",
                second: "2-digit",
              }),
            },
          ]);
        }
      }
    };

    const connect = async () => {
      socket = await openWebSocket("/ws", {
        onOpen: () => sendSubscription(socket!, ["processing"]),
        onMessage: handleMessage,
      });
    };

    void connect();
    return () => {
      if (socket) closeWebSocket(socket);
    };
  }, []);

  // ── Session operations ────────────────────────────────────────────────────────

  const createSession = useCallback(() => {
    const newSession = makeSession(sessions.length + 1);
    setSessions((prev) => [...prev, newSession]);
    setActiveSessionId(newSession.id);
    setInput("");
    setEditingMessageId(null);
  }, [sessions.length]);

  const deleteSession = useCallback(
    (id: string, e: React.MouseEvent) => {
      e.stopPropagation();
      setSessions((prev) => {
        const remaining = prev.filter((s) => s.id !== id);
        if (remaining.length === 0) {
          const fresh = makeSession(1);
          setActiveSessionId(fresh.id);
          return [fresh];
        }
        if (activeSessionId === id) {
          setActiveSessionId(remaining[0].id);
        }
        return remaining;
      });
    },
    [activeSessionId],
  );

  const startRename = useCallback(
    (session: ChatSession, e: React.MouseEvent) => {
      e.stopPropagation();
      setRenamingId(session.id);
      setRenameValue(session.title);
    },
    [],
  );

  const commitRename = useCallback(() => {
    if (!renamingId) return;
    const trimmed = renameValue.trim();
    if (trimmed) {
      setSessions((prev) =>
        prev.map((s) => (s.id === renamingId ? { ...s, title: trimmed } : s)),
      );
    }
    setRenamingId(null);
  }, [renamingId, renameValue]);

  const cancelRename = useCallback(() => {
    setRenamingId(null);
    setRenameValue("");
  }, []);

  // ── Auto-title after first real exchange ──────────────────────────────────────

  const tryAutoTitle = useCallback(
    async (sessionId: string, firstUserMessage: string) => {
      try {
        const data = await fetchJson<{ title?: string }>(
          "/api/v1/chat/session/title",
          {
            method: "POST",
            body: { message: firstUserMessage },
          },
        );
        const generatedTitle = data.title?.trim();
        if (generatedTitle) {
          setSessions((prev) =>
            prev.map((s) =>
              s.id === sessionId ? { ...s, title: generatedTitle } : s,
            ),
          );
        }
      } catch {
        // non-critical — silently ignore
      }
    },
    [],
  );

  // ── Send message ──────────────────────────────────────────────────────────────

  const sendMessage = useCallback(
    async (overrideInput?: string) => {
      const text = (overrideInput ?? input).trim();
      if (!text || loading) return;

      const timestamp = new Date().toLocaleTimeString();
      const userMsg: ChatMessage = {
        id: Date.now().toString(),
        role: "user",
        timestamp,
        content: text,
      };

      const isFirstUserMessage =
        messages.filter((m) => m.role === "user").length === 0;

      setSessions((prev) =>
        prev.map((s) =>
          s.id === activeSession.id
            ? { ...s, messages: [...s.messages, userMsg] }
            : s,
        ),
      );
      setInput("");
      setLiveStages([]);
      setLoading(true);

      try {
        const data = await fetchJson<{
          response?: string;
          message?: string;
          content?: string;
        }>("/api/v1/chat", {
          method: "POST",
          body: { message: text, session_id: activeSession.id },
        });

        const capturedStages = [...liveStages]; // snapshot at response time

        const senaMsg: ChatMessage = {
          id: (Date.now() + 1).toString(),
          role: "sena",
          timestamp: new Date().toLocaleTimeString(),
          content:
            data.response ?? data.message ?? data.content ?? "No response",
          thinkingStages: capturedStages,
        };

        setSessions((prev) =>
          prev.map((s) =>
            s.id === activeSession.id
              ? { ...s, messages: [...s.messages, senaMsg] }
              : s,
          ),
        );

        // Auto-title on first real exchange
        if (isFirstUserMessage) {
          void tryAutoTitle(activeSession.id, text);
        }
      } catch (e) {
        const errorMsg: ChatMessage = {
          id: (Date.now() + 1).toString(),
          role: "sena",
          timestamp: new Date().toLocaleTimeString(),
          content: `Error: ${e instanceof Error ? e.message : String(e)}`,
        };
        setSessions((prev) =>
          prev.map((s) =>
            s.id === activeSession.id
              ? { ...s, messages: [...s.messages, errorMsg] }
              : s,
          ),
        );
      } finally {
        setLoading(false);
        setLiveStages([]);
      }
    },
    [input, loading, activeSession, messages, liveStages, tryAutoTitle],
  );

  // ── Edit last message ──────────────────────────────────────────────────────────

  const startEdit = useCallback((msg: ChatMessage) => {
    setEditingMessageId(msg.id);
    setEditValue(msg.content);
  }, []);

  const cancelEdit = useCallback(() => {
    setEditingMessageId(null);
    setEditValue("");
  }, []);

  const commitEdit = useCallback(async () => {
    if (!editingMessageId || !editValue.trim()) return;

    // Remove the edited message and everything after it, then re-send
    setSessions((prev) =>
      prev.map((s) => {
        if (s.id !== activeSession.id) return s;
        const idx = s.messages.findIndex((m) => m.id === editingMessageId);
        if (idx === -1) return s;
        return { ...s, messages: s.messages.slice(0, idx) };
      }),
    );

    setEditingMessageId(null);
    const text = editValue.trim();
    setEditValue("");

    // Small tick to let state settle before sending
    await new Promise((r) => setTimeout(r, 50));
    await sendMessage(text);
  }, [editingMessageId, editValue, activeSession, sendMessage]);

  // ── Delete session (header button) ────────────────────────────────────────────

  const deleteActiveSession = useCallback(() => {
    setSessions((prev) => {
      const remaining = prev.filter((s) => s.id !== activeSession.id);
      if (remaining.length === 0) {
        const fresh = makeSession(1);
        setActiveSessionId(fresh.id);
        return [fresh];
      }
      setActiveSessionId(remaining[0].id);
      return remaining;
    });
  }, [activeSession]);

  // ── Render ────────────────────────────────────────────────────────────────────

  return (
    <TabLayout>
      <div className="flex h-full overflow-hidden">
        {/* ── Sidebar ── */}
        <AnimatePresence initial={false}>
          {sidebarOpen && (
            <motion.aside
              key="sidebar"
              initial={{ width: 0, opacity: 0 }}
              animate={{ width: 220, opacity: 1 }}
              exit={{ width: 0, opacity: 0 }}
              transition={{ duration: 0.22 }}
              className="flex-shrink-0 flex flex-col border-r border-slate-800/60 bg-slate-950/40 overflow-hidden"
              style={{ minWidth: 0 }}
            >
              {/* Sidebar header */}
              <div className="flex items-center justify-between px-3 pt-4 pb-2">
                <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  Sessions
                </span>
                <button
                  onClick={createSession}
                  title="New session"
                  className="p-1 rounded hover:bg-slate-800 text-slate-400 hover:text-white transition"
                >
                  <Plus className="w-3.5 h-3.5" />
                </button>
              </div>

              {/* Session list */}
              <div className="flex-1 overflow-y-auto px-2 pb-4 space-y-1">
                {sessions.map((session) => {
                  const isActive = session.id === activeSessionId;
                  const isRenaming = renamingId === session.id;

                  return (
                    <div
                      key={session.id}
                      onClick={() => {
                        setActiveSessionId(session.id);
                        setEditingMessageId(null);
                      }}
                      className={`group relative rounded-lg px-2.5 py-2 cursor-pointer transition-all ${
                        isActive
                          ? "bg-purple-500/15 border border-purple-500/30"
                          : "hover:bg-slate-800/60 border border-transparent"
                      }`}
                    >
                      {isRenaming ? (
                        <div className="flex items-center gap-1">
                          <input
                            ref={renameInputRef}
                            value={renameValue}
                            onChange={(e) => setRenameValue(e.target.value)}
                            onKeyDown={(e) => {
                              if (e.key === "Enter") commitRename();
                              if (e.key === "Escape") cancelRename();
                            }}
                            onClick={(e) => e.stopPropagation()}
                            className="flex-1 min-w-0 bg-slate-800 text-white text-xs px-1.5 py-0.5 rounded border border-slate-600 focus:outline-none focus:border-purple-500"
                          />
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              commitRename();
                            }}
                            className="p-0.5 text-emerald-400 hover:text-emerald-300"
                          >
                            <Check className="w-3 h-3" />
                          </button>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              cancelRename();
                            }}
                            className="p-0.5 text-slate-500 hover:text-slate-300"
                          >
                            <X className="w-3 h-3" />
                          </button>
                        </div>
                      ) : (
                        <>
                          <p
                            className={`text-xs truncate pr-10 leading-snug ${
                              isActive ? "text-purple-200" : "text-slate-300"
                            }`}
                          >
                            {session.title}
                          </p>
                          <p className="text-[10px] text-slate-600 mt-0.5">
                            {
                              session.messages.filter((m) => m.role === "user")
                                .length
                            }{" "}
                            messages
                          </p>

                          {/* Action buttons (hover or active) */}
                          <div
                            className={`absolute right-1.5 top-1/2 -translate-y-1/2 flex gap-0.5 ${
                              isActive ? "flex" : "hidden group-hover:flex"
                            }`}
                          >
                            <button
                              onClick={(e) => startRename(session, e)}
                              title="Rename"
                              className="p-1 rounded hover:bg-slate-700 text-slate-500 hover:text-slate-300 transition"
                            >
                              <Pencil className="w-2.5 h-2.5" />
                            </button>
                            <button
                              onClick={(e) => deleteSession(session.id, e)}
                              title="Delete session"
                              className="p-1 rounded hover:bg-red-900/40 text-slate-500 hover:text-red-400 transition"
                            >
                              <Trash2 className="w-2.5 h-2.5" />
                            </button>
                          </div>
                        </>
                      )}
                    </div>
                  );
                })}
              </div>
            </motion.aside>
          )}
        </AnimatePresence>

        {/* ── Main chat area ── */}
        <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
          {/* Chat header */}
          <div className="flex items-center gap-3 px-5 py-3 border-b border-slate-800/50 flex-shrink-0">
            <button
              onClick={() => setSidebarOpen((v) => !v)}
              title={sidebarOpen ? "Hide sidebar" : "Show sidebar"}
              className="p-1.5 rounded-lg hover:bg-slate-800 text-slate-500 hover:text-slate-300 transition"
            >
              {sidebarOpen ? (
                <PanelLeftClose className="w-4 h-4" />
              ) : (
                <PanelLeft className="w-4 h-4" />
              )}
            </button>

            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-purple-500 to-cyan-500 flex items-center justify-center flex-shrink-0">
              <Sparkles className="w-4 h-4 text-white" />
            </div>

            <div className="flex-1 min-w-0">
              <h2 className="text-sm font-semibold text-slate-50 truncate">
                {activeSession?.title ?? "Chat"}
              </h2>
              <p className="text-xs text-slate-500">
                {messages.filter((m) => m.role === "user").length} messages
              </p>
            </div>

            <button
              onClick={deleteActiveSession}
              title="Delete this session"
              className="p-1.5 rounded-lg hover:bg-red-900/30 text-slate-600 hover:text-red-400 transition"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto">
            <div className="max-w-3xl mx-auto w-full px-5 py-6 space-y-5">
              <AnimatePresence initial={false}>
                {messages.map((msg) => {
                  const isLastUser =
                    msg.role === "user" && msg.id === lastUserMsg?.id;
                  const isEditing = editingMessageId === msg.id;

                  return (
                    <motion.div
                      key={msg.id}
                      initial={{ opacity: 0, y: 18, scale: 0.96 }}
                      animate={{ opacity: 1, y: 0, scale: 1 }}
                      transition={{
                        duration: 0.35,
                        ease: [0.34, 1.2, 0.64, 1],
                      }}
                      className={`flex gap-3 ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                    >
                      {/* Sena avatar */}
                      {msg.role === "sena" && (
                        <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-purple-500 to-blue-500 flex items-center justify-center flex-shrink-0 shadow-md mt-1">
                          <Bot className="w-4 h-4 text-white" />
                        </div>
                      )}

                      <div
                        className={`flex flex-col max-w-[78%] ${msg.role === "user" ? "items-end" : "items-start"}`}
                      >
                        {/* Editing state */}
                        {isEditing ? (
                          <div className="w-full space-y-2">
                            <textarea
                              value={editValue}
                              onChange={(e) => setEditValue(e.target.value)}
                              onKeyDown={(e) => {
                                if (e.key === "Enter" && !e.shiftKey) {
                                  e.preventDefault();
                                  void commitEdit();
                                }
                                if (e.key === "Escape") cancelEdit();
                              }}
                              rows={3}
                              className="w-full px-3 py-2 bg-slate-800 border border-purple-500/50 rounded-xl text-slate-100 text-sm resize-none focus:outline-none focus:ring-1 focus:ring-purple-500/50"
                            />
                            <div className="flex gap-2 justify-end">
                              <button
                                onClick={cancelEdit}
                                className="px-3 py-1 text-xs rounded-lg bg-slate-800 text-slate-400 hover:text-white border border-slate-700 transition"
                              >
                                Cancel
                              </button>
                              <button
                                onClick={() => void commitEdit()}
                                disabled={!editValue.trim()}
                                className="px-3 py-1 text-xs rounded-lg bg-purple-600 text-white hover:bg-purple-700 transition disabled:opacity-50"
                              >
                                Resend
                              </button>
                            </div>
                          </div>
                        ) : (
                          <>
                            <div
                              className={`group relative px-4 py-2.5 rounded-2xl shadow-md ${
                                msg.role === "user"
                                  ? "bg-gradient-to-br from-purple-600 to-purple-700 text-white rounded-tr-sm"
                                  : "bg-slate-800/80 text-slate-100 border border-slate-700/50 rounded-tl-sm overflow-hidden"
                              }`}
                            >
                              {msg.role === "sena" ? (
                                <div className="chat-markdown text-sm">
                                  <ReactMarkdown
                                    components={{
                                      code({ className, children, ...props }) {
                                        const match = /language-(\w+)/.exec(
                                          className || "",
                                        );
                                        const language = match?.[1];
                                        if (language) {
                                          return (
                                            <div className="chat-code-block">
                                              <SyntaxHighlighter
                                                {...props}
                                                style={vscDarkPlus}
                                                language={language}
                                                PreTag="div"
                                                wrapLongLines
                                                customStyle={{
                                                  background: "transparent",
                                                  margin: 0,
                                                  padding: 0,
                                                  overflowX: "hidden",
                                                }}
                                                codeTagProps={{
                                                  style: {
                                                    whiteSpace: "pre-wrap",
                                                    wordBreak: "break-word",
                                                  },
                                                }}
                                              >
                                                {String(children).replace(
                                                  /\n$/,
                                                  "",
                                                )}
                                              </SyntaxHighlighter>
                                            </div>
                                          );
                                        }
                                        return (
                                          <code
                                            className={className}
                                            {...props}
                                          >
                                            {children}
                                          </code>
                                        );
                                      },
                                    }}
                                  >
                                    {msg.content}
                                  </ReactMarkdown>
                                </div>
                              ) : (
                                <p className="text-sm leading-relaxed whitespace-pre-wrap">
                                  {msg.content}
                                </p>
                              )}

                              {/* Edit button for last user message */}
                              {isLastUser && !loading && (
                                <button
                                  onClick={() => startEdit(msg)}
                                  title="Edit message"
                                  className="absolute -bottom-1 -left-1 p-1 rounded-full bg-slate-700 border border-slate-600 text-slate-400 hover:text-white hover:bg-slate-600 opacity-0 group-hover:opacity-100 transition-all shadow"
                                >
                                  <Pencil className="w-2.5 h-2.5" />
                                </button>
                              )}
                            </div>

                            <span className="text-[10px] text-slate-500 mt-1 px-1">
                              {msg.timestamp}
                            </span>

                            {/* Thinking panel attached to Sena messages */}
                            {msg.role === "sena" &&
                              msg.thinkingStages &&
                              msg.thinkingStages.length > 0 && (
                                <div className="w-full max-w-sm">
                                  <ThinkingPanel
                                    stages={msg.thinkingStages}
                                    isLive={false}
                                  />
                                </div>
                              )}
                          </>
                        )}
                      </div>

                      {/* User avatar */}
                      {msg.role === "user" && (
                        <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center flex-shrink-0 shadow-md mt-1">
                          <User className="w-4 h-4 text-white" />
                        </div>
                      )}
                    </motion.div>
                  );
                })}
              </AnimatePresence>

              {/* Live thinking + loading indicator */}
              {loading && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="flex gap-3 items-start"
                >
                  <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-purple-500 to-blue-500 flex items-center justify-center flex-shrink-0 mt-1">
                    <Bot className="w-4 h-4 text-white" />
                  </div>
                  <div className="flex flex-col gap-2 max-w-[78%]">
                    <div className="px-4 py-2.5 rounded-2xl rounded-tl-sm bg-slate-800/80 border border-slate-700/50">
                      <div className="flex gap-1.5 items-center">
                        {[0, 0.2, 0.4].map((delay, i) => (
                          <motion.div
                            key={i}
                            animate={{ scale: [1, 1.4, 1] }}
                            transition={{
                              repeat: Infinity,
                              duration: 0.9,
                              delay,
                            }}
                            className="w-2 h-2 bg-purple-400 rounded-full"
                          />
                        ))}
                      </div>
                    </div>

                    {/* Live thinking stages */}
                    {liveStages.length > 0 && (
                      <div className="w-full max-w-sm">
                        <ThinkingPanel stages={liveStages} isLive={true} />
                      </div>
                    )}
                  </div>
                </motion.div>
              )}

              <div ref={messagesEndRef} />
            </div>
          </div>

          {/* Input area */}
          <div className="border-t border-slate-800/50 bg-[#0A0E27]/80 flex-shrink-0">
            <div className="max-w-3xl mx-auto w-full flex gap-3 px-5 py-3.5">
              <input
                ref={inputRef}
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    void sendMessage();
                  }
                }}
                placeholder="Type your message…"
                disabled={loading || !!editingMessageId}
                className="flex-1 px-4 py-2.5 bg-slate-900/80 border border-slate-700/50 rounded-xl text-slate-50 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-purple-500/50 focus:border-purple-500/50 transition-all disabled:opacity-50 text-sm"
              />
              <button
                onClick={() => void sendMessage()}
                disabled={loading || !input.trim() || !!editingMessageId}
                className="px-4 py-2.5 bg-gradient-to-br from-purple-600 to-purple-700 text-white rounded-xl hover:from-purple-700 hover:to-purple-800 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 shadow-lg shadow-purple-500/20"
              >
                {loading ? (
                  <Loader className="w-4 h-4 animate-spin" />
                ) : (
                  <Send className="w-4 h-4" />
                )}
              </button>
            </div>
          </div>
        </div>
      </div>
    </TabLayout>
  );
};
