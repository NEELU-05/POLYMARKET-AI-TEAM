"use client";

import { useEffect, useState } from "react";
import { api, AgentActivityRecord, AgentStatus } from "@/services/api";
import Skeleton from "@/components/Skeleton";
import LiveFeed from "@/components/LiveFeed";

export default function AgentsPage() {
  const [activities, setActivities] = useState<AgentActivityRecord[]>([]);
  const [status, setStatus] = useState<AgentStatus | null>(null);
  const [selectedAgent, setSelectedAgent] = useState<string>("");
  const [activeTab, setActiveTab] = useState<"live" | "history">("live");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 10000);
    return () => clearInterval(interval);
  }, [selectedAgent]);

  async function loadData() {
    try {
      const [acts, st] = await Promise.all([
        api.getAgentActivity(selectedAgent || undefined),
        api.getAgentStatus(),
      ]);
      setActivities(acts);
      setStatus(st);
    } catch {
      console.error("Failed to load agent data");
    } finally {
      setLoading(false);
    }
  }

  const agents = status?.agents || [];

  return (
    <div className="space-y-6 animate-page-in">
      <h2 className="text-2xl font-bold bg-gradient-to-r from-white to-slate-400 bg-clip-text text-transparent">Agent Activity</h2>

      {/* Agent Status Grid */}
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4 lg:grid-cols-6">
        {agents.map((a) => (
          <button
            key={a.name}
            onClick={() =>
              setSelectedAgent(selectedAgent === a.name ? "" : a.name)
            }
            className={`rounded-lg border px-3 py-2 text-left text-sm transition-colors ${
              selectedAgent === a.name
                ? "border-blue-500 bg-blue-600/20"
                : "border-slate-700 bg-slate-800 hover:border-slate-600"
            }`}
          >
            <p className="font-medium">
              {a.name.replace(/_/g, " ")}
            </p>
            <p className={`text-xs ${a.status === "ready" ? "text-green-400" : a.status === "error" ? "text-red-400" : "text-yellow-400"}`}>{a.status}</p>
          </button>
        ))}
      </div>

      <div className="flex gap-6 border-b border-slate-700/50 pb-2 mb-4">
        <button 
          onClick={() => setActiveTab("live")} 
          className={`pb-2 -mb-2.5 transition-colors border-b-2 ${activeTab === "live" ? "border-blue-500 text-blue-400 font-bold" : "border-transparent text-slate-400 hover:text-slate-300"}`}
        >
          Live Feed
        </button>
        <button 
          onClick={() => setActiveTab("history")} 
          className={`pb-2 -mb-2.5 transition-colors border-b-2 ${activeTab === "history" ? "border-blue-500 text-blue-400 font-bold" : "border-transparent text-slate-400 hover:text-slate-300"}`}
        >
          History
        </button>
      </div>

      {activeTab === "live" ? (
        <LiveFeed selectedAgent={selectedAgent} />
      ) : (
        <div className="card">
          <h3 className="mb-4 text-lg font-semibold">
            {selectedAgent
              ? `${selectedAgent.replace(/_/g, " ")} Activity`
              : "All Activity"}
          </h3>

          {loading ? (
            <div className="space-y-2">
              {Array.from({ length: 5 }).map((_, i) => (
                <Skeleton key={i} className="h-16 w-full" />
              ))}
            </div>
          ) : activities.length === 0 ? (
            <p className="py-6 text-center text-slate-400">No activity logged yet</p>
          ) : (
            <div className="space-y-2">
              {activities.map((a) => (
                <div
                  key={a.id}
                  className="flex items-center gap-4 rounded-lg border border-slate-700/50 bg-slate-700/20 px-4 py-3"
                >
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-blue-400">
                        {a.agent.replace(/_/g, " ")}
                      </span>
                      <span className="text-sm text-slate-300">{a.action}</span>
                    </div>
                    {a.details && Object.keys(a.details).length > 0 && (
                      <p className="mt-1 text-xs text-slate-400">
                        {JSON.stringify(a.details).slice(0, 150)}
                      </p>
                    )}
                  </div>
                  <div className="text-right">
                    <span
                      className={
                        a.status === "completed" ? "badge-green" : "badge-red"
                      }
                    >
                      {a.status}
                    </span>
                    <p className="mt-1 text-xs text-slate-500">
                      {a.duration_ms}ms
                    </p>
                  </div>
                  <p className="text-xs text-slate-500">
                    {new Date(a.timestamp).toLocaleTimeString()}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
