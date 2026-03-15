# PLAN.md — The Roadmap From Paper Profits to Real Money

> **Current status:** Paper trading with 91.7% win rate, +₹428 PnL, 85.6% ROI.
> **The goal:** Turn this into real, withdrawable profit on Polymarket.
>
> This plan is organized as a checklist. Do each step in order.
> Every step has a **WHY**, **WHAT**, and **HOW LONG**.

---

## WHERE YOU ARE RIGHT NOW

```
┌─────────────────────────────────────────────┐
│            PAPER TRADING RESULTS            │
├──────────────────────┬──────────────────────┤
│ Starting Capital     │ ₹500                 │
│ Current Balance      │ ₹838.07              │
│ Total PnL            │ +₹428.07             │
│ ROI                  │ +85.6%               │
│ Win Rate             │ 91.7% (11/12)        │
│ Open Positions       │ 3                    │
│ Max Drawdown         │ 4.87%                │
│ Avg Edge             │ 27.41%               │
│ LLM Calls            │ 190 (14s avg)        │
│ Calibration Error    │ 0.22                 │
└──────────────────────┴──────────────────────┘

HONEST ASSESSMENT:
  ✅ Win rate is excellent (91.7%)
  ✅ Risk management works (4.87% max drawdown)
  ✅ Kelly sizing is conservative and safe
  ⚠️  Only 12 trades — too small a sample to trust
  ⚠️  Edge (27%) is suspiciously high — may be lucky markets
  ⚠️  Calibration error (0.22) means AI is off by ~22% on average
  ❌ No real-time data — all analysis is LLM guessing
  ❌ No slippage/fee modeling — real trades cost more
  ❌ No API auth — system is open to anyone on network
```

---

## PHASE 1: HARDEN THE SYSTEM (Week 1)

> Make the system reliable enough to trust with real money.

### Step 1.1 — Add API Authentication

- [x] Create API key middleware on all POST endpoints
- **Why:** Anyone on your network can start/stop trades
- **File:** `backend/app/api/routes.py`
- **How long:** 30 minutes
- **Status:** ✅ COMPLETED — All POST endpoints secured with Bearer token auth
- **How:**
  ```
  1. Add API_SECRET_KEY to .env
  2. Add a dependency that checks Authorization header
  3. Apply to all POST endpoints (/system/start, /pipeline/run, etc.)
  4. Frontend sends the key in headers
  ```

### Step 1.2 — Add LLM Retry with Backoff

- [x] Retry failed LLM calls 3 times with exponential backoff
- **Why:** Free model rate-limits aggressively → kills entire analysis
- **File:** `backend/app/core/llm_client.py`
- **How long:** 30 minutes
- **Status:** ✅ COMPLETED — 3 retries with exponential backoff (1s→2s→4s→8s) + rate limiter (max 5 calls/min)
- **How:**
  ```
  1. pip install tenacity
  2. Wrap the httpx.post call in @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
  3. Add rate limiter: max 5 LLM calls per minute for free tier
  ```

### Step 1.3 — Add Pipeline Timeout

- [x] Kill pipeline runs that take longer than 10 minutes
- **Why:** Hung LLM calls can block the entire system forever
- **File:** `backend/app/agents/orchestrator.py`
- **How long:** 15 minutes
- **Status:** ✅ COMPLETED — 10-minute timeout with asyncio.wait_for, returns partial results on timeout
- **How:**
  ```
  1. Wrap the full pipeline in asyncio.wait_for(timeout=600)
  2. Catch TimeoutError, log it, return partial results
  ```

### Step 1.4 — Fix Resolution Detection Bug

- [x] Use actual API `resolution` field instead of `yes_price > 0.9`
- **Why:** Incorrectly closing trades = losing money you should have kept
- **File:** `backend/app/services/polymarket.py` (line ~191)
- **How long:** 15 minutes
- **Status:** ✅ COMPLETED — Now uses API winningSide + resolutionSource fields

