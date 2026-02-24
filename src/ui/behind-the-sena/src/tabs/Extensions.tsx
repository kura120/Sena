import React, { useEffect, useState } from "react";
import { RefreshCw, Zap, AlertCircle, Puzzle } from "lucide-react";
import { fetchJson } from "../utils/api";
import { TabLayout } from "../components/TabLayout";
import { EmptyState } from "../components/EmptyState";
import { LoadingState } from "../components/LoadingState";
import { IconButton } from "../components/IconButton";

type Extension = {
  name: string;
  enabled: boolean;
  metadata?: { description?: string; [key: string]: unknown };
};

export const Extensions: React.FC = () => {
  const [exts, setExts] = useState<Extension[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloading, setReloading] = useState<Set<string>>(new Set());
  const [toggling, setToggling] = useState<Set<string>>(new Set());

  useEffect(() => {
    void fetchExts();
  }, []);

  async function fetchExts() {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchJson<{
        extensions?: Extension[];
        data?: Extension[];
        items?: Extension[];
      }>("/api/v1/extensions");

      const extensionsList = data.extensions ?? data.data ?? data.items ?? [];

      if (Array.isArray(extensionsList) && extensionsList.length > 0) {
        setExts(extensionsList);
        setError(null);
      } else {
        setExts([]);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setExts([]);
    } finally {
      setLoading(false);
    }
  }

  async function reload(name: string) {
    setReloading((prev) => new Set(prev).add(name));
    try {
      await fetchJson(`/api/v1/extensions/${encodeURIComponent(name)}/reload`, {
        method: "POST",
      });
      void fetchExts();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setReloading((prev) => {
        const next = new Set(prev);
        next.delete(name);
        return next;
      });
    }
  }

  async function toggle(name: string, enabled: boolean) {
    setToggling((prev) => new Set(prev).add(name));
    try {
      await fetchJson(`/api/v1/extensions/${encodeURIComponent(name)}/toggle`, {
        method: "POST",
        body: { enabled },
      });
      setExts((prev) =>
        prev.map((ext) => (ext.name === name ? { ...ext, enabled } : ext)),
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setToggling((prev) => {
        const next = new Set(prev);
        next.delete(name);
        return next;
      });
    }
  }

  return (
    <TabLayout>
      {/* Header row */}
      <div className="px-6 pt-6 pb-4 flex items-center justify-between">
        <p className="text-xs text-slate-400">
          {exts.length} extension{exts.length !== 1 ? "s" : ""} available
        </p>
        <IconButton
          icon={RefreshCw}
          onClick={fetchExts}
          disabled={loading}
          loading={loading}
          label="Refresh extensions"
        />
      </div>

      {/* Error banner */}
      {error && (
        <div className="mx-6 mb-4 border border-red-700/40 bg-red-900/20 rounded-lg p-3 flex gap-2.5">
          <AlertCircle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
          <div>
            <h3 className="font-medium text-red-300 text-sm">
              Error loading extensions
            </h3>
            <p className="text-xs text-red-400 mt-1">{error}</p>
          </div>
        </div>
      )}

      {/* Content */}
      <div className="flex-1 overflow-y-auto px-6 pb-6">
        {loading && exts.length === 0 ? (
          <LoadingState message="Loading extensions…" />
        ) : exts.length === 0 && !error ? (
          <EmptyState
            icon={Puzzle}
            message="No extensions found"
            description="Add extensions to src/extensions/core/ or src/extensions/user/ to get started."
          />
        ) : (
          <div className="grid gap-3">
            {exts.map((ext) => (
              <div
                key={ext.name}
                className="border border-slate-700/40 rounded-lg p-3.5 bg-[#0F1629]/40 hover:bg-[#0F1629]/60 transition backdrop-blur-sm"
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-start gap-3 flex-1 min-w-0">
                    <div className="w-9 h-9 bg-purple-900/30 border border-purple-700/40 rounded-lg flex items-center justify-center mt-0.5 shrink-0">
                      <Zap className="w-4 h-4 text-purple-400" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <h3 className="font-medium text-white text-sm truncate">
                        {ext.name}
                      </h3>
                      <p className="text-xs text-slate-400 mt-1 line-clamp-2">
                        {ext.metadata?.description ??
                          "No description available"}
                      </p>
                      {ext.enabled && (
                        <div className="flex items-center gap-1 mt-2">
                          <div className="w-1.5 h-1.5 rounded-full bg-green-500" />
                          <span className="text-[10px] text-green-400 font-medium">
                            Active
                          </span>
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center gap-1.5 ml-3 shrink-0">
                    <IconButton
                      icon={RefreshCw}
                      onClick={() => void reload(ext.name)}
                      loading={reloading.has(ext.name)}
                      disabled={reloading.has(ext.name)}
                      label="Reload extension"
                    />
                    <button
                      onClick={() => void toggle(ext.name, !ext.enabled)}
                      disabled={toggling.has(ext.name)}
                      className={`px-2.5 py-1 rounded-md font-medium text-xs transition disabled:opacity-50 ${
                        ext.enabled
                          ? "bg-red-900/30 border border-red-700/40 text-red-400 hover:bg-red-900/50"
                          : "bg-green-900/30 border border-green-700/40 text-green-400 hover:bg-green-900/50"
                      }`}
                    >
                      {toggling.has(ext.name)
                        ? "…"
                        : ext.enabled
                          ? "Disable"
                          : "Enable"}
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </TabLayout>
  );
};
