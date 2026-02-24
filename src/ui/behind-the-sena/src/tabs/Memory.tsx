import React, { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Brain, TrendingUp, Calendar, Clock, Database } from "lucide-react";
import { MemoryCard } from "../components/MemoryCard";
import { TabLayout } from "../components/TabLayout";
import { SearchInput } from "../components/SearchInput";
import { StatCard } from "../components/StatCard";
import { EmptyState } from "../components/EmptyState";
import { LoadingState } from "../components/LoadingState";
import { fetchJson } from "../utils/api";
import {
  closeWebSocket,
  openWebSocket,
  sendSubscription,
  WebSocketMessage,
} from "../utils/websocket";

type MemoryUpdateData = {
  action?: string;
  details?: { status?: string; [key: string]: unknown };
  [key: string]: unknown;
};

type LongTermMemory = {
  id: number | string;
  title: string;
  tag: string;
  relevance: number;
  created_at?: string;
  context?: string;
  origin?: string;
};

type ShortTermMemory = {
  id: string;
  content: string;
  role: string;
  timestamp: string;
  expires_at?: string;
  context?: string;
  origin?: string;
};

type MemoryStats = {
  total_memories: number;
  memories_today: number;
  accuracy: number;
};

type ActiveTab = "long-term" | "short-term";