### Step 1.5 — Run 50 More Paper Trades

- [ ] Let the system run for 3-5 days continuously
- **Why:** 12 trades is too small to trust. Need 50+ to confirm the edge is real.
- **Target:** If win rate stays >60% and PnL stays positive after 50 trades → move to Phase 2
- **How long:** 3-5 days (automated)
- **Status:** 🔄 IN PROGRESS — Scheduler now runs every 1 minute (changed from 30) to accelerate testing

---

## PHASE 2: ADD REAL DATA (Week 2)

> Give the AI actual information instead of hallucinations.

### Step 2.1 — Build Search Service (Serper + News API)

- [x] Create `backend/app/services/search_service.py`
- **Why:** The #1 reason the system can earn money — real-time news
- **How long:** 2 hours
- **Status:** ✅ COMPLETED — Search service created with Serper + News API integration, graceful fallback if keys missing
- **Implementation:**
  - `web_search(query)` → Serper API for web results
  - `news_search(query)` → News API for headlines
  - `search(query)` → Combined search (both sources)
- **How:**
  ```
  1. Add serper_api_key and news_api_key to config.py
  2. Create search_service.py with two functions:
     - web_search(query) → calls Serper API, returns top 5 results
     - news_search(query) → calls News API, returns top 5 headlines
  3. Both return title + snippet + date for each result
  ```

### Step 2.2 — Wire Search into Research Agent

- [x] Pass real news into the research agent prompt
- **Why:** LLM goes from guessing to analyzing real information
- **File:** `backend/app/agents/research_agent.py`
- **How long:** 1 hour
- **Status:** ✅ COMPLETED — Research agent now fetches real-time news + web data and injects into LLM prompts
- **Implementation:**
  - Calls `search_service.search()` automatically for each market
  - Formats results into readable text with source/date info
  - Injects into user prompt: "Based on this real-time data, provide your analysis"
- **How:**
  ```
  1. Extract keywords from market question
  2. Call search_service.web_search(keywords)
  3. Call search_service.news_search(keywords)
  4. Add to user_prompt:
     "Recent News (last 24 hours):
      1. [headline] - [source] - [date]
      2. [headline] - [source] - [date]
      ...
      Based on this real information, analyze the market."
  ```

### Step 2.3 — Use Price Timeseries (Real Momentum)

- [x] Call `fetch_market_timeseries()` in the signal agent
- **Why:** Replace fake momentum with actual price movement data
- **File:** `backend/app/agents/signal_agent.py`
- **How long:** 1-2 hours
- **Status:** ✅ COMPLETED — Signal agent now fetches real timeseries, computes 1h/6h/24h/7d momentum + trend direction
- **Implementation:**
  - Added `token_id` field to MarketData schema (parsed from Gamma API `clobTokenIds`)
  - Signal agent calls `polymarket_service.fetch_market_timeseries(token_id)`
  - `_compute_momentum()` calculates price changes at 1h, 6h, 24h, 7d windows
  - Real momentum data injected into LLM prompt with trend direction
- **How:**
  ```
  1. In orchestrator, call polymarket.fetch_market_timeseries(token_id)
  2. Calculate: price_1h_ago, price_6h_ago, price_24h_ago
  3. Compute momentum = (current_price - price_24h_ago) / price_24h_ago
  4. Pass these real numbers into signal agent prompt
  5. Also pass raw price chart data points to the LLM
  ```

### Step 2.4 — Use Orderbook Data

- [x] Fetch live bids/asks before trading
- **Why:** Know the real spread and avoid expensive markets
- **File:** `backend/app/agents/execution_agent.py`
- **How long:** 1 hour
- **Status:** ✅ COMPLETED — Execution agent fetches orderbook, calculates spread + fill price, skips if spread > 5 cents
- **Implementation:**
  - `_analyze_orderbook()` walks order levels to simulate fill price
  - Skips trades with spread > 0.05 (5 cents) — too expensive
  - Uses real fill price from orderbook instead of midpoint
  - Graceful fallback if no orderbook data available
