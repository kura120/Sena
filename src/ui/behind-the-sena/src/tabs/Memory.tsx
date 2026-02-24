import React, { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { Brain, TrendingUp, Calendar } from "lucide-react";
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
  details?: {
    status?: string;
    [key: string]: unknown;
  };
  [key: string]: unknown;
};

type Memory = {
  id: number;
  title: string;
  tag: string;
  relevance: number;
  created_at?: string;
  category?: string;
};

type MemoryStats = {
  total_memories: number;
  memories_today: number;
  accuracy: number;
};

export const Memory: React.FC = () => {
  const [search, setSearch] = useState("");
  const [memories, setMemories] = useState<Memory[]>([]);
  const [stats, setStats] = useState<MemoryStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    void fetchMemories();
    void fetchStats();
  }, []);

  useEffect(() => {
    if (search) {
      const debounce = setTimeout(() => void fetchMemories(), 300);
      return () => clearTimeout(debounce);
    }
  }, [search]);

  useEffect(() => {
    let socket: WebSocket | null = null;

    const handleMessage = (payload: WebSocketMessage) => {
      if (payload?.type !== "memory_update") return;

      const data = payload?.data as MemoryUpdateData | undefined;
      const action = data?.action;
      const status = data?.details?.status;
      if (action === "stored" || status === "stored" || action === "added") {
        void fetchMemories();
        void fetchStats();
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
      if (socket) {
        closeWebSocket(socket);
      }
    };
  }, []);

  async function fetchMemories() {
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
      const mapped = results.map((item: any) => ({
        id: item.memory_id || item.id,
        title: item.content || item.title || "Untitled memory",
        tag: item.metadata?.source || item.tag || "memory",
        relevance: Math.round((item.relevance ?? 1) * 100),
        created_at: item.created_at,
        category: item.metadata?.category || item.category,
      }));
      setMemories(mapped);
    } catch (e) {
      console.error("Failed to fetch memories:", e);
    }
  }

  async function fetchStats() {
    try {
      const data = await fetchJson<any>("/api/v1/memory/stats");
      setStats(data.memory || data);
      setLoading(false);
    } catch (e) {
      console.error("Failed to fetch stats:", e);
      setLoading(false);
    }
  }

  return (
    <TabLayout>
      {/* Stats + Search header */}
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
              value={`${Math.round(stats.accuracy * 100)}%`}
              icon={TrendingUp}
              color="text-emerald-400"
              bg="bg-emerald-500/10"
              delay={0.15}
            />
          </div>
        )}

        <SearchInput
          value={search}
          onChange={setSearch}
          placeholder="Search memories…"
        />
      </div>

      {/* Memory grid */}
      <div className="flex-1 overflow-y-auto px-6 pb-6">
        {loading ? (
          <LoadingState message="Loading memories…" />
        ) : memories.length === 0 ? (
          <EmptyState
            icon={Brain}
            message="No memories found"
            description={
              search
                ? `No memories match "${search}". Try a different search term.`
                : "Start a conversation with Sena to create memories."
            }
          />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {memories.map((memory, index) => (
              <motion.div
                key={memory.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.05 }}
              >
                <MemoryCard
                  title={memory.title}
                  tag={memory.tag}
                  relevance={memory.relevance}
                />
              </motion.div>
            ))}
          </div>
        )}
      </div>
    </TabLayout>
  );
};
