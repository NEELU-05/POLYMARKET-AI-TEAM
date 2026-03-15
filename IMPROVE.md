# Improvement Roadmap — Polymarket AI Team

## Priority Levels

- **P0 — CRITICAL**: Security risk, fix immediately
- **P1 — HIGH**: Causes failures or significantly limits performance
- **P2 — MEDIUM**: Improves reliability/accuracy, should be done before production
- **P3 — LOW**: Nice to have, quality of life improvements

---

## P0 — CRITICAL (Fix First)

### 1. Add API Authentication
**File:** `backend/app/api/routes.py`
**Problem:** All endpoints (including `POST /api/system/start`, `POST /api/pipeline/run`) are completely open. Anyone on the network can start/stop the system or trigger unlimited pipeline runs.
**Fix:** Add API key authentication middleware. At minimum, require a `Bearer` token header on all POST endpoints.

---

## P1 — HIGH (Fix Before Running Seriously)

### 2. Add LLM Retry Logic with Exponential Backoff
**File:** `backend/app/core/llm_client.py` (line 60-74)
**Problem:** A single 429/500/503 from OpenRouter kills the entire analysis for that market. The pipeline logs show `llm_empty_response` warnings — these are unrecoverable failures.
**Fix:** Add 3 retries with exponential backoff (1s → 2s → 4s) + jitter. Use `tenacity` library or manual retry loop.

### 3. Add LLM Rate Limiting
**File:** `backend/app/core/llm_client.py` (line 30-66)
**Problem:** The classifier calls the LLM in a tight loop for 15+ markets. Free-tier models rate-limit aggressively, causing empty responses.
**Fix:** Add an `asyncio.Semaphore(3)` to cap concurrent LLM calls, and a 1-second delay between requests.

### 4. Parallelize Market Analysis in Orchestrator
**File:** `backend/app/services/orchestrator.py` (line 69-88)
**Problem:** Markets are analyzed one at a time: research → signal → probability, sequentially for each market. 10 markets × 3 LLM calls = 30 serial API calls (takes ~10 minutes).
**Fix:** Use `asyncio.gather()` with a semaphore to process 3-5 markets concurrently. Would cut pipeline time from ~10 minutes to ~3 minutes.

### 5. Add Pipeline Timeout
**File:** `backend/app/services/orchestrator.py` (line 28-131)
**Problem:** No timeout on `run_full_pipeline()`. If an LLM call hangs, the pipeline runs forever.
**Fix:** Wrap in `asyncio.wait_for(pipeline, timeout=600)` (10 min max).

### 6. Wire External Data Sources into Research Agent
**File:** `backend/app/agents/research_agent.py`
**Problem:** The research agent relies entirely on the LLM's pre-training knowledge. Serper and News API keys are configured but never used. The AI cannot research current events.
**Fix:**
- Add `serper_api_key` and `news_api_key` to `config.py`
- Create a `search_service.py` that calls Serper for web results and News API for headlines
- Feed real search results into the research agent's LLM prompt

### 7. Call `timed_run()` Instead of `run()` on Agents
**File:** `backend/app/services/orchestrator.py`
**Problem:** `BaseAgent` provides `timed_run()` that automatically logs agent activity to the database (duration, status, errors). But the orchestrator calls `agent.run()` directly everywhere, so the Agent Activity page in the dashboard is always empty.
**Fix:** Replace all `agent.run(...)` calls with `agent.timed_run(...)` in the orchestrator.

### 8. Fix Resolution Detection
**File:** `backend/app/services/polymarket.py` (line 191)
**Problem:** Uses `yes_price > 0.9` as a proxy for resolution outcome. A market at 0.85 YES after resolution would be misclassified, causing wrong PnL calculations.
**Fix:** Use the `resolutionSource` or `winningOutcome` field from the Gamma API response instead of price heuristics.

### 9. Add Slippage Modeling to Paper Trading
**File:** `backend/app/trading/simulator.py` (line 86-120)
**Problem:** Trades execute at exact market price. Real Polymarket has a spread and market impact. Paper trading results will be unrealistically optimistic.
**Fix:** Add configurable slippage (e.g., 1-2%) subtracted from entry/exit prices.

### 10. Make Pipeline Trigger Non-Blocking
**File:** `backend/app/api/routes.py` (line 244-251)
**Problem:** `POST /api/pipeline/run` runs the full pipeline synchronously in the HTTP handler. Long pipelines (~10 min) will timeout.
**Fix:** Launch as a `BackgroundTask` and return a `pipeline_id`. Add `GET /api/pipeline/{id}/status` for polling.

### 11. Add Pipeline Idempotency Guard
**File:** `backend/app/api/routes.py` (line 244-251)
**Problem:** Calling `POST /api/pipeline/run` twice starts two pipelines in parallel, potentially opening duplicate positions on the same market.
**Fix:** Add a lock. If a pipeline is already running, return `409 Conflict`.

