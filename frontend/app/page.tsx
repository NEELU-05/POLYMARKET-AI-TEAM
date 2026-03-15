"use client";

import { useEffect, useState } from "react";
import { toast } from "react-hot-toast";
import {
  api,
  DashboardData,
  EquityPoint,
} from "@/services/api";
import dynamic from "next/dynamic";
import MetricCard from "@/components/MetricCard";
import Skeleton from "@/components/Skeleton";
import PipelineProgress from "@/components/PipelineProgress";

// Lazy load heavy charting components
const EquityChart = dynamic(() => import("@/components/EquityChart"), {
  ssr: false,
  loading: () => <Skeleton className="h-[300px] w-full rounded-xl" />
});
const CategoryChart = dynamic(() => import("@/components/CategoryChart"), {
  ssr: false,
  loading: () => <Skeleton className="h-[300px] w-full rounded-xl" />
});
const EdgeHistogram = dynamic(() => import("@/components/EdgeHistogram"), {
  ssr: false,
  loading: () => <Skeleton className="h-[300px] w-full rounded-xl" />
});
const PnLCalendar = dynamic(() => import("@/components/PnLCalendar"), {
  ssr: false,
  loading: () => <Skeleton className="h-[300px] w-full rounded-xl" />
});

export default function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [curve, setCurve] = useState<EquityPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [triggering, setTriggering] = useState(false);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 30000);
    return () => clearInterval(interval);
  }, []);

  async function loadData() {
    try {
      const [dashboard, equity] = await Promise.all([
        api.getDashboard(),
        api.getEquityCurve(),
      ]);
      setData(dashboard);
      setCurve(equity);
      setError("");
    } catch (e) {
      setError("Failed to load dashboard — is the backend running?");
    } finally {
      setLoading(false);
    }
  }

  async function handleRunPipeline() {
    setTriggering(true);
    try {
      await toast.promise(api.triggerPipeline(), {
        loading: "Running pipeline...",
        success: "Pipeline triggered successfully",
        error: "Pipeline trigger failed",
      });
      setTimeout(loadData, 2000);
    } catch {
      setError("Pipeline trigger failed");
    } finally {
      setTriggering(false);
    }
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <Skeleton className="h-8 w-48 mb-2" />
            <Skeleton className="h-4 w-64" />
          </div>
          <Skeleton className="h-10 w-32" />
        </div>

        <div className="grid grid-cols-2 gap-4 md:grid-cols-4 lg:grid-cols-6">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-28 w-full" />
          ))}
        </div>

        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-28 w-full" />
          ))}
        </div>

        <Skeleton className="h-[300px] w-full rounded-xl" />
        <Skeleton className="h-[120px] w-full rounded-xl" />
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-4">
        <p className="text-red-400">{error}</p>
        <button onClick={loadData} className="btn-primary">
          Retry
        </button>
      </div>
    );
  }

  if (!data) {
    return null;
  }

  const m = data.metrics;

  return (
    <div className="space-y-6 animate-page-in">
      {/* Header */}
      <div className="flex items-center justify-between pb-4 mb-2 border-b border-slate-800">
        <div>
          <h2 className="text-2xl font-bold bg-gradient-to-r from-white to-slate-400 bg-clip-text text-transparent">Dashboard</h2>
          <p className="text-sm text-slate-400">
            Paper trading simulation — starting capital {data.currency}500
          </p>
        </div>
        <div className="flex gap-3">
          {data.emergency_mode && (
            <div className="relative">
              <div className="absolute -inset-0.5 bg-gradient-to-r from-red-500 to-yellow-500 rounded-full blur opacity-60 animate-gradient-shift"></div>
              <span className="relative badge-yellow bg-slate-900 border-red-500/50">EMERGENCY MODE</span>
            </div>
          )}
          <button
            onClick={handleRunPipeline}
            disabled={triggering}
            className={`btn-primary flex items-center gap-2 ${triggering ? "cursor-wait opacity-80" : ""}`}
          >
            {triggering && <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />}
            {triggering ? "Running..." : "Run Pipeline"}
          </button>
        </div>
      </div>

      {/* Live Pipeline Progress */}
      <PipelineProgress />

      {/* Stat Cards */}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4 lg:grid-cols-6">
        <MetricCard
          label="Balance"
          value={`${data.currency}${data.balance.toFixed(2)}`}
          color={data.balance >= 500 ? "green" : "red"}
          sparklineData={curve.length > 0 ? curve.slice(-20).map(c => c.balance) : undefined}
        />
        <MetricCard
          label="Total PnL"
          value={`${m.total_pnl >= 0 ? "+" : ""}${data.currency}${m.total_pnl.toFixed(2)}`}
          color={m.total_pnl >= 0 ? "green" : "red"}
          sparklineData={curve.length > 0 ? curve.slice(-20).map(c => c.pnl) : undefined}
        />
        <MetricCard
          label="ROI"
          value={`${(m.roi * 100).toFixed(1)}%`}
          color={m.roi >= 0 ? "green" : "red"}
          sparklineData={curve.length > 0 ? curve.slice(-20).map(c => c.roi) : undefined}
        />
        <MetricCard label="Win Rate" value={`${(m.win_rate * 100).toFixed(1)}%`} />
        <MetricCard label="Total Trades" value={m.total_trades.toString()} />
        <MetricCard
          label="Open Positions"
          value={data.open_positions.toString()}
        />
      </div>

      {/* Secondary Metrics */}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <MetricCard
          label="Prediction Accuracy"
          value={`${(m.prediction_accuracy * 100).toFixed(1)}%`}
        />
        <MetricCard
          label="Avg Edge"
          value={`${(m.avg_edge * 100).toFixed(1)}%`}
        />
        <MetricCard
          label="Calibration Error"
          value={`${(m.calibration_error * 100).toFixed(1)}%`}
        />
        <MetricCard
          label="Max Drawdown"
          value={`${(m.max_drawdown * 100).toFixed(1)}%`}
          color={m.max_drawdown > 0.15 ? "red" : "default"}
        />
      </div>

      {/* Data Visualizations */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <CategoryChart overallWinRate={m.win_rate} />
        <EdgeHistogram />
        <PnLCalendar />
      </div>

      {/* Equity Curve */}
      <div className="card">
        <h3 className="mb-4 text-lg font-semibold">Equity Curve</h3>
        {curve.length > 0 ? (
          <EquityChart data={curve} currency={data.currency} />
        ) : (
          <p className="py-12 text-center text-slate-400">
            No data yet — run the pipeline to start trading
          </p>
        )}
      </div>

      {/* LLM Stats */}
      <div className="card">
        <h3 className="mb-3 text-lg font-semibold">LLM Usage</h3>
        <div className="grid grid-cols-4 gap-4 text-sm">
          <div>
            <p className="text-slate-400">Total Calls</p>
            <p className="text-lg font-medium">{data.llm_stats.total_calls}</p>
          </div>
          <div>
            <p className="text-slate-400">Total Tokens</p>
            <p className="text-lg font-medium">
              {data.llm_stats.total_tokens.toLocaleString()}
            </p>
          </div>
          <div>
            <p className="text-slate-400">Avg Latency</p>
            <p className="text-lg font-medium">
              {data.llm_stats.avg_latency_seconds}s
            </p>
          </div>
          <div>
            <p className="text-slate-400">Model</p>
            <p className="text-lg font-medium text-blue-400">step-3.5-flash</p>
          </div>
        </div>
      </div>
    </div>
  );
}
