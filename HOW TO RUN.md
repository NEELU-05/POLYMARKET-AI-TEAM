# How to Run — Polymarket AI Team

## Prerequisites

- **Python 3.11+** installed (avoid 3.14, use 3.11 or 3.12)
- **Node.js 18+** installed (for the dashboard)
- **OpenRouter API Key** (already configured in `backend/.env`)

---

## Quick Start (3 Steps)

### Step 1: Start the Backend Server

Open a terminal and run:

```bash
cd backend
pip install -r requirements.txt
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

You should see:

```
INFO:     Uvicorn running on http://0.0.0.0:8000
```

Verify it works: open http://localhost:8000/health in your browser. You should see `{"status":"ok"}`.

### Step 2: Start the Frontend Dashboard

Open a **second terminal** and run:

```bash
cd frontend
npm install
npm run dev
```

You should see:

```
- Local: http://localhost:3000
```

**Or** just double-click `START WEBSITE.bat` in the project root — it starts the frontend and opens your browser automatically.

### Step 3: Start the AI System

1. Open http://localhost:3000 in your browser
2. Look at the bottom-left sidebar — you'll see a green **Start System** button
3. Click **Start System**
4. The status will change to **Running** with a pulsing green dot
5. The AI pipeline will begin scanning real Polymarket markets

To stop: click the **Stop System** button (same location).

---

## What Happens When You Click Start

The system runs a continuous loop every 30 minutes:

```
Scan Markets → Classify → Research → Signals → Probability → Strategy → Risk Check → Execute (Paper)
```

1. **Market Scanner** — Fetches active markets from Polymarket's Gamma API
2. **Market Classifier** — Ranks markets by category and tradability
3. **Research Agent** — Gathers news and context using Serper/News APIs
4. **Signal Agent** — Extracts bullish/bearish signals
5. **Probability Agent** — Estimates true probability using LLM
6. **Strategy Agent** — Compares AI probability vs market price, calculates edge
7. **Risk Manager** — Enforces position limits, drawdown checks, Kelly sizing
8. **Execution Agent** — Places paper trades (no real money)

Every 60 minutes, a **Reflection Cycle** checks resolved markets and logs lessons learned.

---

## Dashboard Pages

| Page              | URL          | What It Shows                    |
| ----------------- | ------------ | -------------------------------- |
| Dashboard         | `/`          | Balance, PnL, ROI, equity curve  |
| Trade History     | `/trades`    | All paper trades with reasoning  |
| Active Positions  | `/positions` | Currently open positions         |
| Agent Activity    | `/agents`    | What each AI agent is doing      |
| Learning / Memory | `/memory`    | Lessons learned from past trades |

---

## Configuration

All settings are in `backend/.env`:

| Setting                             | Default                                | Description                               |
| ----------------------------------- | -------------------------------------- | ----------------------------------------- |
| `OPENROUTER_API_KEY`                | (your key)                             | LLM API key via OpenRouter                |
| `LLM_MODEL`                         | `stepfun/step-3.5-flash:free`          | AI model (free tier)                      |
| `DATABASE_URL`                      | `sqlite+aiosqlite:///polymarket_ai.db` | Database (SQLite for dev)                 |
| `STARTING_CAPITAL`                  | `500.0`                                | Paper trading starting balance (₹)        |
| `MAX_TRADE_SIZE`                    | `30.0`                                 | Max single trade size                     |
| `MAX_OPEN_TRADES`                   | `5`                                    | Max concurrent positions                  |
| `MIN_EDGE`                          | `0.08`                                 | Minimum 8% edge required to trade         |
| `EMERGENCY_BALANCE`                 | `350.0`                                | Reduce position sizes below this          |
| `STOP_BALANCE`                      | `300.0`                                | Stop trading below this (circuit breaker) |
| `SCAN_INTERVAL_MINUTES`             | `30`                                   | How often to scan for new markets         |
| `RESOLUTION_CHECK_INTERVAL_MINUTES` | `60`                                   | How often to check resolved markets       |

---

## API Endpoints (for advanced use)

The backend exposes these endpoints at http://localhost:8000:

| Method | Endpoint                | Description                         |
| ------ | ----------------------- | ----------------------------------- |
| GET    | `/health`               | Health check                        |
| GET    | `/api/dashboard`        | Dashboard metrics                   |
| GET    | `/api/trades`           | Trade history                       |
| GET    | `/api/trades/active`    | Open positions                      |
| GET    | `/api/agents/activity`  | Agent logs                          |
| GET    | `/api/agents/status`    | Agent health                        |
| GET    | `/api/lessons`          | Lessons learned                     |
| GET    | `/api/memory/summary`   | Memory state                        |
| GET    | `/api/events`           | Event bus history                   |
| GET    | `/api/system/status`    | System running status               |
| POST   | `/api/system/start`     | Start the AI pipeline               |
| POST   | `/api/system/stop`      | Stop the AI pipeline                |
| POST   | `/api/pipeline/run`     | Manually trigger one pipeline cycle |
| POST   | `/api/pipeline/reflect` | Manually trigger reflection cycle   |

---

## Troubleshooting

### "No module named uvicorn"

```bash
cd backend
pip install -r requirements.txt
```

### Backend won't start / import errors

Make sure you're running from the `backend/` directory:

```bash
cd backend
python -m uvicorn main:app --reload --port 8000
```

### Dashboard shows "Connecting..." / "Start System" button is greyed out

The backend isn't running. Start the backend first (Step 1), then refresh the dashboard.

### LLM not responding / pipeline hangs

Check your OpenRouter API key in `backend/.env`. Visit https://openrouter.ai/keys to verify your key is active and has credits.

### Database reset

Delete the SQLite file and restart the backend — it auto-creates a fresh one:

```bash
cd backend
del polymarket_ai.db
python -m uvicorn main:app --reload --port 8000
```

---

## Project Structure

```
POLYMARKET AI TEAM/
├── START WEBSITE.bat          # Double-click to open dashboard
├── HOW TO RUN.md              # This file
├── backend/
│   ├── .env                   # Configuration (API keys, settings)
│   ├── main.py                # FastAPI server entry point
│   ├── requirements.txt       # Python dependencies
│   └── app/
│       ├── agents/            # 11 AI agents (scanner, classifier, etc.)
│       ├── api/routes.py      # REST API endpoints
│       ├── core/              # Config, logging, LLM client, event bus
│       ├── db/                # Database setup (SQLite)
│       ├── models/            # SQLAlchemy models + Pydantic schemas
│       ├── services/          # Orchestrator, scheduler, Polymarket API
│       └── trading/           # Paper trading simulator
└── frontend/
    ├── package.json           # Node.js dependencies
    ├── app/                   # Next.js pages
    ├── components/            # React components (Sidebar, charts, etc.)
    └── services/api.ts        # API client for backend
```

---

## Safety Features

- **Paper trading only** — no real money is ever used
- **₹500 starting capital** with circuit breakers
- **25% drawdown protection** — stops trading at ₹300
- **Emergency mode** — reduces position sizes at ₹350
- **Max 5 open trades**, max ₹30 per trade
- **8% minimum edge** — only trades when AI sees clear value
