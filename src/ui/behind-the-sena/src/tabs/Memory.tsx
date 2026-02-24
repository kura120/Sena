import React, { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Brain,
  TrendingUp,
  Calendar,
  Clock,
  Database,
  Sparkles,
  RefreshCw,
  Eye,
  PlusCircle,
  X,
} from "lucide-react";
import { MemoryCard } from "../components/MemoryCard";
import {
  PersonalityCard,
  PersonalityFragment,
} from "../components/PersonalityCard";
import { TabLayout } from "../components/TabLayout";
import { SearchInput } from "../components/SearchInput";
import { StatCard } from "../components/StatCard";
import { EmptyState } from "../components/EmptyState";
import { LoadingState } from "../components/LoadingState";
import { fetchJson } from "../utils/api";
import {
  addMessageHandler,
  connectSharedSocket,
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
  /** Short-term buffer usage 0–100 (percent). */
  context_usage: number;
};

type PersonalityStats = {
  total: number;
  by_status: Record<string, number>;
  by_type: Record<string, number>;
  pending_count: number;
};

type ActiveTab = "long-term" | "short-term" | "personality";

export const Memory: React.FC = () => {
  const [activeTab, setActiveTab] = useState<ActiveTab>("long-term");
  const [search, setSearch] = useState("");

  const [longTermMemories, setLongTermMemories] = useState<LongTermMemory[]>(
    [],
  );
  const [shortTermMemories, setShortTermMemories] = useState<ShortTermMemory[]>(
    [],
  );
  // Start with zeros so the StatCards render immediately on mount.
  const [stats, setStats] = useState<MemoryStats>({
    total_memories: 0,
    memories_today: 0,
    context_usage: 0,
  });
  const [loading, setLoading] = useState(true);
  const [shortTermLoading, setShortTermLoading] = useState(false);

  // ── Personality state ───────────────────────────────────────────────────────
  const [personalityFragments, setPersonalityFragments] = useState<
    PersonalityFragment[]
  >([]);
  const [personalityStats, setPersonalityStats] =
    useState<PersonalityStats | null>(null);
  const [personalityLoading, setPersonalityLoading] = useState(false);
  const [personalityFilter, setPersonalityFilter] = useState<
    "all" | "approved" | "pending" | "rejected"
  >("all");
  const [inferring, setInferring] = useState(false);
  const [inferMessage, setInferMessage] = useState<string | null>(null);
  const [previewBlock, setPreviewBlock] = useState<string | null>(null);
  const [showPreview, setShowPreview] = useState(false);
  const [showAddFragment, setShowAddFragment] = useState(false);
  const [newFragmentContent, setNewFragmentContent] = useState("");
  const [newFragmentCategory, setNewFragmentCategory] = useState("preference");
  const [addingFragment, setAddingFragment] = useState(false);

  // ── Data fetchers ───────────────────────────────────────────────────────────

  const fetchPersonalityFragments = useCallback(async () => {
    setPersonalityLoading(true);
    try {
      const params =
        personalityFilter !== "all" ? `?status=${personalityFilter}` : "";
      const data = await fetchJson<{ data?: PersonalityFragment[] }>(
        `/api/v1/personality${params}`,
      );
      setPersonalityFragments(data.data ?? []);
    } catch (e) {
      console.error("Failed to fetch personality fragments:", e);
    } finally {
      setPersonalityLoading(false);
    }
  }, [personalityFilter]);

  const fetchPersonalityStats = useCallback(async () => {
    try {
      const data = await fetchJson<{ data?: PersonalityStats }>(
        "/api/v1/personality/stats",
      );
      setPersonalityStats(data.data ?? null);
    } catch (e) {
      console.error("Failed to fetch personality stats:", e);
    }
  }, []);

  const handleApproveFragment = useCallback(
    async (id: string) => {
      try {
        await fetchJson(`/api/v1/personality/${id}/approve`, {
          method: "POST",
        });
        void fetchPersonalityFragments();
        void fetchPersonalityStats();
      } catch (e) {
        console.error("Failed to approve fragment:", e);
      }
    },
    [fetchPersonalityFragments, fetchPersonalityStats],
  );

  const handleRejectFragment = useCallback(
    async (id: string) => {
      try {
        await fetchJson(`/api/v1/personality/${id}/reject`, { method: "POST" });
        void fetchPersonalityFragments();
        void fetchPersonalityStats();
      } catch (e) {
        console.error("Failed to reject fragment:", e);
      }
    },
    [fetchPersonalityFragments, fetchPersonalityStats],
  );

  const handleDeleteFragment = useCallback(
    async (id: string) => {
      try {
        await fetchJson(`/api/v1/personality/${id}`, { method: "DELETE" });
        setPersonalityFragments((prev) =>
          prev.filter((f) => f.fragment_id !== id),
        );
        void fetchPersonalityStats();
      } catch (e) {
        console.error("Failed to delete fragment:", e);
      }
    },
    [fetchPersonalityStats],
  );

  const handleEditFragment = useCallback(
    async (id: string, newContent: string) => {
      try {
        await fetchJson(`/api/v1/personality/${id}`, {
          method: "PUT",
          body: { content: newContent, approve: true },
        });
        void fetchPersonalityFragments();
        void fetchPersonalityStats();
      } catch (e) {
        console.error("Failed to edit fragment:", e);
      }
    },
    [fetchPersonalityFragments, fetchPersonalityStats],
  );

  const handleTriggerInference = useCallback(async () => {
    setInferring(true);
    setInferMessage(null);
    try {
      const data = await fetchJson<{ message?: string; total?: number }>(
        "/api/v1/personality/infer",
        { method: "POST", body: {} },
      );
      setInferMessage(data.message ?? "Inference complete");
      void fetchPersonalityFragments();
      void fetchPersonalityStats();
    } catch (e) {
      setInferMessage("Inference failed. Check logs.");
      console.error("Failed to trigger inference:", e);
    } finally {
      setInferring(false);
      setTimeout(() => setInferMessage(null), 5000);
    }
  }, [fetchPersonalityFragments, fetchPersonalityStats]);

  const handlePreviewBlock = useCallback(async () => {
    try {
      const data = await fetchJson<{ data?: { block?: string } }>(
        "/api/v1/personality/preview",
      );
      setPreviewBlock(data.data?.block ?? "");
      setShowPreview(true);
    } catch (e) {
      console.error("Failed to fetch personality preview:", e);
    }
  }, []);

  const handleAddExplicitFragment = useCallback(async () => {
    if (!newFragmentContent.trim()) return;
    setAddingFragment(true);
    try {
      await fetchJson("/api/v1/personality", {
        method: "POST",
        body: {
          content: newFragmentContent.trim(),
          category: newFragmentCategory,
          source: "user_input",
        },
      });
      setNewFragmentContent("");
      setShowAddFragment(false);
      void fetchPersonalityFragments();
      void fetchPersonalityStats();
    } catch (e) {
      console.error("Failed to add fragment:", e);
    } finally {
      setAddingFragment(false);
    }
  }, [
    newFragmentContent,
    newFragmentCategory,
    fetchPersonalityFragments,
    fetchPersonalityStats,
  ]);

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

      // Response shape from /api/v1/memory/stats:
      // {
      //   status: "success",
      //   memory: {
      //     long_term:  { total_memories: N, recent: [{id,content,created_at}] },
      //     short_term: { total_items: N, usage_percent: N },
      //     ...
      //   },
      //   retrieval: { ... }
      // }
      const memory = data?.memory ?? data?.data ?? data ?? {};
      const longTerm = memory?.long_term ?? {};
      const shortTerm = memory?.short_term ?? {};

      // Total long-term memories stored.
      const total =
        Number(longTerm?.total_memories ?? memory?.total_memories ?? 0) || 0;

      // Count how many recent memories were created today.
      // The backend returns up to 5 recent items; this is an approximation
      // (correct when ≤ 5 memories were added today).
      const todayPrefix = new Date().toISOString().slice(0, 10); // "YYYY-MM-DD"
      const recentList: Array<{ created_at?: string }> = longTerm?.recent ?? [];
      const today = recentList.filter((m) =>
        m.created_at?.startsWith(todayPrefix),
      ).length;

      // Short-term buffer usage as a 0–100 percentage.
      const contextUsage = Number(shortTerm?.usage_percent ?? 0) || 0;

      setStats({
        total_memories: total,
        memories_today: today,
        context_usage: Math.round(contextUsage),
      });
    } catch (e) {
      console.error("Failed to fetch stats:", e);
      // Keep the zero defaults already in state — do not null-out the stats
      // because that would hide the StatCards entirely.
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
    if (activeTab === "personality") {
      void fetchPersonalityFragments();
      void fetchPersonalityStats();
    }
  }, [
    activeTab,
    fetchShortTermMemories,
    fetchPersonalityFragments,
    fetchPersonalityStats,
  ]);

  useEffect(() => {
    if (activeTab === "personality") {
      void fetchPersonalityFragments();
    }
  }, [personalityFilter]);

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
    const handleMessage = (payload: WebSocketMessage) => {
      if (payload?.type === "memory_update") {
        const data = payload?.data as MemoryUpdateData | undefined;
        const action = data?.action;
        const status = data?.details?.status;
        if (action === "stored" || status === "stored" || action === "added") {
          void fetchLongTermMemories();
          void fetchStats();
          if (activeTab === "short-term") void fetchShortTermMemories();
        }
      }

      if (payload?.type === "personality_update") {
        if (activeTab === "personality") {
          void fetchPersonalityFragments();
          void fetchPersonalityStats();
        }
      }
    };

    void connectSharedSocket("/ws");
    const unsubscribe = addMessageHandler(handleMessage);
    return unsubscribe;
  }, [activeTab]);

  // ── Render helpers ──────────────────────────────────────────────────────────

  const tabButtonClass = (tab: ActiveTab) =>
    `px-4 py-2 text-sm font-medium rounded-lg transition-all duration-150 flex items-center gap-2 ${
      activeTab === tab
        ? "bg-purple-500/20 text-purple-300 border border-purple-500/40"
        : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 border border-transparent"
    }`;

  const pendingPersonalityCount = personalityStats?.pending_count ?? 0;

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
            label="Added Today"
            value={stats.memories_today}
            icon={Calendar}
            color="text-blue-400"
            bg="bg-blue-500/10"
            delay={0.1}
            subLabel="from recent 5"
          />
          <StatCard
            label="Context Usage"
            value={`${stats.context_usage}%`}
            icon={TrendingUp}
            color="text-emerald-400"
            bg="bg-emerald-500/10"
            delay={0.15}
            subLabel="short-term buffer"
          />
        </div>

        {/* Section tabs */}
        <div className="flex items-center gap-2 flex-wrap">
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
          <button
            className={tabButtonClass("personality")}
            onClick={() => setActiveTab("personality")}
          >
            <Sparkles className="w-4 h-4" />
            Personality
            {pendingPersonalityCount > 0 && (
              <span className="ml-1 px-1.5 py-0.5 text-[10px] rounded-full bg-yellow-500/20 text-yellow-400 border border-yellow-600/40">
                {pendingPersonalityCount}
              </span>
            )}
          </button>
        </div>

        {/* Personality filter bar */}
        {activeTab === "personality" && (
          <div className="flex items-center justify-between gap-3 flex-wrap">
            <div className="flex items-center gap-1.5">
              {(["all", "approved", "pending", "rejected"] as const).map(
                (f) => (
                  <button
                    key={f}
                    onClick={() => setPersonalityFilter(f)}
                    className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-all capitalize ${
                      personalityFilter === f
                        ? "bg-purple-500/20 text-purple-300 border border-purple-500/40"
                        : "text-slate-400 hover:text-slate-200 border border-transparent hover:border-slate-700"
                    }`}
                  >
                    {f}
                    {f === "pending" && pendingPersonalityCount > 0 && (
                      <span className="ml-1.5 px-1 py-0.5 text-[9px] rounded-full bg-yellow-500/20 text-yellow-400">
                        {pendingPersonalityCount}
                      </span>
                    )}
                  </button>
                ),
              )}
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={handlePreviewBlock}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border border-slate-700 text-slate-400 hover:text-slate-200 hover:border-slate-600 transition"
              >
                <Eye className="w-3.5 h-3.5" />
                Preview
              </button>
              <button
                onClick={handleTriggerInference}
                disabled={inferring}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border border-purple-600/50 bg-purple-500/10 text-purple-300 hover:bg-purple-500/20 transition disabled:opacity-50"
              >
                <RefreshCw
                  className={`w-3.5 h-3.5 ${inferring ? "animate-spin" : ""}`}
                />
                {inferring ? "Inferring…" : "Run Inference"}
              </button>
              <button
                onClick={() => setShowAddFragment((v) => !v)}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border border-cyan-600/50 bg-cyan-500/10 text-cyan-300 hover:bg-cyan-500/20 transition"
              >
                <PlusCircle className="w-3.5 h-3.5" />
                Add Fact
              </button>
            </div>
          </div>
        )}

        {/* Add explicit fragment form */}
        {activeTab === "personality" && showAddFragment && (
          <div className="border border-cyan-700/40 rounded-lg bg-slate-900/60 p-4 space-y-3">
            <div className="flex items-center justify-between">
              <p className="text-sm font-medium text-slate-200">
                Add a personal fact
              </p>
              <button
                onClick={() => {
                  setShowAddFragment(false);
                  setNewFragmentContent("");
                }}
                className="text-slate-500 hover:text-slate-300 transition"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            <textarea
              value={newFragmentContent}
              onChange={(e) => setNewFragmentContent(e.target.value)}
              placeholder="e.g. The user prefers dark mode interfaces"
              rows={2}
              className="w-full bg-slate-950 border border-slate-700 focus:border-cyan-500 rounded px-3 py-2 text-sm text-slate-100 resize-none outline-none transition placeholder:text-slate-600"
            />
            <div className="flex items-center gap-3">
              <select
                value={newFragmentCategory}
                onChange={(e) => setNewFragmentCategory(e.target.value)}
                className="px-3 py-1.5 rounded bg-slate-900 border border-slate-700 text-slate-300 text-xs"
              >
                {[
                  "preference",
                  "trait",
                  "habit",
                  "fact",
                  "goal",
                  "dislike",
                  "relationship",
                  "work",
                  "health",
                  "hobby",
                ].map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
              <button
                onClick={handleAddExplicitFragment}
                disabled={addingFragment || !newFragmentContent.trim()}
                className="ml-auto flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-white transition"
              >
                {addingFragment ? "Adding…" : "Add & Approve"}
              </button>
            </div>
          </div>
        )}

        {/* Inference message */}
        {activeTab === "personality" && inferMessage && (
          <div className="text-xs text-purple-300 bg-purple-500/10 border border-purple-500/30 rounded px-3 py-2">
            {inferMessage}
          </div>
        )}

        {/* Search (long-term only) */}
        {activeTab === "long-term" && (
          <SearchInput
            value={search}
            onChange={setSearch}
            placeholder="Search long-term memories…"
          />
        )}
      </div>

      {/* Personality preview modal */}
      <AnimatePresence>
        {showPreview && previewBlock !== null && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4"
            onClick={() => setShowPreview(false)}
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="bg-slate-900 border border-slate-700 rounded-xl shadow-2xl w-full max-w-2xl max-h-[80vh] overflow-hidden flex flex-col"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-center justify-between px-5 py-4 border-b border-slate-700/60">
                <div className="flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-purple-400" />
                  <p className="text-sm font-semibold text-slate-100">
                    Personality Block Preview
                  </p>
                </div>
                <button
                  onClick={() => setShowPreview(false)}
                  className="text-slate-500 hover:text-slate-300 transition"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
              <div className="flex-1 overflow-y-auto p-5">
                <pre className="text-xs text-slate-300 whitespace-pre-wrap font-mono leading-relaxed">
                  {previewBlock || "(No personality fragments approved yet)"}
                </pre>
              </div>
              <div className="px-5 py-3 border-t border-slate-700/60 text-[10px] text-slate-500">
                This is exactly what Sena sees about you in every conversation.
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

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

          {/* ── Personality ── */}
          {activeTab === "personality" && (
            <motion.div
              key="personality"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.18 }}
            >
              {personalityLoading ? (
                <LoadingState message="Loading personality fragments…" />
              ) : personalityFragments.length === 0 ? (
                <EmptyState
                  icon={Sparkles}
                  message="No personality fragments found"
                  description={
                    personalityFilter !== "all"
                      ? `No ${personalityFilter} fragments. Try a different filter.`
                      : "Sena hasn't learned anything about you yet. Chat for a while, then click 'Run Inference' to extract personal facts."
                  }
                />
              ) : (
                <div className="space-y-3">
                  {personalityFilter === "all" &&
                    personalityStats &&
                    pendingPersonalityCount > 0 && (
                      <div className="flex items-center gap-2 text-xs text-yellow-400 bg-yellow-500/10 border border-yellow-600/30 rounded-lg px-3 py-2.5">
                        <Sparkles className="w-3.5 h-3.5 flex-shrink-0" />
                        <span>
                          {pendingPersonalityCount} fragment
                          {pendingPersonalityCount !== 1 ? "s" : ""} awaiting
                          your review. Filter by &quot;pending&quot; to review
                          them.
                        </span>
                      </div>
                    )}
                  {personalityFragments.map((fragment, index) => (
                    <motion.div
                      key={fragment.fragment_id}
                      initial={{ opacity: 0, y: 12 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: index * 0.03 }}
                    >
                      <PersonalityCard
                        fragment={fragment}
                        onApprove={handleApproveFragment}
                        onReject={handleRejectFragment}
                        onDelete={handleDeleteFragment}
                        onEdit={handleEditFragment}
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
