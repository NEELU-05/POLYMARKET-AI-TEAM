"use client";

import { useEffect, useState } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import { api, LessonRecord, MemorySummary } from "@/services/api";
import Skeleton from "@/components/Skeleton";

const SEVERITY_COLORS: Record<string, string> = {
  critical: "#ef4444",
  high: "#f97316",
  medium: "#eab308",
  low: "#22c55e",
};

export default function MemoryPage() {
  const [lessons, setLessons] = useState<LessonRecord[]>([]);
  const [summary, setSummary] = useState<MemorySummary | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    try {
      const [l, s] = await Promise.all([
        api.getLessons(),
        api.getMemorySummary(),
      ]);
      setLessons(l);
      setSummary(s);
    } catch {
      console.error("Failed to load memory data");
    } finally {
      setLoading(false);
    }
  }

  async function handleReflect() {
    try {
      await api.triggerReflection();
      setTimeout(loadData, 2000);
    } catch {
      console.error("Reflection trigger failed");
    }
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <Skeleton className="h-8 w-48 mb-2" />
            <Skeleton className="h-4 w-32" />
          </div>
          <Skeleton className="h-10 w-32" />
        </div>
        <Skeleton className="h-64 w-full" />
        <div className="space-y-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-24 w-full" />
          ))}
        </div>
      </div>
    );
  }

  const mistakeData = summary
    ? Object.entries(summary.mistake_distribution).map(([type, count]) => ({
        type: type.replace(/_/g, " "),
        count,
      }))
    : [];

  return (
    <div className="space-y-6 animate-page-in">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold bg-gradient-to-r from-white to-slate-400 bg-clip-text text-transparent">Learning / Memory</h2>
          <p className="text-sm text-slate-400">
            {summary?.total_lessons || 0} total lessons learned
          </p>
        </div>
        <button onClick={handleReflect} className="btn-primary">
          Run Reflection
        </button>
      </div>

      {/* Mistake Distribution Chart */}
      {mistakeData.length > 0 && (
        <div className="card">
          <h3 className="mb-4 text-lg font-semibold">Mistake Distribution</h3>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={mistakeData}>
              <XAxis dataKey="type" stroke="#64748b" fontSize={12} />
              <YAxis stroke="#64748b" fontSize={12} />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#1e293b",
                  border: "1px solid #334155",
                  borderRadius: "8px",
                  color: "#f1f5f9",
                }}
              />
              <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                {mistakeData.map((_, i) => (
                  <Cell
                    key={i}
                    fill={["#3b82f6", "#8b5cf6", "#ec4899", "#f97316", "#22c55e"][i % 5]}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Critical Lessons */}
      {summary && summary.critical_lessons.length > 0 && (
        <div className="card border-red-900/50">
          <h3 className="mb-3 text-lg font-semibold text-red-400">
            Critical Lessons
          </h3>
          <div className="space-y-2">
            {summary.critical_lessons.map((l, i) => (
              <div
                key={i}
                className="rounded-lg border border-red-900/30 bg-red-900/10 px-4 py-3"
              >
                <p className="text-sm">{l.lesson}</p>
                <p className="mt-1 text-xs text-slate-400">
                  Type: {l.type} | Severity: {l.severity}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* All Lessons */}
      <div className="card">
        <h3 className="mb-4 text-lg font-semibold">All Lessons</h3>
        {lessons.length === 0 ? (
          <p className="py-6 text-center text-slate-400">
            No lessons yet — run reflection after markets resolve
          </p>
        ) : (
          <div className="space-y-3">
            {lessons.map((l) => (
              <div
                key={l.id}
                className="rounded-lg border border-slate-700/50 bg-slate-700/20 px-4 py-3"
              >
                <div className="flex items-center gap-2">
                  <span
                    className="badge"
                    style={{
                      backgroundColor:
                        (SEVERITY_COLORS[l.severity] || "#64748b") + "20",
                      color: SEVERITY_COLORS[l.severity] || "#64748b",
                    }}
                  >
                    {l.severity}
                  </span>
                  <span className="badge-blue">{l.mistake_type || "general"}</span>
                  {l.trade_id && (
                    <span className="text-xs text-slate-500">
                      Trade #{l.trade_id}
                    </span>
                  )}
                </div>
                <p className="mt-2 text-sm">{l.description}</p>
                <p className="mt-1 text-sm text-blue-300">{l.lesson}</p>
                <div className="mt-2 flex gap-1">
                  {(l.tags || []).map((tag, i) => (
                    <span key={i} className="badge bg-slate-600/50 text-slate-300">
                      {tag}
                    </span>
                  ))}
                </div>
                <p className="mt-2 text-xs text-slate-500">
                  {new Date(l.created_at).toLocaleDateString()}
                </p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