### 12. Write Tests
**Location:** `backend/tests/`
**Problem:** Zero tests exist. No way to verify agents work correctly or catch regressions.
**Fix:** Priority test targets:
- `test_llm_client.py` — mock OpenRouter, test retry + parse logic
- `test_simulator.py` — test balance, PnL, edge cases
- `test_risk_manager.py` — test position limits, drawdown circuit breaker
- `test_polymarket.py` — mock API responses, test price parsing

---

## P2 — MEDIUM (Before Production)

### 13. Reuse httpx Clients (Connection Pooling)
**Files:** `llm_client.py` (line 61), `polymarket.py` (all methods)
**Problem:** Every API call creates and destroys a new `httpx.AsyncClient`. This prevents HTTP/2 connection reuse, keep-alive, and adds latency.
**Fix:** Create a persistent `self._client` in `__init__` and close it in a `shutdown()` method.

### 14. Add Response Caching
**Files:** `llm_client.py`, `polymarket.py`
**Problem:** Identical markets get re-analyzed every 30 minutes. Same Polymarket data fetched repeatedly.
**Fix:**
- LLM: Cache responses keyed on `hash(system_prompt + user_prompt)` with 30-min TTL
- Polymarket: Cache `fetch_active_markets` for 5-10 minutes

### 15. Pass Memory Context to Agents
**File:** `backend/app/services/orchestrator.py` (line 67)
**Problem:** `memory = await memory_manager.run(db)` is called but `memory` is never passed to any agent. Past lessons are collected but never used.
**Fix:** Pass `memory` to the research, signal, and probability agents so they can learn from past mistakes.

### 16. Prevent Duplicate Positions
**File:** `backend/app/agents/risk_manager.py`
**Problem:** The risk manager does not check if there's already an open position on the same `condition_id`. Can open duplicate bets on the same market.
**Fix:** Query `Trade` table for open trades with matching `condition_id` before approving.

### 17. Add Daily Trade Limit
**File:** `backend/app/trading/simulator.py` (line 63-79)
**Problem:** The design says "max 5 daily trades" but there is no enforcement anywhere.
**Fix:** Add `daily_trade_limit` to config. In `can_trade()`, count today's trades and reject if limit reached.

### 18. Add Position Size as Percentage of Capital
**File:** `backend/app/trading/simulator.py`
**Problem:** The design says "max position: 15%" but the code only enforces an absolute `max_trade_size` ($30). With ₹500 capital, 15% = ₹75, so this isn't currently an issue, but after profits it could be.
**Fix:** Add `max_position_pct` to config and check in `can_trade()`.

### 19. Add Transaction Fee Modeling
**File:** `backend/app/trading/simulator.py`
**Problem:** Polymarket has maker/taker fees. Paper trading ignores them, making results unrealistically profitable.
**Fix:** Add `fee_pct` to config (default 2%). Subtract from PnL on trade closure.

### 20. Batch Market Classification
**File:** `backend/app/agents/market_classifier.py` (line 30-56)
**Problem:** Calls the LLM once per market (15 calls). Could batch 5-10 markets into a single prompt.
**Fix:** Group markets and classify in batches of 5. Reduces LLM calls from 15 to 3.

### 21. Add Database Indexes
**File:** `backend/app/models/db_models.py`
**Problem:** No indexes on frequently queried columns.
**Fix:** Add indexes:
```python
# Trade table
Index("ix_trade_status", Trade.status)
Index("ix_trade_opened_at", Trade.opened_at)
Index("ix_trade_condition_status", Trade.condition_id, Trade.status)

# PortfolioSnapshot table
Index("ix_snapshot_timestamp", PortfolioSnapshot.timestamp)

# LessonLearned table
Index("ix_lesson_created", LessonLearned.created_at)
```

### 22. Add Market Deduplication Across Cycles
**File:** `backend/app/services/orchestrator.py`
**Problem:** Markets are re-analyzed from scratch every 30 minutes even if nothing changed.
**Fix:** Store `last_analyzed_at` per `condition_id` in `MarketRecord`. Skip markets analyzed within the last hour unless price moved significantly.

### 23. Add Missing Trade Fields to Database
**File:** `backend/app/models/db_models.py` (line 49-70)
**Problem:** `Trade` table lacks `fees`, `slippage`, `kelly_fraction` — cannot audit sizing decisions.
**Fix:** Add columns: `fees: Float`, `slippage: Float`, `kelly_fraction: Float`.

### 24. Add Input Validation on API Limits
**File:** `backend/app/api/routes.py` (line 72, 152, 199)
**Problem:** Client can pass `limit=999999` and load the entire database into memory.
**Fix:** Add `limit = min(limit, 100)` at the top of each paginated endpoint.

