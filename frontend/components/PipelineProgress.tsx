"use client";

import { useEffect, useState } from "react";
import { api, SystemStatus } from "@/services/api";

const STAGES = ["Scanning", "Classifying", "Analyzing", "Strategy", "Executing", "Done"];

export default function PipelineProgress() {
  const [status, setStatus] = useState<SystemStatus | null>(null);

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const s = await api.getSystemStatus();
        setStatus(s);
      } catch {
        // ignore
      }
    };
    fetchStatus();
    const interval = setInterval(fetchStatus, 2000); // Polling every 2s
    return () => clearInterval(interval);
  }, []);

  if (!status || !status.running) return null;

  const currentMessage = status.message || "";
  const lowerMsg = currentMessage.toLowerCase();
  
  let currentStageIndex = 0;
  if (lowerMsg.includes("scan")) currentStageIndex = 0;
  else if (lowerMsg.includes("classif")) currentStageIndex = 1;
  else if (lowerMsg.includes("analy")) currentStageIndex = 2;
  else if (lowerMsg.includes("strateg")) currentStageIndex = 3;
  else if (lowerMsg.includes("execut")) currentStageIndex = 4;
  else if (lowerMsg.includes("done")) currentStageIndex = 5;

  return (
    <div className="card w-full mb-6 py-4">
      <div className="flex justify-between mb-3">
        <h3 className="text-sm font-semibold">Live Pipeline Progress</h3>
        <span className="text-xs text-blue-400 font-medium">{status.message || "Running..."}</span>
      </div>
      <div className="flex gap-2">
        {STAGES.map((stage, i) => {
          const isActive = i === currentStageIndex;
          const isPast = i < currentStageIndex;
          return (
            <div key={stage} className="flex-1">
              <div 
                className={`h-2 w-full rounded-full transition-colors duration-500 ${
                  isActive ? "bg-blue-500 shadow-[0_0_10px_rgba(59,130,246,0.6)] animate-pulse" :
                  isPast ? "bg-blue-500/40" : "bg-slate-700/50"
                }`}
              />
              <p className={`mt-1.5 text-[10px] sm:text-xs text-center font-medium ${
                  isActive ? "text-blue-400" : isPast ? "text-slate-400" : "text-slate-600"
              }`}>
                {stage}
              </p>
            </div>
          );
        })}
      </div>
    </div>
  );
}