- **How:**
  ```
  1. Call polymarket.fetch_orderbook(token_id) before execution
  2. Calculate spread = best_ask - best_bid
  3. If spread > 0.05 (5 cents), skip the trade
  4. Calculate fill price based on order depth vs trade size
  5. Use real fill price instead of midpoint
  ```

### Step 2.5 — Volume Spike Detection

- [x] Detect unusual trading activity
- **Why:** Smart money moves before news breaks publicly
- **File:** `backend/app/agents/signal_agent.py`
- **How long:** 1 hour
- **Status:** ✅ COMPLETED — Signal agent fetches last 50 trades, detects 2x+ volume spikes, alerts LLM
- **Implementation:**
  - `_detect_volume_spike()` computes avg vs recent trade size ratio
  - Flags spike when recent avg > 2x overall avg
  - Spike data (ratio, avg sizes) injected into LLM prompt
  - "VOLUME SPIKE DETECTED" warning when smart money may be moving
- **How:**
  ```
  1. Call polymarket.fetch_market_trades(condition_id, limit=50)
  2. Calculate avg trade size and frequency
  3. Flag if recent volume > 2x normal
  4. Add "volume_spike: true/false" to signal output
  5. Volume spike + news confirmation = high-confidence trade
  ```

---

## PHASE 3: CLOSE THE LEARNING LOOP (Week 3)

> Make the system smarter with every trade.

### Step 3.1 — Feed Lessons Back to Agents

- [x] Load past lessons and inject into analysis prompts
- **Why:** System repeats the same mistakes forever without this
- **Files:** `research_agent.py`, `probability_agent.py`, `orchestrator.py`
- **How long:** 2 hours
- **Status:** ✅ COMPLETED — Orchestrator loads 20 recent lessons + calibration data, passes to research and probability agents
- **Implementation:**
  - `memory_manager.get_lessons_for_prompt(db)` fetches last 20 lessons with severity/category
  - `memory_manager.get_calibration_data(db)` computes per-category win rate, avg error, bias direction
  - Research agent: `_format_lessons()` injects lessons as "LESSONS FROM PAST TRADES" bullet points
  - Probability agent: `_format_calibration()` injects calibration history with bias warnings
  - Orchestrator passes `lessons=lessons` to research agent & `calibration=calibration` to probability agent
- **How:**
  ```
  1. In orchestrator, before analysis: load last 20 lessons from DB
  2. Format as bullet points
  3. Add to research_agent system prompt:
     "LESSONS FROM PAST TRADES (apply these):
      - [lesson 1]
      - [lesson 2]"
  4. Add to probability_agent system prompt:
     "YOUR CALIBRATION HISTORY:
      - Average error: 22%
      - You overestimate by [X]% on [category]
      - Adjust your estimates accordingly"
  ```

### Step 3.2 — Track Calibration by Category

- [x] Log AI probability vs actual outcome per market category
- **Why:** Know which categories you're good at and which to avoid
- **How long:** 1 hour
- **Status:** ✅ COMPLETED — `get_calibration_data()` computes per-category win rate, avg error, bias from closed trades
- **Implementation:**
  - `memory_manager.get_calibration_data(db)` iterates closed trades and computes: overall avg error, bias direction, per-category stats
  - Reflection agent now stores actual market category (crypto/politics/etc.) instead of "yes"/"no" in LessonLearned
  - Categories with ≥3 trades get reported; fewer are excluded as insufficient data
  - Bias classified as: "overestimates YES" / "overestimates NO" / "well-calibrated" (threshold ±5%)
- **How:**
  ```
  1. After each trade closes, save: category, ai_probability, outcome
  2. Calculate per-category: avg_error, win_rate, bias_direction
  3. Store in DB or CSV
  4. Use to auto-filter: skip categories with <50% win rate
  ```

### Step 3.3 — Add Market Description to Signal Agent

