"use client";

import { useEffect, useRef } from "react";
import { TradeRecord } from "@/services/api";

interface TradeModalProps {
  trade: TradeRecord | null;
  onClose: () => void;
}

export default function TradeModal({ trade, onClose }: TradeModalProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    if (trade) {
      dialogRef.current?.showModal();
    } else {
      dialogRef.current?.close();
    }
  }, [trade]);

  if (!trade) return null;

  return (
    <dialog
      ref={dialogRef}
      onClose={onClose}
      className="backdrop:bg-slate-900/80 backdrop:backdrop-blur-sm bg-transparent w-full max-w-2xl m-auto"
    >
      <div className="card w-full border border-slate-600 shadow-2xl shadow-blue-900/20 text-slate-100 p-0 overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-700 p-4 bg-slate-800/80">
          <h2 className="text-lg font-bold">Trade #{trade.id} Detail</h2>
          <button onClick={onClose} className="text-slate-400 hover:text-white transition-colors">
            ✕
          </button>
        </div>
        
        {/* Content */}
        <div className="p-6 space-y-6 max-h-[80vh] overflow-y-auto">
          <div>
            <p className="text-xs text-slate-400 mb-1">Market Question</p>
            <p className="text-sm font-medium leading-relaxed">{trade.question}</p>
          </div>
          
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="stat-card bg-slate-800/50 p-3 rounded-lg border border-slate-700/50">
              <p className="text-xs text-slate-400">Position</p>
              <p className={`font-bold ${trade.side === "yes" ? "text-green-400" : "text-red-400"}`}>
                {trade.side.toUpperCase()}
              </p>
            </div>
            <div className="stat-card bg-slate-800/50 p-3 rounded-lg border border-slate-700/50">
              <p className="text-xs text-slate-400">Size</p>
              <p className="font-bold">₹{trade.size.toFixed(2)}</p>
            </div>
            <div className="stat-card bg-slate-800/50 p-3 rounded-lg border border-slate-700/50">
              <p className="text-xs text-slate-400">Entry → Exit</p>
              <p className="font-bold">{trade.entry_price.toFixed(2)} → {trade.exit_price ? trade.exit_price.toFixed(2) : "—"}</p>
            </div>
            <div className="stat-card bg-slate-800/50 p-3 rounded-lg border border-slate-700/50">
              <p className="text-xs text-slate-400">PnL</p>
              <p className={`font-bold ${trade.pnl != null ? (trade.pnl >= 0 ? "text-green-400" : "text-red-400") : ""}`}>
                {trade.pnl != null ? `${trade.pnl >= 0 ? "+" : ""}₹${trade.pnl.toFixed(2)}` : "—"}
              </p>
            </div>
          </div>
          
          <div className="grid grid-cols-2 gap-4">
             <div className="bg-slate-800/50 p-4 rounded-lg border border-slate-700/50">
                <p className="text-xs text-slate-400 mb-2">Edge Calculation</p>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-slate-400">AI Probability:</span>
                    <span className="font-medium">{(trade.ai_probability * 100).toFixed(1)}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Market Probability:</span>
                    <span className="font-medium">{(trade.market_probability * 100).toFixed(1)}%</span>
                  </div>
                  <div className="flex justify-between border-t border-slate-700 pt-2 mt-2">
                    <span className="text-slate-400">Calculated Edge:</span>
                    <span className="font-medium text-blue-400">{(trade.edge * 100).toFixed(1)}%</span>
                  </div>
                </div>
             </div>
             
             <div className="bg-slate-800/50 p-4 rounded-lg border border-slate-700/50">
                <p className="text-xs text-slate-400 mb-2">Confidence Score</p>
                <div className="flex items-center justify-center h-full pb-4">
                  <div className="text-center">
                    <span className="text-3xl font-bold text-white">{(trade.confidence * 100).toFixed(0)}</span>
                    <span className="text-sm text-slate-400 ml-1">/ 100</span>
                  </div>
                </div>
             </div>
          </div>

          <div>
            <p className="text-xs text-slate-400 mb-2">AI Reasoning</p>
            <div className="bg-slate-900/50 rounded-lg p-4 border border-slate-700/50">
              <p className="text-sm text-slate-300 whitespace-pre-wrap leading-relaxed">
                {trade.reasoning || "No reasoning documented."}
              </p>
            </div>
          </div>
          
        </div>
      </div>
    </dialog>
  );
}
