# Polymarket AI Team — Setup Guide

## Prerequisites

- **Python 3.11+**
- **Node.js 18+** and npm
- **Docker** and Docker Compose (for PostgreSQL and Redis)
- **OpenRouter API key** (free tier works — using `stepfun/step-3.5-flash:free`)

---

## Quick Start

### 1. Start Infrastructure (PostgreSQL + Redis)

```bash
docker-compose up -d
```

This starts PostgreSQL (`localhost:5432`) and Redis (`localhost:6379`).

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Mac/Linux)
# source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env file from example
cp .env.example .env
```

Edit `backend/.env` and set your OpenRouter API key:

```
OPENROUTER_API_KEY=sk-or-v1-your-actual-key-here
```

### 3. Start the Backend

```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`.
Check health: `http://localhost:8000/health`

The backend will automatically:

- Create database tables on startup
- Start the pipeline scheduler (runs every 30 minutes)
- Start the reflection scheduler (runs every 60 minutes)

### 4. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

The dashboard will be at `http://localhost:3000`.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    ORCHESTRATOR                          │
│  scan → classify → research → signal → probability      │
│  → strategy → risk → execute → reflect                  │
└─────────────────────┬───────────────────────────────────┘
                      │
         ┌────────────┼────────────┐
         ▼            ▼            ▼
  ┌──────────┐ ┌──────────┐ ┌──────────┐
  │ Event Bus│ │ LLM      │ │ Paper    │
  │ (Redis)  │ │ (OpenR.) │ │ Trading  │
  └──────────┘ └──────────┘ └──────────┘
         │            │            │
         ▼            ▼            ▼
  ┌──────────────────────────────────────┐
  │         PostgreSQL Database          │
  │  markets | trades | snapshots |      │
  │  agent_activities | lessons_learned  │
  └──────────────────────────────────────┘
         │
         ▼
  ┌──────────────────────────────────────┐
  │     Next.js Dashboard (port 3000)    │
  │  Dashboard | Trades | Positions |    │
  │  Agent Activity | Learning/Memory    │
  └──────────────────────────────────────┘
```

## Agents

| Agent             | Role                                                         |
| ----------------- | ------------------------------------------------------------ |
| Market Scanner    | Fetches active markets from Polymarket Gamma API             |
| Market Classifier | Classifies markets by category (crypto, politics, etc.)      |
| Research Agent    | Analyzes events, extracts factors and bull/bear cases        |
| Signal Agent      | Generates composite trading signals                          |
| Probability Agent | Estimates true probability, independent of market price      |
| Strategy Agent    | Finds opportunities where AI prob ≠ market prob by ≥ 8%      |
| Risk Manager      | Applies survival protocol (capital limits, drawdown breaker) |
| Execution Agent   | Opens paper trades in the simulation wallet                  |
| Portfolio Manager | Tracks balance, PnL, ROI, drawdown                           |
| Reflection Agent  | Analyzes mistakes upon market resolution                     |
| Memory Manager    | Stores lessons for future decision-making                    |

## Survival Protocol

| Rule                     | Value          |
| ------------------------ | -------------- |
| Starting capital         | ₹500           |
| Max trade size           | ₹30            |
| Max open trades          | 5              |
| Min edge required        | 8%             |
| Emergency mode           | balance < ₹350 |
| Stop trading             | balance < ₹300 |
| Drawdown circuit breaker | 25%            |

## API Endpoints

| Method | Path                          | Description                |
| ------ | ----------------------------- | -------------------------- |
| GET    | `/health`                     | Health check               |
| GET    | `/api/dashboard`              | Dashboard overview         |
| GET    | `/api/dashboard/equity-curve` | Equity curve data          |
| GET    | `/api/trades`                 | Trade history              |
| GET    | `/api/trades/active`          | Open positions             |
| GET    | `/api/agents/activity`        | Agent activity log         |
| GET    | `/api/agents/status`          | Agent health status        |
| GET    | `/api/lessons`                | Lessons learned            |
| GET    | `/api/memory/summary`         | Memory aggregation         |
| GET    | `/api/events`                 | Event bus history          |
| POST   | `/api/pipeline/run`           | Trigger one pipeline cycle |
| POST   | `/api/pipeline/reflect`       | Trigger reflection cycle   |

## Manual Pipeline Trigger

From the dashboard, click **Run Pipeline** to manually trigger one analysis cycle.

Or via curl:

```bash
curl -X POST http://localhost:8000/api/pipeline/run
```

## Troubleshooting

- **Backend won't start**: Make sure PostgreSQL and Redis are running (`docker-compose ps`)
- **LLM errors**: Check your OpenRouter API key in `.env`
- **No trades appearing**: The system needs markets with ≥8% edge — this is conservative by design
- **Database errors**: Tables are auto-created on startup; if schema changes, restart the backend
