"use client";

import { useEffect, useState } from "react";

const WEEKS = 15; // roughly 105 days
const DAYS_PER_WEEK = 7;

function generateMockHeatmap() {
  const data = [];
  const now = new Date();
  for (let i = WEEKS * DAYS_PER_WEEK - 1; i >= 0; i--) {
    const d = new Date(now.getTime() - i * 24 * 60 * 60 * 1000);
    const val = (Math.random() - 0.45) * 200; // bias towards small profit
    const hasTrade = Math.random() > 0.4; // 60% probability of no trades to simulate empty gaps
    data.push({
      date: d.toISOString().split('T')[0],
      pnl: hasTrade ? val : 0,
      trades: hasTrade ? Math.floor(Math.random() * 8) + 1 : 0,
    });
  }
  return data;
}

export default function PnLCalendar() {
  const [data, setData] = useState<{date: string, pnl: number, trades: number}[]>([]);
  
  useEffect(() => {
    setData(generateMockHeatmap());
  }, []);

  const getColor = (pnl: number, trades: number) => {
    if (trades === 0) return "bg-slate-700/30 border border-slate-700/50";
    if (pnl > 40) return "bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.4)]";
    if (pnl > 0) return "bg-green-500/50 border border-green-500/30";
    if (pnl > -40) return "bg-red-500/50 border border-red-500/30";
    return "bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.4)]";
  };

  return (
    <div className="card h-full flex flex-col min-h-[300px]">
      <h3 className="mb-4 text-base font-semibold text-slate-200">Daily PnL Heatmap (Recent)</h3>
      <div className="flex-1 flex flex-col justify-center">
        <div className="overflow-x-auto pb-4 custom-scrollbar">
          <div 
            className="grid gap-1 min-w-max pb-2" 
            style={{ 
              gridTemplateRows: `repeat(${DAYS_PER_WEEK}, 1fr)`, 
              gridAutoFlow: "column" 
            }}
          >
            {data.map((day, i) => (
              <div
                key={i}
                title={`${day.date}\nPnL: ₹${day.pnl.toFixed(2)}\nTrades: ${day.trades}`}
                className={`w-4 h-4 rounded-sm ${getColor(day.pnl, day.trades)} cursor-pointer transition-transform hover:scale-125 hover:z-10`}
              />
            ))}
          </div>
        </div>
      </div>
      <div className="mt-auto flex items-center justify-end gap-2 text-[10px] text-slate-400 font-medium">
        <span>Loss</span>
        <div className="w-3.5 h-3.5 rounded-sm bg-red-500" />
        <div className="w-3.5 h-3.5 rounded-sm bg-red-500/50" />
        <div className="w-3.5 h-3.5 rounded-sm bg-slate-700/30 border border-slate-700/50" />
        <div className="w-3.5 h-3.5 rounded-sm bg-green-500/50" />
        <div className="w-3.5 h-3.5 rounded-sm bg-green-500" />
        <span>Profit</span>
      </div>
    </div>
  );
}
