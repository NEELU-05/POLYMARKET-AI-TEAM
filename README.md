# Polymarket AI Team

A self-learning multi-agent system that scans [Polymarket](https://polymarket.com) prediction markets, estimates true probabilities using real-time data, and executes paper trades where it finds edge. Eleven AI agents work in a pipeline from market scanning through to reflection and memory — getting smarter with each resolved trade.

**Current status:** Paper trading only. No real money is ever moved.

---

## What It Does

Every 30 minutes the system runs a full cycle:

```
Scan Markets → Classify → Research (live news) → Signal (price momentum, volume)
→ Probability Estimate → Find Edge → Risk Check → Execute (paper) → Reflect & Learn
```

When markets resolve, a reflection agent analyses what went right or wrong and stores lessons. Those lessons feed back into the next cycle's prompts — the system accumulates calibration data over time and adjusts its estimates accordingly.

---

## Quick Start

You need **Python 3.11+** and **Node.js 18+**. No Docker required for the default SQLite setup.

**1. Start the backend**

```bash
cd backend
pip install -r requirements.txt
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Verify it's running: open http://localhost:8000/health — you should see `{"status":"ok"}`.

**2. Start the dashboard**

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000.

**3. Start the system**

Click **Start System** in the bottom-left of the sidebar. The status dot turns green and the pipeline begins.

Or double-click `START WEBSITE.bat` on Windows — it starts the frontend and opens the browser automatically.

---

## Configuration

All settings live in `backend/.env`. Copy the example to get started:

```bash
cp backend/.env.example backend/.env
```

The only required change is your OpenRouter API key:

```env
OPENROUTER_API_KEY=sk-or-v1-your-key-here
```

Everything else has sensible defaults. Key settings:

| Setting | Default | Description |
|---|---|---|
| `LLM_MODEL` | `nvidia/nemotron-3-super-120b-a12b:free` | LLM via OpenRouter (free tier works) |
| `STARTING_CAPITAL` | `500.0` | Paper trading balance |
| `MAX_TRADE_SIZE` | `30.0` | Max size per trade |
| `MAX_OPEN_TRADES` | `5` | Max concurrent positions |
| `MIN_EDGE` | `0.08` | Minimum 8% edge required to trade |
| `SCAN_INTERVAL_MINUTES` | `30` | How often to run the pipeline |
| `SERPER_API_KEY` | *(optional)* | Enables real-time web search in research agent |
| `NEWS_API_KEY` | *(optional)* | Enables live news headlines in research agent |
| `API_SECRET_KEY` | *(optional)* | Bearer token for POST endpoints |

Search API keys are optional but strongly recommended — without them the research agent falls back to the LLM's training data, which is stale.

---

## Dashboard Pages

| Page | URL | What it shows |
|---|---|---|
| Dashboard | `/` | Balance, PnL, ROI, equity curve, LLM usage |
| Trade History | `/trades` | All paper trades with AI reasoning |
| Active Positions | `/positions` | Open positions with entry/current price |
| Agent Activity | `/agents` | Live WebSocket feed + agent logs |
| Learning / Memory | `/memory` | Lessons learned, mistake distribution |

**Keyboard shortcuts:** `Ctrl+K` opens the command palette. `Ctrl+1` through `Ctrl+5` navigate between pages.

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    ORCHESTRATOR                      │
│                                                     │
│  MarketScanner → MarketClassifier                   │
│       ↓                                             │
│  ResearchAgent (Serper + News API)                  │
│       ↓                                             │
│  SignalAgent (timeseries, volume spikes, orderbook) │
│       ↓                                             │
│  ProbabilityAgent (calibration-adjusted estimate)   │
│       ↓                                             │
│  StrategyAgent (Kelly sizing, resolution timing)    │
│       ↓                                             │
│  RiskManager (drawdown, duplicate, position limits) │
│       ↓                                             │
│  ExecutionAgent (orderbook-aware entry price)       │
│       ↓                                             │
│  PortfolioManager → ReflectionAgent → MemoryManager │
└─────────────────────────────────────────────────────┘
```

**Backend:** Python 3.11, FastAPI, SQLAlchemy (async), SQLite (default) or PostgreSQL, Redis (optional), httpx, structlog.

**Frontend:** Next.js 15, React 19, Tailwind CSS 3.4, Recharts, lucide-react, WebSocket live feed.

---

## Agents

| Agent | Role |
|---|---|
| **MarketScanner** | Fetches active markets from Polymarket's Gamma API, filters by volume and liquidity |
| **MarketClassifier** | Classifies markets by category (crypto, politics, macro, etc.) in a single batched LLM call |
| **ResearchAgent** | Searches for live news and web results, injects past lessons, asks the LLM to analyse |
| **SignalAgent** | Computes real price momentum from timeseries data, detects volume spikes from trade history |
| **ProbabilityAgent** | Estimates true probability independent of market price, adjusted by calibration history |
| **StrategyAgent** | Identifies edge, sizes positions using quarter-Kelly, prioritises near-expiry near-certain bets |
| **RiskManager** | Enforces capital rules: max trades, drawdown circuit breaker, duplicate position guard |
| **ExecutionAgent** | Walks the CLOB orderbook to find real fill price, skips trades with spread > 8 cents |
| **PortfolioManager** | Tracks balance, PnL, ROI, drawdown, saves snapshots for equity curve |
| **ReflectionAgent** | On market resolution: calculates PnL, runs LLM post-mortem, stores lessons |
| **MemoryManager** | Retrieves past lessons and per-category calibration data for injection into future prompts |

---

## Safety

The system has multiple layers preventing runaway losses:

- **Paper trading only** — the execution agent writes to a local database, not Polymarket's CLOB
- **Circuit breaker** — stops all trading if balance drops below ₹300 (40% drawdown)
- **Emergency mode** — reduces max position size to ₹10 if balance falls below ₹350
- **Max 5 open trades** at once, max ₹30 per trade
- **Duplicate guard** — won't open a second position on the same market
- **Spread filter** — execution agent skips markets where the bid-ask spread exceeds 8 cents
- **Kelly sizing** — quarter-Kelly by default, so individual positions are conservative

---

## API Endpoints

The backend runs at `http://localhost:8000`. All `POST` endpoints require a `Bearer` token if `API_SECRET_KEY` is set in `.env`.

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `GET` | `/api/dashboard` | Dashboard metrics and LLM stats |
| `GET` | `/api/dashboard/equity-curve` | Balance history for chart |
| `GET` | `/api/trades` | Trade history (filterable by status) |
| `GET` | `/api/trades/active` | Open positions |
| `GET` | `/api/agents/activity` | Agent action log |
| `GET` | `/api/agents/status` | Agent health |
| `GET` | `/api/lessons` | Stored lessons from reflection |
| `GET` | `/api/memory/summary` | Aggregated memory state |
| `GET` | `/api/analytics/trades-summary` | Edge distribution + daily PnL for charts |
| `GET` | `/api/system/status` | Scheduler running state + current pipeline stage |
| `POST` | `/api/system/start` | Start the background scheduler |
| `POST` | `/api/system/stop` | Stop the scheduler |
| `POST` | `/api/pipeline/run` | Manually trigger one pipeline cycle |
| `POST` | `/api/pipeline/reflect` | Manually trigger reflection on resolved markets |
| `WS` | `/api/ws/events` | WebSocket stream of all internal events |

---

## Project Structure

```
POLYMARKET AI TEAM/
├── START WEBSITE.bat          # Windows: starts frontend, opens browser
├── backend/
│   ├── .env                   # Your configuration (create from .env.example)
│   ├── .env.example           # Template with all available settings
│   ├── main.py                # FastAPI app entry point
│   ├── requirements.txt       # Python dependencies
│   └── app/
│       ├── agents/            # All 11 agents
│       ├── api/
│       │   ├── routes.py      # REST API endpoints
│       │   └── websocket.py   # WebSocket event stream
│       ├── core/
│       │   ├── config.py      # Settings (pydantic-settings)
│       │   ├── event_bus.py   # Internal pub/sub
│       │   ├── llm_client.py  # OpenRouter client with retry + rate limiting
│       │   └── logging.py     # structlog setup
│       ├── db/database.py     # SQLAlchemy async engine + session
│       ├── models/
│       │   ├── db_models.py   # ORM models (Trade, Lesson, Snapshot, etc.)
│       │   └── schemas.py     # Pydantic inter-agent schemas
│       ├── services/
│       │   ├── orchestrator.py  # Pipeline coordinator
│       │   ├── polymarket.py    # Gamma, Data, CLOB API clients
│       │   ├── scheduler.py     # Background pipeline + reflection loops
│       │   └── search_service.py # Serper + News API integration
│       └── trading/
│           └── simulator.py   # Paper trading balance + PnL tracking
└── frontend/
    ├── app/                   # Next.js pages
    ├── components/            # React components
    └── services/
        ├── api.ts             # Typed fetch wrappers for backend
        └── ws.ts              # Auto-reconnecting WebSocket client
```

---

## Troubleshooting

**Backend won't start / import errors**

Make sure you're running from the `backend/` directory and have installed dependencies:
```bash
cd backend && pip install -r requirements.txt
python -m uvicorn main:app --reload --port 8000
```

**Dashboard shows "Connecting..." or Start button is greyed out**

The backend isn't running. Start it first, then refresh the page.

**Agent Activity page is empty**

This is a known issue — the orchestrator currently calls `agent.run()` instead of `agent.timed_run()`, so activity isn't logged to the database. It's a one-line fix per agent call in `orchestrator.py`.

**Pipeline runs but finds no trades**

The system requires ≥8% edge to trade. With a free LLM and no search API keys, the probability estimates are often too close to market price to clear the threshold. Add `SERPER_API_KEY` and `NEWS_API_KEY` to `.env` for real-time data, which significantly improves estimate quality.

**LLM not responding / pipeline hangs**

Check your OpenRouter key at https://openrouter.ai/keys. The LLM client retries up to 4 times with exponential backoff and rotates through fallback models automatically, but a completely invalid key will still fail.

**Database reset**

Delete the SQLite file and restart — the schema is recreated automatically:
```bash
cd backend && del polymarket_ai.db   # Windows
# rm polymarket_ai.db               # Mac/Linux
python -m uvicorn main:app --reload --port 8000
```

---

## Road to Live Trading

The system is designed to graduate from paper trading to real money in phases. Do not skip steps.

1. **Paper trade for at least 50 resolved trades** — 12 trades is not a statistically meaningful sample
2. **Add search API keys** — the research agent needs real-time data to have genuine edge
3. **Validate calibration error drops below 15%** — current 22% means estimates are off by that much on average
4. **Implement slippage + fee modelling** — paper results are optimistic without it
5. **Create a Polymarket wallet and fund with $10 maximum** — prove real execution matches paper results
6. **Scale up only after 20+ profitable live trades at each level**

The infrastructure is production-ready. The edge is still being built.
