"use client";

import { useEffect, useState, useRef } from "react";
import { wsService } from "@/services/ws";

interface LiveEvent {
  event_id: string;
  source: string;
  topic: string;
  data: any;
  timestamp: string;
}

export default function LiveFeed({ selectedAgent }: { selectedAgent?: string }) {
  const [events, setEvents] = useState<LiveEvent[]>([]);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const unsub = wsService.subscribe("event_bus", (data: LiveEvent) => {
      setEvents(prev => {
        const newEvents = [...prev, data];
        if (newEvents.length > 200) return newEvents.slice(newEvents.length - 200);
        return newEvents;
      });
    });

    return () => unsub();
  }, []);

  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [events]);

  const filteredEvents = selectedAgent 
    ? events.filter(e => e.source === selectedAgent)
    : events;

  return (
    <div className="card h-full flex flex-col font-mono text-sm bg-slate-900 border border-slate-700 shadow-xl shadow-blue-900/10">
      <div className="flex items-center justify-between border-b border-slate-700 pb-3 mb-3 shrink-0">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
          <h3 className="font-semibold text-slate-200">Live Terminal Feed</h3>
        </div>
        <span className="text-[10px] uppercase text-slate-500 tracking-wider font-bold">WebSocket Connected</span>
      </div>

      <div ref={containerRef} className="flex-1 overflow-y-auto custom-scrollbar pr-2 space-y-1.5 h-[400px]">
        {filteredEvents.length === 0 ? (
          <p className="text-slate-500 text-center py-8 text-xs italic">Awaiting event streams...</p>
        ) : (
          filteredEvents.map((ev, idx) => {
            const time = new Date(ev.timestamp).toLocaleTimeString([], { hour12: false, fractionalSecondDigits: 3 });
            return (
              <div key={ev.event_id || idx} className="flex flex-col sm:flex-row gap-1 sm:gap-3 text-[11px] opacity-80 hover:opacity-100 hover:bg-slate-800/80 p-1.5 rounded transition-colors cursor-default">
                <span className="text-slate-500 shrink-0 select-none">[{time}]</span>
                <span className="text-blue-400 font-semibold shrink-0 sm:w-40 truncate" title={ev.source}>[{ev.source}]</span>
                <span className="text-yellow-400 shrink-0 sm:w-32 truncate" title={ev.topic}>{ev.topic}</span>
                <span className="text-slate-300 break-all">{typeof ev.data === 'object' ? JSON.stringify(ev.data) : String(ev.data)}</span>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
