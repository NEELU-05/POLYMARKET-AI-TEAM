"use client";

import { useEffect, useState } from "react";
import { api, TradeRecord } from "@/services/api";
import Skeleton from "@/components/Skeleton";
import TradeModal from "@/components/TradeModal";

export default function TradesPage() {
  const [trades, setTrades] = useState<TradeRecord[]>([]);
  const [filter, setFilter] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [selectedTrade, setSelectedTrade] = useState<TradeRecord | null>(null);
  const [knownTradeIds, setKnownTradeIds] = useState<Set<number>>(new Set());

  useEffect(() => {
    loadTrades();
  }, [filter]);

  async function loadTrades() {
    setLoading(true);
    try {
      const data = await api.getTrades(filter || undefined);
      
      // Update known trades to trigger animations for new ones
      setKnownTradeIds(prev => {
        const next = new Set(prev);
        if (prev.size > 0) { // Don't animate on initial load
          data.forEach(t => next.add(t.id));
        } else {
          data.forEach(t => next.add(t.id));
        }
        return next;
      });
      
      setTrades(data);
    } catch {
      console.error("Failed to load trades");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6 animate-page-in">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold bg-gradient-to-r from-white to-slate-400 bg-clip-text text-transparent">Trade History</h2>
        <div className="flex gap-2">
          {["", "open", "closed"].map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`rounded-lg px-3 py-1.5 text-sm ${
                filter === f
                  ? "bg-blue-600 text-white"
                  : "bg-slate-700 text-slate-300 hover:bg-slate-600"
              }`}
            >
              {f || "All"}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="space-y-4">
          <Skeleton className="h-10 w-full" />
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-16 w-full" />
          ))}
        </div>
      ) : trades.length === 0 ? (
        <div className="card py-12 text-center">
          <p className="text-slate-400">No trades yet</p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-700 text-left text-slate-400">
                <th className="px-3 py-3">ID</th>
                <th className="px-3 py-3">Market</th>
                <th className="px-3 py-3">Side</th>
                <th className="px-3 py-3">Entry</th>
                <th className="px-3 py-3">Exit</th>
                <th className="px-3 py-3">Size</th>
                <th className="px-3 py-3">AI Prob</th>
                <th className="px-3 py-3">Edge</th>
                <th className="px-3 py-3">PnL</th>
                <th className="px-3 py-3">Status</th>
                <th className="px-3 py-3">Date</th>
              </tr>
            </thead>
            <tbody>
              {trades.map((t) => (
                <tr
                  key={t.id}
                  onClick={() => setSelectedTrade(t)}
                  className={`border-b border-slate-700/50 hover:bg-slate-700/30 cursor-pointer ${
                    knownTradeIds.size > 0 && !knownTradeIds.has(t.id) ? "row-new" : ""
                  }`}
                >
                  <td className="px-3 py-3 text-slate-400">#{t.id}</td>
                  <td className="max-w-[200px] truncate px-3 py-3" title={t.question}>
                    {t.question}
                  </td>
                  <td className="px-3 py-3">
                    <span
                      className={
                        t.side === "yes" ? "text-green-400" : "text-red-400"
                      }
                    >
                      {t.side.toUpperCase()}
                    </span>
                  </td>
                  <td className="px-3 py-3">{t.entry_price.toFixed(2)}</td>
                  <td className="px-3 py-3">
                    {t.exit_price != null ? t.exit_price.toFixed(2) : "—"}
                  </td>
                  <td className="px-3 py-3">₹{t.size.toFixed(2)}</td>
                  <td className="px-3 py-3">
                    {(t.ai_probability * 100).toFixed(0)}%
                  </td>
                  <td className="px-3 py-3">
                    {(t.edge * 100).toFixed(1)}%
                  </td>
                  <td className="px-3 py-3">
                    {t.pnl != null ? (
                      <span
                        className={
                          t.pnl >= 0 ? "text-green-400" : "text-red-400"
                        }
                      >
                        {t.pnl >= 0 ? "+" : ""}₹{t.pnl.toFixed(2)}
                      </span>
                    ) : (
                      "—"
                    )}
                  </td>
                  <td className="px-3 py-3">
                    <span
                      className={
                        t.status === "open"
                          ? "badge-blue"
                          : t.pnl != null && t.pnl >= 0
                          ? "badge-green"
                          : "badge-red"
                      }
                    >
                      {t.status}
                    </span>
                  </td>
                  <td className="px-3 py-3 text-slate-400">
                    {t.opened_at ? new Date(t.opened_at).toLocaleDateString() : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Trade Detail Modal */}
      <TradeModal trade={selectedTrade} onClose={() => setSelectedTrade(null)} />
    </div>
  );
}
