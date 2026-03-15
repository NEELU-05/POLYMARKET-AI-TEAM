"use client";

import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from "recharts";

const MOCK_CATEGORIES = [
  { name: "Crypto", winRate: 65, total: 40 },
  { name: "Politics", winRate: 55, total: 35 },
  { name: "Sports", winRate: 45, total: 20 },
  { name: "Pop Culture", winRate: 70, total: 15 },
  { name: "Science", winRate: 48, total: 10 },
];

export default function CategoryChart({ overallWinRate }: { overallWinRate: number }) {
  const getColor = (rate: number) => {
    if (rate >= 60) return "#22c55e"; // green-500
    if (rate >= 50) return "#eab308"; // yellow-500
    return "#ef4444"; // red-500
  };

  return (
    <div className="card h-full flex flex-col min-h-[300px]">
      <h3 className="mb-2 text-base font-semibold text-slate-200">Win Rate by Category</h3>
      <div className="flex-1 relative">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={MOCK_CATEGORIES}
              cx="50%"
              cy="50%"
              innerRadius={70}
              outerRadius={95}
              paddingAngle={2}
              dataKey="total"
              stroke="none"
            >
              {MOCK_CATEGORIES.map((entry, index) => (
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
                      <p className="text-slate-300">Win Rate: <span className="font-semibold text-white ml-2">{data.winRate}%</span></p>
                      <p className="text-slate-300">Trades: <span className="font-semibold text-white ml-2">{data.total}</span></p>
                    </div>
                  );
                }
                return null;
              }}
            />
          </PieChart>
        </ResponsiveContainer>
        {/* Center Text */}
        <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
          <span className="text-2xl font-bold text-white">{(overallWinRate * 100).toFixed(0)}%</span>
          <span className="text-[10px] text-slate-400">Overall Win Rate</span>
        </div>
      </div>
      {/* Legend */}
      <div className="mt-4 flex flex-wrap justify-center gap-3 text-xs">
        {MOCK_CATEGORIES.map((c) => (
          <div key={c.name} className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: getColor(c.winRate) }} />
            <span className="text-slate-400">{c.name}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