- [x] The signal agent currently never sees the market description
- **Why:** Missing crucial context → worse signals
- **File:** `backend/app/agents/signal_agent.py`
- **How long:** 5 minutes
- **Status:** ✅ COMPLETED — Description added to signal agent prompt (done as part of Step 2.3 rewrite)

### Step 3.4 — Store Bull/Bear Cases

- [x] The research agent asks for bull_case and bear_case but never saves them
- **Why:** Useful context for downstream agents gets thrown away
- **Files:** `research_agent.py`, `models/schemas.py`
- **How long:** 15 minutes
- **Status:** ✅ COMPLETED — Added `bull_case` and `bear_case` fields to ResearchResult schema; research agent now stores them; probability agent reads them
- **Implementation:**
  - Added `bull_case: str = ""` and `bear_case: str = ""` to `ResearchResult` schema
  - Research agent stores `result.get("bull_case")` and `result.get("bear_case")` from LLM response
  - Probability agent includes bull/bear cases in its prompt when available

### Step 3.5 — Run 50 More Trades with Real Data

- [ ] Validate that Phases 2-3 improvements actually help
- **Target:** Win rate still >60%, PnL positive, calibration error drops below 0.15
- **How long:** 3-5 days (automated)
- **Status:** 🔄 IN PROGRESS — System running with 1-minute intervals, collecting trades with all Phase 2+3 improvements active

---

## PHASE 4: ADD ADVANCED STRATEGIES (Week 4)

> New ways to find profitable trades.

### Step 4.1 — Resolution Timing Strategy

- [x] Target near-expiry markets with obvious outcomes
- **Why:** 2-5% profit on near-certain bets with almost zero risk
- **File:** `backend/app/agents/strategy_agent.py`
- **How long:** 2 hours
- **Status:** ✅ COMPLETED — Strategy agent now detects near-expiry (<48h) near-certain (>92% or <8%) markets, applies 2x position sizing, prioritizes in sort order
- **Implementation:**
  - `_check_resolution_timing()` checks: end_date within 48h + price >0.92 or <0.08 + confidence >0.7
  - Qualifying trades get 2x normal position size (capped at max_trade_size)
  - Resolution timing trades are sorted first (highest priority)
  - Reasoning tagged with `[RESOLUTION TIMING]` for tracking
  - Orchestrator passes full market data to strategy agent for end_date access
- **How:**
  ```
  1. Check if market ends within 48 hours
  2. Check if outcome is nearly certain (price > 0.92 or < 0.08)
  3. Cross-reference with real data (news, current values)
  4. These trades get 2x normal position size (high confidence)
  5. Expected return: 3-8% overnight
  ```

### Step 4.2 — Cross-Market Arbitrage Scanner

- [ ] Find logically inconsistent prices across related markets
- **Why:** Guaranteed profit — no prediction needed
- **File:** Create `backend/app/agents/arbitrage_agent.py`
- **How long:** 3-4 hours
- **How:**
  ```
  1. Use fetch_global_events() to find events with multiple markets
  2. For each event, check: do all outcome prices sum to ~1.0?
  3. If sum > 1.05 → buy NO on all (guaranteed profit)
  4. If sum < 0.95 → buy YES proportionally
  5. Also check: "X before June" vs "X before December" consistency
  ```

### Step 4.3 — Market Efficiency Filter

- [ ] Avoid markets where you can't win
- **Why:** High-volume crypto markets are priced by quant firms — you can't beat them
- **File:** `backend/app/agents/market_classifier.py`
- **How long:** 1 hour
- **How:**
  ```
  Prefer: Niche markets ($1K-$50K volume), near resolution (<14 days)
  Avoid: Crypto price markets, >$100K volume, >30 days to resolution
  Skip: Sports (free LLM has no sports knowledge)
  ```

### Step 4.4 — Slippage + Fee Modeling

