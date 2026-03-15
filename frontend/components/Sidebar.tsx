"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState, useCallback } from "react";
import { toast } from "react-hot-toast";
import { 
  BarChart3, 
  ClipboardList, 
  TrendingUp, 
  Bot, 
  Brain, 
  Menu, 
  X, 
  ChevronLeft, 
  ChevronRight,
  Settings,
  LayoutGrid
} from "lucide-react";
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
  const [isOpen, setIsOpen] = useState(false); // Mobile menu open
  const [isCollapsed, setIsCollapsed] = useState(false); // Desktop collapsed

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

  // Close mobile menu on route change
  useEffect(() => {
    setIsOpen(false);
  }, [pathname]);

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
    <>
      {/* Mobile Header (Always visible on mobile) */}
      <div className="flex items-center justify-between border-b border-slate-700 bg-slate-800/80 backdrop-blur-md px-4 py-3 md:hidden sticky top-0 z-30">
        <div className="flex items-center gap-2">
          <div className="h-8 w-8 rounded bg-blue-600 flex items-center justify-center">
            <span className="font-bold text-white text-sm">P</span>
          </div>
          <span className="font-bold text-white text-sm tracking-tight">Polymarket AI</span>
        </div>
        <button 
          onClick={() => setIsOpen(true)}
          className="p-1 text-slate-300 hover:text-white transition-colors"
        >
          <Menu className="h-6 w-6" />
        </button>
      </div>

      {/* Mobile Overlay */}
      {isOpen && (
        <div 
          className="fixed inset-0 z-40 bg-slate-900/60 backdrop-blur-sm md:hidden"
          onClick={() => setIsOpen(false)}
        />
      )}

      {/* Sidebar Container */}
      <aside 
        className={`fixed inset-y-0 left-0 z-50 flex flex-col border-r border-slate-700 bg-slate-800 transition-all duration-300 md:relative md:translate-x-0 ${
          isOpen ? "translate-x-0 w-64" : "-translate-x-full w-0 md:w-64"
        } ${isCollapsed && !isOpen ? "md:w-20" : "md:w-64"}`}
      >
        <div className={`relative flex items-center justify-between border-b border-slate-700 px-6 py-5 ${isCollapsed && !isOpen ? "px-0 justify-center" : ""}`}>
          <div className={`overflow-hidden transition-all duration-300 ${isCollapsed && !isOpen ? "w-0 opacity-0" : "w-auto opacity-100"}`}>
            <h1 className="text-lg font-bold text-white whitespace-nowrap">Polymarket AI</h1>
            <p className="text-xs text-slate-400 whitespace-nowrap">Multi-Agent Team</p>
          </div>
          
          {/* Logo only when collapsed */}
          {isCollapsed && !isOpen && (
             <div className="h-10 w-10 rounded-lg bg-blue-600 flex items-center justify-center shrink-0">
               <span className="font-bold text-white text-xl">P</span>
             </div>
          )}

          <button 
            onClick={() => setIsOpen(false)}
            className="p-1 text-slate-400 hover:text-white md:hidden"
          >
            <X className="h-6 w-6" />
          </button>
          
          {/* Collapse Toggle for Desktop */}
          <button
            onClick={() => setIsCollapsed(!isCollapsed)}
            className="absolute -right-3 top-1/2 -translate-y-1/2 hidden h-6 w-6 items-center justify-center rounded-full border border-slate-600 bg-slate-800 text-slate-400 hover:text-white md:flex"
          >
            {isCollapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
          </button>
        </div>

        <nav className="flex-1 space-y-1 p-3 overflow-y-auto">
          {navItems.map((item) => {
            const active = pathname === item.href;
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                title={isCollapsed ? item.label : ""}
                className={`group flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-all ${
                  active
                    ? "bg-blue-600/20 text-blue-400"
                    : "text-slate-300 hover:bg-slate-700/50 hover:text-white"
                } ${isCollapsed && !isOpen ? "justify-center px-0" : ""}`}
              >
                <Icon className={`h-5 w-5 shrink-0 transition-transform ${active ? "scale-110" : "group-hover:scale-110"}`} />
                <span className={`transition-all duration-300 ${isCollapsed && !isOpen ? "hidden opacity-0 w-0" : "block opacity-100"}`}>
                  {item.label}
                </span>
              </Link>
            );
          })}
        </nav>

        {/* System Start/Stop Control */}
        <div className="border-t border-slate-700 p-4 space-y-3 overflow-hidden">
          <button
            onClick={handleToggle}
            disabled={loading || status === null}
            className={`w-full flex items-center justify-center gap-2 rounded-lg py-3 text-sm font-bold transition-all ${
              loading
                ? "bg-slate-600 text-slate-300 cursor-wait"
                : running
                ? "bg-red-600 hover:bg-red-700 text-white"
                : "bg-green-600 hover:bg-green-700 text-white"
            } disabled:opacity-50 ${isCollapsed && !isOpen ? "px-0 h-10 w-10 mx-auto rounded-full" : "px-4"}`}
          >
            {loading ? (
              <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
            ) : running ? (
              <span className="text-lg">⏹</span>
            ) : (
              <span className="text-lg">▶</span>
            )}
            <span className={`${isCollapsed && !isOpen ? "hidden" : "inline"}`}>
              {running ? "Stop System" : "Start System"}
            </span>
          </button>

          {/* Full-width Status indicator */}
          {!isCollapsed || isOpen ? (
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
                <span className="truncate">
                  {status === null
                    ? "Connecting..."
                    : running
                    ? "LIVE"
                    : "STOPPED"}
                </span>
              </div>
            </div>
          ) : (
            <div className={`mx-auto h-2 w-2 rounded-full ${status === null ? "bg-slate-500" : running ? "bg-green-400 animate-pulse" : "bg-slate-500"}`} />
          )}

          <div className={`rounded-lg bg-slate-700/50 px-3 py-2 ${isCollapsed && !isOpen ? "hidden" : "block"}`}>
            <p className="text-xs text-slate-400">Mode</p>
            <p className="text-sm font-medium text-yellow-400">Paper Trading</p>
          </div>
        </div>
      </aside>
    </>
  );
}

