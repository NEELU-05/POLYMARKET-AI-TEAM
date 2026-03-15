"use client";

import { useEffect, useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { Search, Home, Activity, List, Bot, Brain } from "lucide-react";

export default function CommandPalette() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);
  const router = useRouter();

  // Keyboard shortcut listener
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Toggle Command Palette: Cmd+K or Ctrl+K
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setOpen((o) => !o);
      }
      
      // Close on Escape
      if (e.key === "Escape") {
        setOpen(false);
      }

      // Number shortcuts for fast navigation
      if (!open && (e.metaKey || e.ctrlKey) && parseInt(e.key) >= 1 && parseInt(e.key) <= 5) {
        e.preventDefault();
        const routes = ["/", "/trades", "/positions", "/agents", "/memory"];
        router.push(routes[parseInt(e.key) - 1]);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [open, router]);

  // Focus input when opened
  useEffect(() => {
    if (open) {
      setTimeout(() => inputRef.current?.focus(), 50);
    } else {
      setQuery("");
    }
  }, [open]);

  if (!open) return null;

  const commands = [
    { name: "Go to Dashboard", shortcut: "Ctrl+1", icon: Home, action: () => router.push("/") },
    { name: "Go to Trade History", shortcut: "Ctrl+2", icon: List, action: () => router.push("/trades") },
    { name: "Go to Active Positions", shortcut: "Ctrl+3", icon: Activity, action: () => router.push("/positions") },
    { name: "Go to Agent Activity", shortcut: "Ctrl+4", icon: Bot, action: () => router.push("/agents") },
    { name: "Go to Learning/Memory", shortcut: "Ctrl+5", icon: Brain, action: () => router.push("/memory") },
  ];

  const filteredCommands = commands.filter((cmd) =>
    cmd.name.toLowerCase().includes(query.toLowerCase())
  );

  const executeCommand = (action: () => void) => {
    action();
    setOpen(false);
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-start justify-center pt-32 bg-slate-900/50 backdrop-blur-sm animate-page-in">
      <div 
        className="fixed inset-0"
        onClick={() => setOpen(false)}
      />
      
      <div className="relative w-full max-w-lg bg-slate-800 border border-slate-700 shadow-2xl rounded-xl overflow-hidden divide-y divide-slate-700/50">
        
        {/* Search Input */}
        <div className="flex items-center px-4 py-3">
          <Search className="w-5 h-5 text-slate-400 mr-3 shrink-0" />
          <input
            ref={inputRef}
            type="text"
            className="w-full bg-transparent border-none text-white focus:outline-none placeholder-slate-500 text-lg"
            placeholder="Search commands..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <kbd className="hidden sm:inline-block px-2 py-0.5 rounded text-xs font-mono bg-slate-700 text-slate-400">
            ESC
          </kbd>
        </div>

        {/* Command List */}
        <div className="max-h-80 overflow-y-auto p-2 scroll-smooth custom-scrollbar">
          {filteredCommands.length === 0 ? (
            <p className="px-4 py-8 text-center text-sm text-slate-500">
              No results found for &quot;{query}&quot;
            </p>
          ) : (
            filteredCommands.map((cmd) => (
              <button
                key={cmd.name}
                onClick={() => executeCommand(cmd.action)}
                className="w-full flex items-center justify-between px-3 py-2.5 text-sm text-slate-300 rounded-lg hover:bg-slate-700/50 hover:text-white transition-colors group"
              >
                <div className="flex items-center gap-3">
                  <cmd.icon className="w-4 h-4 text-slate-400 group-hover:text-blue-400 transition-colors" />
                  <span>{cmd.name}</span>
                </div>
                {cmd.shortcut && (
                  <kbd className="px-2 py-0.5 rounded text-xs font-mono bg-slate-700/50 text-slate-400">
                    {cmd.shortcut}
                  </kbd>
                )}
              </button>
            ))
          )}
        </div>
        
      </div>
    </div>
  );
}