### 25. Add Frontend Error Boundaries
**Location:** `frontend/app/layout.tsx`
**Problem:** If any component throws, the whole app crashes with no recovery.
**Fix:** Wrap pages in React error boundaries with "Something went wrong" fallback.

### 26. Add Database Migrations (Alembic)
**File:** `backend/app/db/database.py` (line 73-78)
**Problem:** Uses `Base.metadata.create_all()` which cannot handle schema changes. If you add a column, existing databases don't get updated.
**Fix:** Set up Alembic with auto-generate migrations.

---

## P3 — LOW (Nice to Have)

### 27. Add Scheduler Error Recovery with Backoff
**File:** `backend/app/services/scheduler.py`
If a pipeline cycle fails, add exponential backoff before retrying. Add a circuit breaker after 3 consecutive failures.

### 28. Add Settings Page to Dashboard
**Location:** `frontend/app/settings/page.tsx`
View and modify system configuration (starting capital, min edge, max trade size, scan interval) from the UI.

### 29. Add Markets Page to Dashboard
**Location:** `frontend/app/markets/page.tsx`
Browse currently scanned markets, see classification results, view research/signal/probability outputs per market.

### 30. Add Trade Detail View
**Location:** `frontend/app/trades/[id]/page.tsx`
Click a trade to see full reasoning, entry/exit details, linked lessons, and market context.

### 31. Add Pagination to Trade History
**File:** `frontend/app/trades/page.tsx`
Only 50 trades are loaded. Add "Load More" or page controls.

### 32. Add WebSocket/SSE for Real-Time Updates
**Problem:** Frontend polls 5 different endpoints every 5-30 seconds.
**Fix:** Add a single WebSocket connection. Push events from the event bus to connected clients.

### 33. Add Max-Cycles Option to Scheduler
**File:** `backend/app/services/scheduler.py`
Add a `max_cycles` parameter so you can say "run 5 cycles and stop." Useful for testing.

### 34. Add Cycle Timing Metrics
**File:** `backend/app/services/scheduler.py`
Track how long each cycle takes. Add `last_cycle_duration_ms` to `get_status()` response.

### 35. Make Config Values Dynamic from Dashboard
Hardcoded values in frontend:
- `page.tsx` line 86: Starting capital shows `500` instead of API value
- `page.tsx` line 182: Model name shows static string instead of `llm_stats`

### 36. Add `.env.example`
**Location:** Project root
New developers don't know which environment variables are required. Create an `.env.example` with all variables and descriptions.

### 37. Add `aiosqlite` to `requirements.txt`
**File:** `backend/requirements.txt`
The `.env` uses SQLite but `aiosqlite` is not listed as a dependency.

### 38. Optimize Balance Calculation
**File:** `backend/app/trading/simulator.py` (line 48-51)
`_compute_balance` loads ALL closed trades into memory. Use `SELECT SUM(pnl)` instead.

### 39. Reduce Redundant Portfolio Snapshots
**File:** `backend/app/agents/portfolio_manager.py` (line 67-78)
Creates a new snapshot every time `run()` is called (multiple times per cycle). Save only once at end of cycle.

### 40. Make Orchestrator Limits Configurable
**File:** `backend/app/services/orchestrator.py` (line 69, 105)
`[:10]` markets and `[:3]` trades per cycle are hardcoded magic numbers. Move to `config.py`.

---

## Implementation Order (Recommended)

**Week 1 — Stability:**
1. API Authentication (#1)
2. LLM retry + rate limiting (#2, #3)
3. Pipeline timeout + idempotency guard (#5, #11)
4. Fix `timed_run()` for agent activity tracking (#7)

**Week 2 — Accuracy:**
5. Wire Serper/News API into research agent (#6)
6. Fix resolution detection (#8)
7. Add slippage + fees to paper trading (#9, #19)
8. Prevent duplicate positions (#16)

**Week 3 — Performance:**
9. Parallelize market analysis (#4)
10. Reuse httpx clients (#13)
11. Batch market classification (#20)
12. Add database indexes (#21)

**Week 4 — Polish:**
13. Write tests (#12)
14. Add response caching (#14)
15. Pass memory to agents (#15)
16. Frontend improvements (#28-35)

---

## Quick Wins (< 30 minutes each)

| # | Task | Impact |
|---|------|--------|
| 7 | Change `agent.run()` to `agent.timed_run()` in orchestrator | Agent Activity page starts working |
| 24 | Add `limit = min(limit, 100)` to API routes | Prevents memory bomb |
| 37 | Add `aiosqlite` to requirements.txt | Fixes install for new users |
| 40 | Move `[:10]` and `[:3]` to config | Makes limits adjustable |
| 36 | Create `.env.example` | Helps new developers |