export const Memory: React.FC = () => {
  const [activeTab, setActiveTab] = useState<ActiveTab>("long-term");
  const [search, setSearch] = useState("");

  const [longTermMemories, setLongTermMemories] = useState<LongTermMemory[]>(
    [],
  );
  const [shortTermMemories, setShortTermMemories] = useState<ShortTermMemory[]>(
    [],
  );
  const [stats, setStats] = useState<MemoryStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [shortTermLoading, setShortTermLoading] = useState(false);

  // ── Data fetchers ───────────────────────────────────────────────────────────

  const fetchLongTermMemories = useCallback(async () => {
    try {
      const data = search
        ? await fetchJson<{ results?: any[]; memories?: any[] }>(
            "/api/v1/memory/search",
            { query: { query: search } },
          )
        : await fetchJson<{ results?: any[]; memories?: any[] }>(
            "/api/v1/memory/recent",
          );

      const results = data.results || data.memories || [];
      const mapped: LongTermMemory[] = results.map((item: any) => ({
        id: item.memory_id ?? item.id,
        title: item.content ?? item.title ?? "Untitled memory",
        tag: item.origin ?? item.metadata?.source ?? item.tag ?? "memory",
        relevance: Math.round((item.relevance ?? 1) * 100),
        created_at: item.created_at,
        context: item.context ?? item.metadata?.context ?? "",
        origin:
          item.origin ?? item.metadata?.origin ?? item.metadata?.source ?? "",
      }));
      setLongTermMemories(mapped);
    } catch (e) {
      console.error("Failed to fetch long-term memories:", e);
    }
  }, [search]);

  const fetchShortTermMemories = useCallback(async () => {
    setShortTermLoading(true);
    try {
      const data = await fetchJson<{ results?: any[] }>(
        "/api/v1/memory/short-term",
      );
      const results = data.results ?? [];
      const mapped: ShortTermMemory[] = results.map((item: any) => ({
        id: item.id ?? String(Math.random()),
        content: item.content ?? "",
        role: item.role ?? "unknown",
        timestamp: item.timestamp ?? "",
        expires_at: item.expires_at,
        context:
          item.context ?? item.metadata?.context ?? "In-session conversation",
        origin: item.origin ?? item.metadata?.origin ?? item.role ?? "unknown",
      }));
      setShortTermMemories(mapped);
    } catch (e) {
      console.error("Failed to fetch short-term memories:", e);
    } finally {
      setShortTermLoading(false);
    }
  }, []);

  const fetchStats = useCallback(async () => {
    try {
      const data = await fetchJson<any>("/api/v1/memory/stats");
      setStats(data.memory ?? data);
    } catch (e) {
      console.error("Failed to fetch stats:", e);
    } finally {
      setLoading(false);
    }
  }, []);

  // ── Delete handler ──────────────────────────────────────────────────────────

  const handleDelete = useCallback(
    async (id: number | string) => {
      try {
        await fetchJson(`/api/v1/memory/${id}`, { method: "DELETE" });
        setLongTermMemories((prev) => prev.filter((m) => m.id !== id));
        void fetchStats();
      } catch (e) {
        console.error("Failed to delete memory:", e);
      }
    },
    [fetchStats],
  );

  // ── Initial load ────────────────────────────────────────────────────────────

  useEffect(() => {
    void fetchLongTermMemories();
    void fetchStats();
  }, []);

  useEffect(() => {
    if (activeTab === "short-term") {
      void fetchShortTermMemories();
    }
  }, [activeTab, fetchShortTermMemories]);

  // ── Debounced search ────────────────────────────────────────────────────────

  useEffect(() => {
    if (search) {
      const debounce = setTimeout(() => void fetchLongTermMemories(), 300);
      return () => clearTimeout(debounce);
    }
    void fetchLongTermMemories();
  }, [search]);

  // ── WebSocket subscription ──────────────────────────────────────────────────

  useEffect(() => {
    let socket: WebSocket | null = null;

    const handleMessage = (payload: WebSocketMessage) => {
      if (payload?.type !== "memory_update") return;
      const data = payload?.data as MemoryUpdateData | undefined;
      const action = data?.action;
      const status = data?.details?.status;
      if (action === "stored" || status === "stored" || action === "added") {
        void fetchLongTermMemories();
        void fetchStats();
        if (activeTab === "short-term") void fetchShortTermMemories();
      }
    };

    const connect = async () => {
      socket = await openWebSocket("/ws", {
        onOpen: () => sendSubscription(socket!, ["memory"]),
        onMessage: handleMessage,
      });
    };

    void connect();
    return () => {
      if (socket) closeWebSocket(socket);
    };
  }, [activeTab]);

  // ── Render helpers ──────────────────────────────────────────────────────────

  const tabButtonClass = (tab: ActiveTab) =>
    `px-4 py-2 text-sm font-medium rounded-lg transition-all duration-150 flex items-center gap-2 ${
      activeTab === tab
        ? "bg-purple-500/20 text-purple-300 border border-purple-500/40"
        : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 border border-transparent"
    }`;

  const roleColor = (role: string) => {
    if (role === "user")
      return "text-cyan-400 bg-cyan-500/10 border-cyan-700/50";
    if (role === "assistant")
      return "text-purple-400 bg-purple-500/10 border-purple-700/50";
    return "text-slate-400 bg-slate-700/30 border-slate-600/50";
  };

  const formatTs = (iso: string) => {
    try {
      return new Date(iso).toLocaleTimeString(undefined, {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      });
    } catch {
      return iso;
    }
  };

  // ── JSX ─────────────────────────────────────────────────────────────────────

  return (
    <TabLayout>
      {/* Stats header */}
      <div className="px-6 pt-6 pb-4 space-y-4">
        {stats && (
          <div className="grid grid-cols-3 gap-3">
            <StatCard
              label="Total Memories"
              value={stats.total_memories}
              icon={Brain}
              color="text-purple-400"
              bg="bg-purple-500/10"
              delay={0.05}
            />
            <StatCard
              label="Today"
              value={stats.memories_today}
              icon={Calendar}
              color="text-blue-400"
              bg="bg-blue-500/10"
              delay={0.1}
            />
            <StatCard
              label="Accuracy"
              value={`${Math.round((stats.accuracy ?? 0) * 100)}%`}
              icon={TrendingUp}
              color="text-emerald-400"
              bg="bg-emerald-500/10"
              delay={0.15}
            />
          </div>
        )}

        {/* Section tabs */}
        <div className="flex items-center gap-2">
          <button
            className={tabButtonClass("long-term")}
            onClick={() => setActiveTab("long-term")}
          >
            <Database className="w-4 h-4" />
            Long-Term
            <span className="ml-1 px-1.5 py-0.5 text-[10px] rounded-full bg-slate-700 text-slate-400">
              {longTermMemories.length}
            </span>
          </button>
          <button
            className={tabButtonClass("short-term")}
            onClick={() => setActiveTab("short-term")}
          >
            <Clock className="w-4 h-4" />
            Short-Term
            <span className="ml-1 px-1.5 py-0.5 text-[10px] rounded-full bg-slate-700 text-slate-400">
              {shortTermMemories.length}
            </span>
          </button>
        </div>

        {/* Search (long-term only) */}
        {activeTab === "long-term" && (
          <SearchInput
            value={search}
            onChange={setSearch}
            placeholder="Search long-term memories…"
          />
        )}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto px-6 pb-6">
        <AnimatePresence mode="wait">
          {/* ── Long-term ── */}
          {activeTab === "long-term" && (
            <motion.div
              key="long-term"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.18 }}
            >
              {loading ? (
                <LoadingState message="Loading long-term memories…" />
              ) : longTermMemories.length === 0 ? (
                <EmptyState
                  icon={Brain}
                  message="No long-term memories found"
                  description={
                    search
                      ? `No memories match "${search}". Try a different search term.`
                      : "Long-term memories are stored permanently. Try telling Sena to remember something."
                  }
                />
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {longTermMemories.map((memory, index) => (
                    <motion.div
                      key={memory.id}
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: index * 0.04 }}
                    >
                      <MemoryCard
                        id={memory.id}
                        title={memory.title}
                        tag={memory.tag}
                        relevance={memory.relevance}
                        context={memory.context}
                        origin={memory.origin}
                        created_at={memory.created_at}
                        onDelete={handleDelete}
                      />
                    </motion.div>
                  ))}
                </div>
              )}
            </motion.div>
          )}

          {/* ── Short-term ── */}
          {activeTab === "short-term" && (
            <motion.div
              key="short-term"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.18 }}
            >
              {shortTermLoading ? (
                <LoadingState message="Loading short-term memory…" />
              ) : shortTermMemories.length === 0 ? (
                <EmptyState
                  icon={Clock}
                  message="No short-term memories"
                  description="Short-term memory holds the current session's conversation context. Start chatting with Sena to populate it."
                />
              ) : (
                <div className="space-y-3">
                  <p className="text-xs text-slate-500 mb-4">
                    These messages are held in-memory for the current session
                    only and will expire automatically.
                  </p>
                  {shortTermMemories.map((item, index) => (
                    <motion.div
                      key={item.id}
                      initial={{ opacity: 0, x: -12 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: index * 0.03 }}
                      className="border border-slate-700/60 rounded-lg bg-slate-800/40 p-4 space-y-2"
                    >
                      {/* Role badge + timestamp */}
                      <div className="flex items-center justify-between gap-2">
                        <span
                          className={`px-2 py-0.5 text-xs font-semibold rounded border capitalize ${roleColor(item.role)}`}
                        >
                          {item.role}
                        </span>
                        <span className="text-[10px] text-slate-500">
                          {formatTs(item.timestamp)}
                        </span>
                      </div>

                      {/* Content */}
                      <p className="text-sm text-slate-200 leading-snug break-words">
                        {item.content}
                      </p>

                      {/* Metadata */}
                      {(item.context || item.origin) && (
                        <div className="pt-1 border-t border-slate-700/40 flex flex-wrap gap-x-4 gap-y-1">
                          {item.origin && (
                            <span className="text-[10px] text-slate-500">
                              <span className="text-slate-600 uppercase tracking-wider">
                                Origin:{" "}
                              </span>
                              {item.origin}
                            </span>
                          )}
                          {item.context && (
                            <span className="text-[10px] text-slate-500">
                              <span className="text-slate-600 uppercase tracking-wider">
                                Context:{" "}
                              </span>
                              {item.context}
                            </span>
                          )}
                          {item.expires_at && (
                            <span className="text-[10px] text-slate-500 ml-auto">
                              <span className="text-slate-600 uppercase tracking-wider">
                                Expires:{" "}
                              </span>
                              {formatTs(item.expires_at)}
                            </span>
                          )}
                        </div>
                      )}
                    </motion.div>
                  ))}
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </TabLayout>
  );
};
