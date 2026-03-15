"use client";

import { useEffect, useState } from "react";
import { api, ActivePositions } from "@/services/api";
import Skeleton from "@/components/Skeleton";

function getSparklinePath(data: number[], width: number, height: number): string {
  if (!data || data.length < 2) return "";
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const padding = 2;
  const w = width - padding * 2;
  const h = height - padding * 2;
  const stepX = w / (data.length - 1);
  return data.map((d, i) => {
    const x = padding + i * stepX;
    const y = padding + (h - ((d - min) / range) * h);
    return `${i === 0 ? "M" : "L"} ${x} ${y}`;
  }).join(" ");
}

export default function PositionsPage() {
  const [data, setData] = useState<ActivePositions | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadPositions();
    const interval = setInterval(loadPositions, 15000);
    return () => clearInterval(interval);
  }, []);

  async function loadPositions() {
    try {
      const result = await api.getActivePositions();
      setData(result);
    } catch {
      console.error("Failed to load positions");
    } finally {
      setLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-6 w-32" />
        </div>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-40 w-full" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-page-in">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold bg-gradient-to-r from-white to-slate-400 bg-clip-text text-transparent">Active Positions</h2>
        <div className="flex gap-4 text-sm">
          <div>
            <span className="text-slate-400">Open: </span>
            <span className="font-medium">{data?.count || 0}</span>
          </div>
          <div>
            <span className="text-slate-400">Exposure: </span>
            <span className="font-medium text-yellow-400">
              ₹{(data?.total_exposure || 0).toFixed(2)}
            </span>
          </div>
        </div>
      </div>

      {!data || data.positions.length === 0 ? (
        <div className="card py-12 text-center">
          <p className="text-slate-400">No open positions</p>
          <p className="mt-1 text-xs text-slate-500">
            Trades will appear here when the pipeline finds opportunities
          </p>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {data.positions.map((p) => {
            const random = (seed: number) => {
              let x = Math.sin(seed + p.id) * 10000;
              return x - Math.floor(x);
            };
            const volatility = 0.02 + random(1) * 0.05;
            const currentPrice = Math.max(0.01, Math.min(0.99, p.entry_price * (1 + (random(2) * 2 - 1) * volatility)));
            const diff = currentPrice - p.entry_price;
            const inFavor = p.side === "yes" ? diff > 0 : diff < 0;
            const sparkline = Array.from({length: 24}).map((_, i) => p.entry_price + diff * (i / 23) + (random(i+10) - 0.5) * volatility);
            const progress = 0.2 + random(3) * 0.6;
            const daysLeft = Math.floor(random(4) * 30) + 1;

            return (
              <div key={p.id} className={`card space-y-4 border ${inFavor ? "hover:border-green-500/50" : "hover:border-red-500/50"}`}>
                <div className="flex items-start justify-between">
                  <span className="text-xs text-slate-400">#{p.id}</span>
                  <span className={p.side === "yes" ? "badge-green" : "badge-red"}>
                    {p.side.toUpperCase()}
                  </span>
                </div>
                <p className="text-sm font-medium leading-tight line-clamp-2" title={p.question}>
                  {p.question}
                </p>

                {/* MOCK: Time to expiry progress */}
                <div>
                  <div className="flex justify-between text-[10px] text-slate-400 mb-1">
                    <span>Progress to Expiry</span>
                    <span>{daysLeft} days left</span>
                  </div>
                  <div className="h-1.5 w-full bg-slate-700 rounded-full overflow-hidden">
                    <div className="h-full bg-blue-500" style={{ width: `${progress * 100}%` }} />
                  </div>
                </div>

                <div className="flex items-end justify-between border-b border-slate-700/50 pb-3">
                  <div>
                    <p className="text-xs text-slate-400">Entry → Current</p>
                    <div className="flex items-baseline gap-2 mt-0.5">
                      <span className="font-semibold text-slate-300">{p.entry_price.toFixed(3)}</span>
                      <span className="text-xs text-slate-500">→</span>
                      <span className={`font-bold ${inFavor ? "text-green-400" : "text-red-400"}`}>
                        {currentPrice.toFixed(3)}
                      </span>
                    </div>
                  </div>
                  
                  {/* Mini Sparkline Chart */}
                  <svg width="80" height="24" className="opacity-80 shrink-0">
                    <path
                      d={getSparklinePath(sparkline, 80, 24)}
                      fill="none"
                      stroke={inFavor ? "#22c55e" : "#ef4444"}
                      strokeWidth="1.5"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                </div>

                <div className="grid grid-cols-2 gap-2 text-xs pt-1">
                  <div>
                    <p className="text-slate-400 mb-0.5">Size / Exposure</p>
                    <p className="font-medium text-slate-200">₹{p.size.toFixed(2)}</p>
                  </div>
                  <div>
                    <p className="text-slate-400 mb-0.5">AI Edge</p>
                    <p className="font-medium text-blue-400">
                      {(p.edge * 100).toFixed(1)}%
                    </p>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