- [ ] Model real trading costs
- **Why:** Your system thinks trades are free — they're not
- **File:** `backend/app/agents/strategy_agent.py`
- **How long:** 1 hour
- **How:**
  ```
  1. Estimate spread cost from orderbook (from Step 2.4)
  2. Add ~2% Polymarket fee on net profit
  3. New rule: only trade if edge > spread + fees + 3% buffer
  4. Recalculate Kelly using realistic expected returns
  ```

---

## PHASE 5: GO LIVE (Week 5-6)

> Move from paper trading to real money.

### Step 5.1 — Create Polymarket Wallet

- [ ] Set up a funded Polymarket account
- **How:**
  ```
  1. Go to polymarket.com
  2. Create account (requires crypto wallet)
  3. Deposit $10 USDC to start (₹830 at current rates)
  4. Note your wallet address and API credentials
  ```

### Step 5.2 — Implement Real Order Placement

- [ ] Replace paper trade simulator with actual CLOB API orders
- **Why:** This is where paper profits become real profits
- **File:** `backend/app/agents/execution_agent.py`
- **How long:** 3-4 hours
- **How:**
  ```
  1. Add Polymarket CLOB order API integration
  2. Place limit orders at bid price (not market orders)
  3. Monitor order fills
  4. Keep paper trading as a fallback/comparison mode
  5. Add a DRY_RUN=true/false toggle in .env
  ```

### Step 5.3 — Start with Micro-Trades

- [ ] First 2 weeks: max $2 per trade
- **Why:** Validate that paper results match real execution
- **Settings:**
  ```env
  MAX_TRADE_SIZE=2.0
  MAX_OPEN_TRADES=3
  MIN_EDGE=0.10
  STARTING_CAPITAL=10.0
  ```
- **Target:** Break even or small profit over 2 weeks
- **If losing:** Stop immediately, analyze what's different from paper trading

### Step 5.4 — Scale Up Gradually

- [ ] Increase trade size only after proven live results
- **Plan:**
  ```
  Week 1-2:  $2 trades, $10 capital  → prove it works
  Week 3-4:  $5 trades, $50 capital  → target $1-3/day
  Month 2:   $10 trades, $200 capital → target $5-10/day
  Month 3:   $15 trades, $500 capital → target $10-25/day
  ```
- **Rule:** Only increase after 20+ profitable trades at current level

---

## PHASE 6: OPTIMIZE (Month 2+)

> Squeeze out more profit from a proven system.

### Step 6.1 — Upgrade LLM Model

- [ ] Switch from free model to paid model for key decisions
- **When:** After earning $5+/day consistently
- **How:**
  ```env
  # Two-tier model system:
  LLM_MODEL_CHEAP=stepfun/step-3.5-flash:free        # for classification
  LLM_MODEL_SMART=google/gemini-2.0-flash-001         # for probability estimation
  ```
- **Cost:** ~$0.30/day for 30 analyses → worth it if earning $5+/day

### Step 6.2 — Event Calendar System

- [ ] Pre-identify scheduled events and trade them
- **Why:** Highest per-trade profit — event results are facts, not predictions
- **File:** Create `backend/app/services/event_calendar.py`
- **How long:** 3-4 hours

### Step 6.3 — Dynamic Position Sizing

- [ ] Adjust Kelly fraction based on actual track record per category
- **Why:** Bet more on categories where you're proven good
- **How:**
  ```
  Win rate > 70% in category → half-Kelly (0.5x)
  Win rate 55-70%             → quarter-Kelly (0.25x, current)
  Win rate < 55%              → eighth-Kelly (0.125x) or skip
  ```

### Step 6.4 — Portfolio Correlation Check

- [ ] Don't hold 3 positions that all depend on the same event
- **Why:** One bad event wipes out multiple positions
- **How long:** 1-2 hours

### Step 6.5 — Real-Time News Monitor

- [ ] Continuous news monitoring, not just at scan time
- **Why:** Breaking news during off-scan can invalidate open positions
- **How:** Background task that checks news every 5 min for open position keywords

---

## THE MASTER CHECKLIST

