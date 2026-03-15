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
        data.forEach(t => next.add(t.id));
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
        <>
          {/* Desktop Table View */}
          <div className="hidden md:block overflow-x-auto">
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
                    className={`border-b border-slate-700/50 hover:bg-slate-700/30 cursor-pointer transition-colors ${
                      knownTradeIds.size > 0 && !knownTradeIds.has(t.id) ? "row-new" : ""
                    }`}
                  >
                    <td className="px-3 py-3 text-slate-400">#{t.id}</td>
                    <td className="max-w-[200px] truncate px-3 py-3 font-medium" title={t.question}>
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

          {/* Mobile Card View */}
          <div className="space-y-4 md:hidden">
            {trades.map((t) => (
              <div
                key={t.id}
                onClick={() => setSelectedTrade(t)}
                className={`card p-4 space-y-3 cursor-pointer active:scale-[0.98] transition-transform ${
                  knownTradeIds.size > 0 && !knownTradeIds.has(t.id) ? "row-new border-green-500/50" : ""
                }`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <p className="text-xs text-slate-400 mb-1">#{t.id} • {t.opened_at ? new Date(t.opened_at).toLocaleDateString() : "—"}</p>
                    <h3 className="text-sm font-bold line-clamp-2">{t.question}</h3>
                  </div>
                  <span
                    className={`ml-3 text-xs font-bold px-2 py-0.5 rounded ${
                      t.side === "yes" ? "bg-green-500/20 text-green-400" : "bg-red-500/20 text-red-400"
                    }`}
                  >
                    {t.side.toUpperCase()}
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-4 border-t border-slate-700/50 pt-3">
                  <div>
                    <p className="text-[10px] text-slate-500 uppercase font-bold tracking-wider">Entry/Exit</p>
                    <p className="text-sm">
                      {t.entry_price.toFixed(2)} → {t.exit_price != null ? t.exit_price.toFixed(2) : "—"}
                    </p>
                  </div>
                  <div>
                    <p className="text-[10px] text-slate-500 uppercase font-bold tracking-wider">Size</p>
                    <p className="text-sm font-medium">₹{t.size.toFixed(2)}</p>
                  </div>
                  <div>
                    <p className="text-[10px] text-slate-500 uppercase font-bold tracking-wider">Edge / Prob</p>
                    <p className="text-sm">
                      {(t.edge * 100).toFixed(1)}% / {(t.ai_probability * 100).toFixed(0)}%
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-[10px] text-slate-500 uppercase font-bold tracking-wider">PnL</p>
                    {t.pnl != null ? (
                      <p className={`text-sm font-bold ${t.pnl >= 0 ? "text-green-400" : "text-red-400"}`}>
                        {t.pnl >= 0 ? "+" : ""}₹{t.pnl.toFixed(2)}
                      </p>
                    ) : (
                      <span className="badge-blue text-[10px] px-1.5 py-0">OPEN</span>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </>
      )}


      {/* Trade Detail Modal */}
      <TradeModal trade={selectedTrade} onClose={() => setSelectedTrade(null)} />
    </div>
  );
}
