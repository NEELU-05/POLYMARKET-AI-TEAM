"use client";

import { useEffect, useState } from "react";
import { api } from "@/services/api";

const WEEKS = 15;
const DAYS_PER_WEEK = 7;

interface DayData {
  date: string;
  pnl: number;
  hasTrade: boolean;
}

export default function PnLCalendar() {
  const [data, setData] = useState<DayData[]>([]);

  useEffect(() => {
    // Build 15-week grid of empty days first
    const now = new Date();
    const grid: DayData[] = [];
    for (let i = WEEKS * DAYS_PER_WEEK - 1; i >= 0; i--) {
      const d = new Date(now.getTime() - i * 24 * 60 * 60 * 1000);
      grid.push({
        date: d.toISOString().split("T")[0],
        pnl: 0,
        hasTrade: false,
      });
    }

    // Overlay real daily PnL
    api.getTradesSummary()
      .then((summary) => {
        const pnlMap: Record<string, number> = {};
        for (const day of summary.daily_pnl) {
          pnlMap[day.date] = day.pnl;
        }
        // Convert cumulative PnL to daily PnL by diffing consecutive days
        const sortedDates = Object.keys(pnlMap).sort();
        const dailyMap: Record<string, number> = {};
        for (let i = 0; i < sortedDates.length; i++) {
          const date = sortedDates[i];
          const prev = i > 0 ? pnlMap[sortedDates[i - 1]] : 0;
          dailyMap[date] = pnlMap[date] - prev;
        }
        setData(
          grid.map((d) => ({
            ...d,
            pnl: dailyMap[d.date] ?? 0,
            hasTrade: d.date in dailyMap,
          }))
        );
      })
      .catch(() => setData(grid));
  }, []);

  const getColor = (pnl: number, hasTrade: boolean) => {
    if (!hasTrade) return "bg-slate-700/30 border border-slate-700/50";
    if (pnl > 40) return "bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.4)]";
    if (pnl > 0) return "bg-green-500/50 border border-green-500/30";
    if (pnl > -40) return "bg-red-500/50 border border-red-500/30";
    return "bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.4)]";
  };

  return (
    <div className="card h-full flex flex-col min-h-[300px]">
      <h3 className="mb-4 text-base font-semibold text-slate-200">Daily PnL Heatmap</h3>
      <div className="flex-1 flex flex-col justify-center">
        <div className="overflow-x-auto pb-4 custom-scrollbar">
          <div
            className="grid gap-1 min-w-max pb-2"
            style={{
              gridTemplateRows: `repeat(${DAYS_PER_WEEK}, 1fr)`,
              gridAutoFlow: "column",
            }}
          >
            {data.map((day, i) => (
              <div
                key={i}
                title={`${day.date}\nPnL: ₹${day.pnl.toFixed(2)}`}
                className={`w-4 h-4 rounded-sm ${getColor(day.pnl, day.hasTrade)} cursor-pointer transition-transform hover:scale-125 hover:z-10`}
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
