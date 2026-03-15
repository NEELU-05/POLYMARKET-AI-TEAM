"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState, useCallback } from "react";
import { toast } from "react-hot-toast";
import { BarChart3, ClipboardList, TrendingUp, Bot, Brain } from "lucide-react";
import { api, SystemStatus } from "@/services/api";

const navItems = [
  { href: "/", label: "Dashboard", icon: BarChart3 },
  { href: "/trades", label: "Trade History", icon: ClipboardList },
  { href: "/positions", label: "Active Positions", icon: TrendingUp },
  { href: "/agents", label: "Agent Activity", icon: Bot },
  { href: "/memory", label: "Learning / Memory", icon: Brain },
];

export default function Sidebar() {
  const pathname = usePathname();
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [loading, setLoading] = useState(false);

  const fetchStatus = useCallback(async () => {
    try {
      const s = await api.getSystemStatus();
      setStatus(s);
    } catch {
      setStatus(null);
    }
  }, []);

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 5000);
    return () => clearInterval(interval);
  }, [fetchStatus]);

  const handleToggle = async () => {
    setLoading(true);
    try {
      if (status?.running) {
        await toast.promise(
          api.stopSystem().then(s => setStatus(s)),
          {
            loading: "Stopping system...",
            success: "System stopped",
            error: "Failed to stop system",
          }
        );
      } else {
        await toast.promise(
          api.startSystem().then(s => setStatus(s)),
          {
            loading: "Starting system...",
            success: "System started",
            error: "Failed to start system",
          }
        );
      }
    } catch {
      // ignore
    }
    setLoading(false);
  };

  const running = status?.running ?? false;

  return (
    <aside className="flex w-64 flex-col border-r border-slate-700 bg-slate-800/50">
      <div className="border-b border-slate-700 px-6 py-5">
        <h1 className="text-lg font-bold text-white">Polymarket AI</h1>
        <p className="text-xs text-slate-400">Multi-Agent Research Team</p>
      </div>
      <nav className="flex-1 space-y-1 p-3">
        {navItems.map((item) => {
          const active = pathname === item.href;
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-colors ${
                active
                  ? "bg-blue-600/20 text-blue-400"
                  : "text-slate-300 hover:bg-slate-700/50 hover:text-white"
              }`}
            >
              <Icon className="h-5 w-5" />
              {item.label}
            </Link>
          );
        })}
      </nav>

      {/* System Start/Stop Control */}
      <div className="border-t border-slate-700 p-4 space-y-3">
        <button
          onClick={handleToggle}
          disabled={loading || status === null}
          className={`w-full flex items-center justify-center gap-2 rounded-lg px-4 py-3 text-sm font-bold transition-all ${
            loading
              ? "bg-slate-600 text-slate-300 cursor-wait"
              : running
              ? "bg-red-600 hover:bg-red-700 text-white"
              : "bg-green-600 hover:bg-green-700 text-white"
          } disabled:opacity-50`}
        >
          {loading ? (
            <>
              <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
              {running ? "Stopping..." : "Starting..."}
            </>
          ) : running ? (
            <>
              <span className="text-lg">⏹</span>
              Stop System
            </>
          ) : (
            <>
              <span className="text-lg">▶</span>
              Start System
            </>
          )}
        </button>

        {/* Full-width Status indicator */}
        <div
          className={`w-full rounded-md px-3 py-2 text-center text-sm font-medium ${
            status === null
              ? "bg-slate-700/50 text-slate-400"
              : running
              ? "bg-gradient-to-r from-green-900/40 to-green-800/40 border border-green-800 text-green-400 shadow-[0_0_10px_rgba(34,197,94,0.1)]"
              : "bg-gradient-to-r from-slate-800/80 to-slate-700/80 border border-slate-600 text-slate-400"
          }`}
        >
          <div className="flex items-center justify-center gap-2">
            <span
              className={`h-2 w-2 rounded-full ${
                status === null
                  ? "bg-slate-500"
                  : running
                  ? "bg-green-400 animate-pulse shadow-[0_0_8px_rgba(34,197,94,0.8)]"
                  : "bg-slate-500"
              }`}
            />
            <span>
              {status === null
                ? "Connecting..."
                : running
                ? "LIVE — Running"
                : "STOPPED"}
            </span>
          </div>
          {running && status?.cycles_completed !== undefined && (
            <p className="mt-1 text-xs text-green-400/70">
              {status.cycles_completed} cycle{status.cycles_completed !== 1 ? "s" : ""} completed
            </p>
          )}
        </div>

        <div className="rounded-lg bg-slate-700/50 px-3 py-2">
          <p className="text-xs text-slate-400">Mode</p>
          <p className="text-sm font-medium text-yellow-400">Paper Trading</p>
        </div>
      </div>
    </aside>
  );
}
