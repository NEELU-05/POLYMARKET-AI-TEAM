/** API service layer — communicates with the FastAPI backend. */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API_KEY = process.env.NEXT_PUBLIC_API_KEY || "";

async function fetchAPI<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`API error: ${res.status} ${res.statusText}`);
  return res.json();
}

async function postAPI<T>(path: string, body?: unknown): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (API_KEY) headers["Authorization"] = `Bearer ${API_KEY}`;
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error(`API error: ${res.status} ${res.statusText}`);
  return res.json();
}

// --- Types ---

export interface DashboardData {
  balance: number;
  currency: string;
  emergency_mode: boolean;
  open_positions: number;
  metrics: PerformanceMetrics;
  llm_stats: LLMStats;
}

export interface PerformanceMetrics {
  total_trades: number;
  win_rate: number;
  total_pnl: number;
  roi: number;
  avg_edge: number;
  prediction_accuracy: number;
  calibration_error: number;
  max_drawdown: number;
}

export interface LLMStats {
  total_calls: number;
  total_tokens: number;
  total_latency_seconds: number;
  avg_latency_seconds: number;
  current_model: string;
}

export interface EquityPoint {
  timestamp: string;
  balance: number;
  pnl: number;
  roi: number;
}

export interface TradeRecord {
  id: number;
  condition_id: string;
  question: string;
  side: string;
  entry_price: number;
  exit_price: number | null;
  size: number;
  ai_probability: number;
  market_probability: number;
  edge: number;
  confidence: number;
  pnl: number | null;
  status: string;
  resolution: string | null;
  reasoning: string | null;
  opened_at: string | null;
  closed_at: string | null;
}

export interface ActivePosition {
  id: number;
  condition_id: string;
  question: string;
  side: string;
  entry_price: number;
  size: number;
  ai_probability: number;
  edge: number;
  opened_at: string | null;
}

export interface ActivePositions {
  positions: ActivePosition[];
  total_exposure: number;
  count: number;
}

export interface AgentActivityRecord {
  id: number;
  agent: string;
  action: string;
  details: Record<string, unknown>;
  status: string;
  duration_ms: number;
  timestamp: string;
}

export interface AgentStatus {
  agents: { name: string; status: string }[];
  event_bus_history: number;
}

export interface LessonRecord {
  id: number;
  trade_id: number | null;
  category: string;
  mistake_type: string;
  description: string;
  lesson: string;
  severity: string;
  tags: string[] | null;
  created_at: string;
}

export interface MemorySummary {
  total_lessons: number;
  mistake_distribution: Record<string, number>;
  critical_lessons: { lesson: string; type: string; severity: string }[];
  recent_lessons: { lesson: string; type: string }[];
  category_performance: Record<string, { total: number; mistakes: number }>;
}

export interface SystemStatus {
  running: boolean;
  started_at: string | null;
  cycles_completed: number;
  current_stage: string;      // NEW — empty string when idle
  pipeline_busy: boolean;     // NEW — true during manual trigger
}

export interface TradesSummary {
  edge_distribution: { name: string; wins: number; losses: number }[];
  daily_pnl: { date: string; pnl: number }[];
  total_closed: number;
}

// --- API Functions ---

export const api = {
  getDashboard: () => fetchAPI<DashboardData>("/api/dashboard"),
  getEquityCurve: () => fetchAPI<EquityPoint[]>("/api/dashboard/equity-curve"),
  getTrades: (status?: string) =>
    fetchAPI<TradeRecord[]>(`/api/trades${status ? `?status=${status}` : ""}`),
  getActivePositions: () => fetchAPI<ActivePositions>("/api/trades/active"),
  getAgentActivity: (agent?: string) =>
    fetchAPI<AgentActivityRecord[]>(
      `/api/agents/activity${agent ? `?agent_name=${agent}` : ""}`
    ),
  getAgentStatus: () => fetchAPI<AgentStatus>("/api/agents/status"),
  getLessons: (category?: string) =>
    fetchAPI<LessonRecord[]>(`/api/lessons${category ? `?category=${category}` : ""}`),
  getMemorySummary: () => fetchAPI<MemorySummary>("/api/memory/summary"),
  getEvents: (topic?: string) =>
    fetchAPI<unknown[]>(`/api/events${topic ? `?topic=${topic}` : ""}`),
  getTradesSummary: () => fetchAPI<TradesSummary>("/api/analytics/trades-summary"),
  triggerPipeline: () => postAPI<Record<string, unknown>>("/api/pipeline/run"),
  triggerReflection: () => postAPI<Record<string, unknown>>("/api/pipeline/reflect"),
  getSystemStatus: () => fetchAPI<SystemStatus>("/api/system/status"),
  startSystem: () => postAPI<SystemStatus>("/api/system/start"),
  stopSystem: () => postAPI<SystemStatus>("/api/system/stop"),
};
