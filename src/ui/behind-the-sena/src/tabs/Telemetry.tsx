import React, { useState, useEffect } from "react";
import {
  TrendingUp,
  Activity,
  Zap,
  Clock,
  AlertCircle,
  RefreshCw,
} from "lucide-react";
import { fetchJson } from "../utils/api";
import { TabLayout } from "../components/TabLayout";
import { StatCard } from "../components/StatCard";
import { LoadingState } from "../components/LoadingState";
import { Card } from "../components/Card";
import { IconButton } from "../components/IconButton";

type MetricsData = {
  requests_total: number;
  requests_today: number;
  avg_response_time_ms: number;
  errors: number;
  uptime_seconds: number;
  successful_requests: number;
  failed_requests: number;
  success_rate: number;
};

function formatUptime(seconds: number): string {
  if (seconds < 60) return `${Math.round(seconds)}s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
  if (seconds < 86400) {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    return `${h}h ${m}m`;
  }
  const d = Math.floor(seconds / 86400);
  const h = Math.floor((seconds % 86400) / 3600);
  return `${d}d ${h}h`;
}

function formatResponseTime(ms: number): string {
  if (ms === 0) return "—";
  if (ms < 1000) return `${Math.round(ms)}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

export const Telemetry: React.FC = () => {
  const [data, setData] = useState<MetricsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  useEffect(() => {
    void fetchMetrics();
    const interval = setInterval(() => void fetchMetrics(), 5000);
    return () => clearInterval(interval);
  }, []);

  async function fetchMetrics() {
    try {
      const res = await fetchJson<{
        status: string;
        metrics?: MetricsData;
        data?: MetricsData;
      }>("/api/v1/telemetry/metrics");
      const metrics =
        res.metrics ??
        (res.data as MetricsData) ??
        (res as unknown as MetricsData);
      setData({
        requests_total: metrics.requests_total ?? 0,
        requests_today: metrics.requests_today ?? 0,
        avg_response_time_ms: metrics.avg_response_time_ms ?? 0,
        errors: metrics.errors ?? 0,
        uptime_seconds: metrics.uptime_seconds ?? 0,
        successful_requests: metrics.successful_requests ?? 0,
        failed_requests: metrics.failed_requests ?? 0,
        success_rate: metrics.success_rate ?? 0,
      });
      setError(null);
      setLastUpdated(new Date());
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  if (loading && !data) {
    return (
      <TabLayout>
        <LoadingState message="Loading telemetry…" />
      </TabLayout>
    );
  }

  return (
    <TabLayout scrollable>
      {/* Header */}
      <div className="px-6 pt-6 pb-2 flex items-center justify-between">
        <div>
          <h2 className="text-base font-semibold text-slate-50">
            Telemetry &amp; Metrics
          </h2>
          {lastUpdated && (
            <p className="text-[11px] text-slate-500 mt-0.5">
              Updated {lastUpdated.toLocaleTimeString()}
            </p>
          )}
        </div>
        <IconButton
          icon={RefreshCw}
          onClick={fetchMetrics}
          disabled={loading}
          loading={loading}
          label="Refresh metrics"
        />
      </div>

      {/* Error banner */}
      {error && (
        <div className="mx-6 mb-2 border border-red-700/40 bg-red-900/20 rounded-lg p-3 flex gap-2.5">
          <AlertCircle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
          <p className="text-xs text-red-300">{error}</p>
        </div>
      )}

      <div className="px-6 pb-6 space-y-6">
        {/* Stats Grid */}
        {data && (
          <div className="grid grid-cols-2 gap-4">
            <StatCard
              label="Total Requests"
              value={data.requests_total}
              icon={TrendingUp}
              color="text-blue-400"
              bg="bg-blue-500/10"
              delay={0.05}
            />
            <StatCard
              label="Requests Today"
              value={data.requests_today}
              icon={Activity}
              color="text-emerald-400"
              bg="bg-emerald-500/10"
              delay={0.1}
            />
            <StatCard
              label="Avg Response Time"
              value={formatResponseTime(data.avg_response_time_ms)}
              icon={Zap}
              color="text-orange-400"
              bg="bg-orange-500/10"
              delay={0.15}
            />
            <StatCard
              label="Uptime"
              value={formatUptime(data.uptime_seconds)}
              icon={Clock}
              color="text-purple-400"
              bg="bg-purple-500/10"
              delay={0.2}
            />
          </div>
        )}

        {/* Request breakdown */}
        {data && (
          <Card>
            <h3 className="text-sm font-semibold text-slate-100 mb-4">
              Request Breakdown
            </h3>
            <div className="space-y-0">
              <div className="flex items-center justify-between py-3 border-b border-slate-800/50">
                <span className="text-sm text-slate-400">Successful</span>
                <span className="text-sm font-semibold text-green-400 tabular-nums">
                  {data.successful_requests}
                </span>
              </div>
              <div className="flex items-center justify-between py-3 border-b border-slate-800/50">
                <span className="text-sm text-slate-400">Failed</span>
                <span className="text-sm font-semibold text-red-400 tabular-nums">
                  {data.failed_requests}
                </span>
              </div>
              <div className="flex items-center justify-between py-3 border-b border-slate-800/50">
                <span className="text-sm text-slate-400">Errors</span>
                <span className="text-sm font-semibold text-yellow-400 tabular-nums">
                  {data.errors}
                </span>
              </div>
              <div className="flex items-center justify-between py-3">
                <span className="text-sm text-slate-400">Success Rate</span>
                <span className="text-sm font-semibold text-blue-400 tabular-nums">
                  {data.success_rate > 0
                    ? `${(data.success_rate * 100).toFixed(1)}%`
                    : "—"}
                </span>
              </div>
            </div>
          </Card>
        )}
      </div>
    </TabLayout>
  );
};
