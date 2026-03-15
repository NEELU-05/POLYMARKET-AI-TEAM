"use client";

import { useEffect, useState } from "react";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from "recharts";
import { api, LessonRecord } from "@/services/api";

interface CategoryStat {
  name: string;
  winRate: number;
  total: number;
}

export default function CategoryChart({ overallWinRate }: { overallWinRate: number }) {
  const [categories, setCategories] = useState<CategoryStat[]>([]);

  useEffect(() => {
    api.getLessons().then((lessons: LessonRecord[]) => {
      const stats: Record<string, { wins: number; total: number }> = {};
      for (const l of lessons) {
        const cat = l.category || "other";
        if (!stats[cat]) stats[cat] = { wins: 0, total: 0 };
        stats[cat].total += 1;
        if (l.mistake_type === "correct_prediction") stats[cat].wins += 1;
      }
      const result = Object.entries(stats)
        .filter(([, s]) => s.total >= 1)
        .map(([name, s]) => ({
          name: name.charAt(0).toUpperCase() + name.slice(1),
          winRate: Math.round((s.wins / s.total) * 100),
          total: s.total,
        }))
        .sort((a, b) => b.total - a.total)
        .slice(0, 6);
      if (result.length > 0) setCategories(result);
    }).catch(() => {});
  }, []);

  const getColor = (rate: number) => {
    if (rate >= 60) return "#22c55e";
    if (rate >= 50) return "#eab308";
    return "#ef4444";
  };

  const displayData = categories.length > 0
    ? categories
    : [{ name: "No data yet", winRate: 50, total: 1 }];

  return (
    <div className="card h-full flex flex-col min-h-[300px]">
      <h3 className="mb-2 text-base font-semibold text-slate-200">Win Rate by Category</h3>
      <div className="flex-1 relative">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={displayData}
              cx="50%"
              cy="50%"
              innerRadius={70}
              outerRadius={95}
              paddingAngle={2}
              dataKey="total"
              stroke="none"
            >
              {displayData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={getColor(entry.winRate)} opacity={0.8} />
              ))}
            </Pie>
            <Tooltip
              content={({ active, payload }) => {
                if (active && payload && payload.length) {
                  const data = payload[0].payload;
                  return (
                    <div className="bg-slate-800 border border-slate-700 p-3 rounded-lg shadow-xl text-xs">
                      <p className="font-bold text-white mb-1.5">{data.name}</p>
                      <p className="text-slate-300">
                        Win Rate: <span className="font-semibold text-white ml-2">{data.winRate}%</span>
                      </p>
                      <p className="text-slate-300">
                        Lessons: <span className="font-semibold text-white ml-2">{data.total}</span>
                      </p>
                    </div>
                  );
                }
                return null;
              }}
            />
          </PieChart>
        </ResponsiveContainer>
        <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
          <span className="text-2xl font-bold text-white">{(overallWinRate * 100).toFixed(0)}%</span>
          <span className="text-[10px] text-slate-400">Overall Win Rate</span>
        </div>
      </div>
      <div className="mt-4 flex flex-wrap justify-center gap-3 text-xs">
        {displayData.map((c) => (
          <div key={c.name} className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: getColor(c.winRate) }} />
            <span className="text-slate-400">{c.name}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