```
PHASE 1: HARDEN (Week 1)
  ✅ 1.1  API authentication
  ✅ 1.2  LLM retry + backoff
  ✅ 1.3  Pipeline timeout
  ✅ 1.4  Fix resolution detection
  🔄 1.5  Run 50 paper trades → validate win rate (1-min intervals now)

PHASE 2: REAL DATA (Week 2)
  ✅ 2.1  Build search_service.py (Serper + News API)
  ✅ 2.2  Wire news into research agent
  ✅ 2.3  Use price timeseries for real momentum
  ✅ 2.4  Use orderbook data for smart entry
  ✅ 2.5  Volume spike detection

PHASE 3: LEARNING LOOP (Week 3)
  ✅ 3.1  Feed lessons back to agents
  ✅ 3.2  Track calibration by category
  ✅ 3.3  Add description to signal agent
  ✅ 3.4  Store bull/bear cases
  🔄 3.5  Run 50 more trades → validate improvements

PHASE 4: ADVANCED STRATEGIES (Week 4)
  ✅ 4.1  Resolution timing strategy
  □ 4.2  Cross-market arbitrage scanner
  □ 4.3  Market efficiency filter
  □ 4.4  Slippage + fee modeling

PHASE 5: GO LIVE (Week 5-6)
  □ 5.1  Create Polymarket wallet
  □ 5.2  Implement real order placement
  □ 5.3  Start with $2 micro-trades
  □ 5.4  Scale up after 20+ profitable trades

PHASE 6: OPTIMIZE (Month 2+)
  □ 6.1  Upgrade to paid LLM model
  □ 6.2  Event calendar system
  □ 6.3  Dynamic position sizing
  □ 6.4  Portfolio correlation check
  □ 6.5  Real-time news monitor
```

---

## RULES THAT PROTECT YOUR MONEY

```
1. NEVER skip paper trading validation (Phase 1.5 and 3.5)
2. NEVER scale up after a winning streak — only after 20+ trades
3. NEVER invest money you can't afford to lose
4. ALWAYS start with $10 max, no matter how good paper results look
5. ALWAYS keep the circuit breakers active (stop at $300, emergency at $350)
6. IF live results are 10%+ worse than paper results → STOP and investigate
7. IF you lose 3 trades in a row → pause for 24 hours and review
8. NEVER disable dry-run mode without completing Phases 1-4
```

---

## INCOME PROJECTIONS (Conservative)

```
After Phase 2 (real data):
  Capital: $10  →  Expected: $0.50-1.00/day  →  $15-30/month

After Phase 4 (advanced):
  Capital: $50  →  Expected: $2-5/day  →  $60-150/month

After Phase 6 (optimized):
  Capital: $200 →  Expected: $5-15/day  →  $150-450/month

After 6 months (compounding):
  Capital: $500+→  Expected: $10-30/day →  $300-900/month
```

> These are conservative estimates assuming 55-65% win rate after real data is added.
> Your current 91.7% paper win rate will drop in live trading — expect 55-70% as realistic.
> The key to earning is NOT win rate — it's edge _ frequency _ capital.

---

## WHAT TO DO RIGHT NOW

```
Today:
  1. Read this plan
  2. Start with Step 1.1 (API auth) — 30 min
  3. Then Step 1.2 (LLM retry) — 30 min
  4. Then Step 1.4 (resolution fix) — 15 min
  5. Let the system run overnight (Step 1.5)

Tomorrow:
  6. Build search_service.py (Step 2.1) — 2 hours
  7. Wire it into research agent (Step 2.2) — 1 hour
  8. Let it run with real data for 24 hours

This week:
  9. Complete Phase 2 (Steps 2.3-2.5)
  10. Start Phase 3
  11. Count your paper trades — need 50+ before even thinking about real money
```

---

_Generated from live system analysis. Portfolio data as of 2026-03-14._
_System: 12 trades, 91.7% win rate, +₹428 PnL, ₹838 balance._
