# Research Agent Improvement Plan

> Backend agent pipeline upgrades for the Polymarket AI Multi-Agent System.
> Current stack: Python 3.12, FastAPI, SQLAlchemy (async), OpenRouter LLM, httpx

---

## PROGRESS OVERVIEW

| Priority | Name                        | Status     |
| -------- | --------------------------- | ---------- |
| 1        | Research Depth & Concurrency| 🔜 Next    |
| 2        | Prompt Engineering Overhaul | 🔜 Planned |
| 3        | Signal Agent Intelligence   | 🔜 Planned |
| 4        | Probability Calibration     | 🔜 Planned |
| 5        | Memory & Learning Loop      | 🔜 Planned |
| 6        | Pipeline Orchestration      | 🔜 Planned |
| 7        | LLM Client Hardening       | 🔜 Planned |
| 8        | New Agents                  | 🔜 Planned |
| 9        | Observability & Debugging   | 🔜 Planned |

---

## CURRENT STATE

### Pipeline Flow
```
Scan → Research → Signal → Probability → Strategy → Risk → Execute → Reflect
```

### What Works
- 10 agents with clean `BaseAgent` class, event bus, structured logging
- Research agent fetches web + news via Serper / News API
- Signal agent reads real price timeseries + volume spikes
- Probability agent uses calibration history + base rates
- Strategy agent applies quarter-Kelly sizing + resolution timing
- Reflection agent learns from resolved trades → stores lessons
- Memory manager injects lessons into future prompts
- LLM client has dual-key rotation, model fallback, rate limiting

### What's Weak
- **Research is shallow** — 1 LLM call with 3 search results, no follow-up
- **No multi-source cross-validation** — single search query, no social media or on-chain data
- **Sequential market analysis** — 5 markets analyzed one-by-one (slow)
- **No chain-of-thought** — agents return flat JSON, no reasoning traces
- **Prompts are generic** — same prompt regardless of market category
- **Calibration is post-hoc only** — no real-time probability adjustment
- **No agent-to-agent debate** — single-pass pipeline, no adversarial checking
- **Memory is keyword-based** — no semantic similarity for lesson retrieval
- **No market lifecycle tracking** — can't detect odds-shifting or late-breaking events
- **No confidence decay** — old research treated same as fresh research

---

## PRIORITY 1: RESEARCH DEPTH & CONCURRENCY

### 1.1 — Multi-Query Research Strategy

**Problem:** Research agent sends 1 search query (the market question). Generic queries miss nuance.

**Solution:**
- LLM generates 3-4 targeted sub-queries per market:
  - Main event query
  - Key participant/entity query
  - Contrarian/opposing view query
  - Data/statistics query
- Run all sub-queries in parallel via `asyncio.gather`
- Deduplicate results by URL before passing to analysis

**Files:** `agents/research_agent.py`, `services/search_service.py`

### 1.2 — Concurrent Market Analysis

**Problem:** Pipeline analyzes 5 markets sequentially — each takes ~10s (3 LLM calls + search). Total: ~50s.

**Solution:**
- Use `asyncio.gather` with `asyncio.Semaphore(3)` to analyze 3 markets concurrently
- Reduces pipeline time from ~50s to ~20s
- Semaphore prevents overwhelming the LLM rate limit

**File:** `services/orchestrator.py`

### 1.3 — Research Depth Scaling

**Problem:** All markets get the same research depth regardless of edge size or confidence.

**Solution:**
- **Shallow pass** (1 search, 1 LLM call): Quick triage for all markets
- **Deep pass** (5 searches, 2 LLM calls): Only for markets where shallow pass finds edge > 5%
- Skip markets early if shallow research finds zero edge — saves LLM tokens

**File:** `agents/research_agent.py`, `services/orchestrator.py`

### 1.4 — Source Diversity Score

**Problem:** All 3 search results might come from the same source/perspective.

**Solution:**
- Track source domains across results
- Compute a diversity score (0-1): `unique_domains / total_results`
- Flag low-diversity research in the research result
- Penalize confidence when diversity is low

**File:** `agents/research_agent.py`

---

## PRIORITY 2: PROMPT ENGINEERING OVERHAUL

### 2.1 — Category-Specific System Prompts

**Problem:** Same generic prompt for crypto, politics, sports, weather. Each domain needs different reasoning.

**Solution:**
Create a prompt registry mapping categories to specialized prompts:
```python
CATEGORY_PROMPTS = {
    "crypto": "Focus on: on-chain metrics, whale wallet movements, ...",
    "politics": "Focus on: polling data, historical precedents, ...",
    "sports": "Focus on: injury reports, head-to-head stats, ...",
    "macro": "Focus on: central bank policy, yield curves, ...",
    "conflict": "Focus on: OSINT sources, satellite imagery reports, ...",
}
```
- Market classifier assigns category → research agent uses matched prompt
- Fallback to generic prompt for unknown categories

**Files:** `agents/research_agent.py`, `agents/market_classifier.py`

### 2.2 — Chain-of-Thought Reasoning

**Problem:** Agents return flat JSON — no visible reasoning chain. Hard to debug bad predictions.

**Solution:**
- Add `thinking` field to all agent JSON responses
- Require step-by-step reasoning before final answer
- Store thinking traces in the database for post-mortem analysis
- Prompt format:
```
Think step by step:
1. What is the base rate for this type of event?
2. What evidence supports YES? How strong?
3. What evidence supports NO? How strong?
4. What am I uncertain about?
5. Final probability estimate:
```

**Files:** All agent files, `models/schemas.py`

### 2.3 — Few-Shot Examples in Prompts

**Problem:** LLM calibration drifts without concrete examples of well-calibrated reasoning.

**Solution:**
- Include 2-3 few-shot examples in the probability estimation prompt
- Examples should cover: correct high-confidence call, correct low-confidence call, calibrated uncertainty
- Rotate examples from the agent's own past correct predictions (from DB)

**File:** `agents/probability_agent.py`, `agents/memory_manager.py`

### 2.4 — Adversarial Self-Check

**Problem:** Agents have confirmation bias — once they form a view, they don't challenge it.

**Solution:**
- After initial probability estimate, run a second LLM call:
  - "You estimated X% for YES. Now argue the OPPOSITE position as strongly as possible."
- Compare adversarial reasoning with original reasoning
- If adversarial case is compelling, reduce confidence by 20-30%

**File:** `agents/probability_agent.py`

---

## PRIORITY 3: SIGNAL AGENT INTELLIGENCE

### 3.1 — Order Book Depth Analysis

**Problem:** Signal agent looks at price + volume but not the order book shape.

**Solution:**
- Fetch order book from Polymarket CLOB API (`GET /book`)
- Compute: bid-ask spread, total bid depth vs ask depth, top-of-book imbalance
- Pass to LLM as structured data:
  ```
  Order Book: Bid depth $12,340 | Ask depth $8,200 | Spread 0.02
  Imbalance: 60% bid-heavy → buying pressure
  ```

**Files:** `services/polymarket.py`, `agents/signal_agent.py`

### 3.2 — Smart Money Detection

**Problem:** Volume spike detection uses average trade size — doesn't identify whale wallets.

**Solution:**
- Track large trades (>$500) separately
- Identify repeat large traders by wallet address
- Compute "whale consensus": if multiple large traders bet the same direction, boost signal
- Log whale trade patterns for future pattern recognition

**Files:** `agents/signal_agent.py`, `services/polymarket.py`

### 3.3 — Multi-Timeframe Momentum

**Problem:** Momentum analysis uses raw price change — doesn't detect acceleration or deceleration.

**Solution:**
- Compute momentum rate-of-change (derivative of price change):
  - Accelerating: `change_1h > change_6h / 6` → momentum building
  - Decelerating: `change_1h < change_6h / 6` → momentum fading
- Add EMA (exponential moving average) crossover signals
- Short EMA (6h) crossing above long EMA (24h) → bullish signal

**File:** `agents/signal_agent.py`

### 3.4 — Sentiment Analysis via Social Media

**Problem:** No social media signal — Twitter/X often leads market moves for political/crypto markets.

**Solution:**
- Add Twitter/X search via Serper's social results or a dedicated API
- Extract sentiment: count of positive/negative mentions in last 24h
- Weight by account influence (follower count if available)
- Only for high-signal categories: `crypto`, `politics`, `entertainment`

**Files:** `services/search_service.py`, `agents/signal_agent.py`

---

## PRIORITY 4: PROBABILITY CALIBRATION ENGINE

### 4.1 — Bayesian Probability Update

**Problem:** Probability agent makes one estimate and never updates it. Real probabilities shift.

**Solution:**
- Store initial probability estimate with timestamp
- On each pipeline cycle, re-check markets with open positions:
  - Fetch latest price + news
  - Bayesian update: `P(new) = P(prior) * likelihood_ratio`
  - If updated probability diverges >10% from entry → trigger position review
- Separate "re-evaluation" mini-pipeline for open positions

**Files:** `agents/probability_agent.py`, `services/orchestrator.py`

### 4.2 — Calibration Bucketing

**Problem:** Calibration data is aggregate (overall avg error). Doesn't tell agent if it's miscalibrated at specific probability ranges.

**Solution:**
- Bucket closed trades by AI probability: 0-20%, 20-40%, 40-60%, 60-80%, 80-100%
- Compute actual win rate per bucket
- Inject into prompt: "When you estimate 60-80%, actual outcome is YES 55% of the time. Adjust accordingly."
- Visualize calibration curve on the frontend

**Files:** `agents/memory_manager.py`, `agents/probability_agent.py`

### 4.3 — Confidence-Weighted Position Sizing

**Problem:** Strategy agent uses edge * Kelly but doesn't dynamically weight by historical accuracy.

**Solution:**
- Weight Kelly fraction by the agent's historical accuracy at that confidence level
- If agent says "90% confident" but history shows only 65% accuracy at that level → reduce size
- Formula: `adjusted_kelly = kelly * (historical_accuracy_at_confidence / confidence)`

**File:** `agents/strategy_agent.py`

### 4.4 — Automatic Edge Threshold Tuning

**Problem:** `min_edge` is hardcoded. Optimal threshold changes based on market conditions.

**Solution:**
- Track rolling average edge of winning vs losing trades
- If losing trades have avg edge 4% and winning trades avg 8% → set threshold at 6%
- Auto-adjust `min_edge` every 50 trades based on this data
- Log threshold changes and reasoning

**Files:** `agents/strategy_agent.py`, `core/config.py`

---

## PRIORITY 5: MEMORY & LEARNING LOOP

### 5.1 — Semantic Lesson Retrieval

**Problem:** Lessons are retrieved by recency, not relevance. A crypto lesson surfaces when analyzing a politics market.

**Solution:**
- Compute embedding vectors for each lesson (use a lightweight embedding model or hashing)
- On new market analysis, embed the market question
- Retrieve top-5 most semantically similar lessons instead of most recent
- Fallback to category-based retrieval if no embedding model is configured

**Files:** `agents/memory_manager.py`, create `services/embedding_service.py`

### 5.2 — Pattern Recognition Across Trades

**Problem:** Memory stores individual lessons but doesn't detect meta-patterns.

**Solution:**
- After every 20 trades, run a "meta-reflection" LLM call:
  - Input: last 20 trade outcomes + lessons
  - "Identify systematic patterns. Are we consistently wrong about X type of market?"
- Store meta-patterns as high-priority lessons
- Inject meta-patterns at the top of all agent prompts

**Files:** `agents/reflection_agent.py`, `agents/memory_manager.py`

### 5.3 — Lesson Decay & Relevance Scoring

**Problem:** A lesson from 3 months ago about COVID policy markets isn't relevant today.

**Solution:**
- Add `relevance_score` to lessons: starts at 1.0, decays by 0.01/day
- Lessons that get "confirmed" (same mistake repeated) get a relevance boost
- Only inject lessons with relevance > 0.3 into prompts
- Auto-archive lessons below 0.1 relevance

**Files:** `agents/memory_manager.py`, `models/db_models.py`

### 5.4 — Mistake Taxonomy Expansion

**Problem:** Only 6 mistake types: `overconfidence|anchoring|timing|insufficient_research|correct_prediction|other`. Too coarse.

**Solution:**
Add fine-grained mistake types:
```python
MISTAKE_TYPES = [
    "anchoring_to_market_price",    # Followed the herd
    "recency_bias",                 # Overweighted recent events
    "base_rate_neglect",            # Ignored historical frequency
    "overconfidence_narrow_range",  # Probability too extreme
    "insufficient_contrarian",      # Didn't consider opposing view
    "timing_too_early",             # Right direction, wrong timing
    "timing_too_late",              # Entered after the move
    "category_misunderstanding",    # Didn't understand the domain
    "data_quality_issue",           # Bad search results led to wrong conclusion
    "correct_prediction",           # ✅ Trade was correct
]
```

**File:** `agents/reflection_agent.py`

---

## PRIORITY 6: PIPELINE ORCHESTRATION

### 6.1 — Priority Queue for Markets

**Problem:** Pipeline picks top 5 markets by volume. Volume ≠ opportunity.

**Solution:**
- Score markets by: `priority = volume * (1 + liquidity/10000) * time_decay`
- `time_decay`: markets expiring soon get a boost (resolution timing strategy)
- Markets with existing positions get a 2x priority boost for re-evaluation
- Replace `markets.sort(key=lambda m: m.volume)` with priority scoring

**File:** `services/orchestrator.py`

### 6.2 — Parallel Pipeline Stages

**Problem:** Research → Signal → Probability is sequential per market. Some stages are independent.

**Solution:**
- Research and Signal can run in parallel (both read market data, don't depend on each other)
- Only Probability needs both research + signal
- Pipeline per market: `[Research || Signal] → Probability → Strategy`
- Reduces per-market latency by ~30%

**File:** `services/orchestrator.py`

### 6.3 — Circuit Breaker for Bad Streaks

**Problem:** System keeps trading during losing streaks. No automatic pullback mechanism.

**Solution:**
- Track rolling 10-trade P&L
- If last 10 trades net negative → reduce position sizes by 50%
- If last 20 trades net negative → pause trading for 1 hour, run "deep reflection"
- Resume with half-Kelly sizing for 10 trades after any pause

**Files:** `services/orchestrator.py`, `agents/risk_manager.py`

### 6.4 — Market Re-Evaluation Loop

**Problem:** No re-evaluation of open positions. Markets can shift dramatically after entry.

**Solution:**
- Every other pipeline cycle, run a mini-pipeline on open positions:
  - Fresh research + probability estimate
  - Compare new estimate with entry thesis
  - If edge has evaporated (edge < 2%), suggest exit
  - If edge doubled, suggest adding to position
- Emit `position_review` event for frontend display

**Files:** `services/orchestrator.py`, create `agents/position_reviewer.py`

---

## PRIORITY 7: LLM CLIENT HARDENING

### 7.1 — Structured Output Mode

**Problem:** LLM returns text → regex/JSON parsing → failures on malformed output. Fragile.

**Solution:**
- Use OpenRouter's `response_format: { type: "json_object" }` parameter
- Forces the model to return valid JSON
- Eliminates ~95% of parse failures
- If model doesn't support structured output, fall back to current parsing

**File:** `core/llm_client.py`

### 7.2 — Token Budget Management

**Problem:** No tracking of how many tokens each agent uses. Can't optimize costs.

**Solution:**
- Track tokens per-agent, per-call: `{agent: {calls: N, input_tokens: N, output_tokens: N}}`
- Set per-agent token budgets in config
- Log warning when agent approaches 80% of daily budget
- Emit `budget_warning` event for frontend display

**File:** `core/llm_client.py`, `core/config.py`

### 7.3 — Response Caching

**Problem:** Identical market analyzed on consecutive cycles wastes LLM calls.

**Solution:**
- Hash `system_prompt + user_prompt` → check cache before calling LLM
- Cache TTL: 15 minutes for research, 5 minutes for probability estimates
- Cache in-memory with `functools.lru_cache` or a simple dict with TTL
- Cache hit rate should be >30% for typical workloads

**File:** `core/llm_client.py`

### 7.4 — Model Performance Tracking

**Problem:** Model fallback rotates blindly. We don't know which models actually perform best.

**Solution:**
- Track per-model: avg latency, parse success rate, token cost
- After 50+ calls on a model, compute a "model quality score"
- Prefer models with high quality scores for important agents (probability, strategy)
- Use lower-quality models for less critical tasks (classification, initial triage)

**File:** `core/llm_client.py`

---

## PRIORITY 8: NEW AGENTS

### 8.1 — Contrarian Agent

**Problem:** All agents share the same information flow — no adversarial perspective.

**Solution:**
- New agent that specifically argues against the majority signal
- Takes research + initial probability → produces "anti-thesis"
- Strategy agent weighs both thesis and anti-thesis
- If contrarian case is stronger than main case → skip the trade

**File:** Create `agents/contrarian_agent.py`

### 8.2 — News Velocity Agent

**Problem:** No tracking of how fast news is breaking. Fast-breaking news = volatile odds.

**Solution:**
- Monitor news publication rate for a market topic:
  - "0-1 articles/day" → stable, trust current research
  - "10+ articles/day" → fast-breaking, reduce confidence
- Delay trading on fast-breaking news until velocity drops below 5/day
- Inject velocity score into probability agent prompt

**File:** Create `agents/news_velocity_agent.py`

### 8.3 — Market Maker Detection Agent

**Problem:** Some Polymarket markets have automated market makers that distort the order book.

**Solution:**
- Analyze trade patterns: regular intervals, constant sizes = bot trader
- Identify if most liquidity is from bots vs humans
- Markets dominated by bot liquidity → lower confidence in price signal
- Markets with organic, diverse trading → higher confidence in price signal

**File:** Create `agents/market_maker_detector.py`

### 8.4 — Exit Strategy Agent

**Problem:** No automated exit logic. Positions sit until market resolution or manual close.

**Solution:**
- Monitor open positions for exit triggers:
  - **Take profit**: price moved 20%+ in our favor → lock in gains
  - **Stop loss**: price moved 30%+ against us → cut losses
  - **Time decay**: <24h to expiry with uncertain outcome → reduce exposure
  - **Edge evaporation**: current edge < 2% → exit
- Execute exit trades through the existing execution pipeline

**File:** Create `agents/exit_agent.py`

---

## PRIORITY 9: OBSERVABILITY & DEBUGGING

### 9.1 — Agent Decision Trace Logging

**Problem:** When a trade goes wrong, no easy way to trace back through every agent's reasoning.

**Solution:**
- Create a `PipelineTrace` DB model:
  ```python
  class PipelineTrace(Base):
      id: int
      condition_id: str
      cycle_id: str  # unique per pipeline run
      agent_name: str
      input_data: dict  # what the agent received
      output_data: dict  # what the agent produced
      llm_prompt: str    # exact prompt sent
      llm_response: str  # exact response received
      duration_ms: int
      created_at: datetime
  ```
- Query by `cycle_id` to reconstruct the full decision chain
- Frontend: "Decision Trace" view on the trade detail modal

**Files:** `models/db_models.py`, `agents/base.py`, `services/orchestrator.py`

### 9.2 — Agent Performance Dashboard API

**Problem:** No way to compare agent performance metrics.

**Solution:**
- New API endpoint: `GET /api/agents/performance`
- Response includes per-agent:
  - Avg execution time
  - LLM token usage
  - Success/failure rates
  - Most common error types
- Frontend: Agent Performance comparison cards

**Files:** `api/routes.py`, `agents/base.py`

### 9.3 — Prompt Version Control

**Problem:** System prompts are hardcoded strings in agent files. No history of changes.

**Solution:**
- Move all system prompts to `prompts/` directory as versioned `.txt` files
- Load prompts at runtime from filesystem
- Log which prompt version was used for each LLM call
- Easy to A/B test prompt variations by swapping files

**Files:** Create `prompts/` directory, update all agents

### 9.4 — Backtesting Framework

**Problem:** No way to test pipeline changes against historical data before deploying.

**Solution:**
- Record all pipeline inputs (market data, search results, prices) as JSON snapshots
- Create `backtest.py` that replays snapshots through the pipeline with modified agents
- Compare: original prediction vs modified prediction vs actual outcome
- Compute: would this change have improved accuracy?

**Files:** Create `services/backtester.py`, `tests/test_backtest.py`

---

## IMPLEMENTATION ORDER

```
Week 1 (Pipeline Speed):
  1.2  Concurrent market analysis    — 1 hour
  6.2  Parallel pipeline stages      — 1 hour
  7.1  Structured output mode        — 30 min
  7.3  Response caching              — 1 hour

Week 2 (Research Quality):
  1.1  Multi-query research          — 2 hours
  1.3  Research depth scaling        — 1 hour
  2.1  Category-specific prompts     — 1 hour
  3.1  Order book depth analysis     — 1 hour

Week 3 (Intelligence):
  2.2  Chain-of-thought reasoning    — 1 hour
  2.4  Adversarial self-check        — 1 hour
  4.1  Bayesian probability update   — 2 hours
  4.2  Calibration bucketing         — 1 hour

Week 4 (Learning):
  5.1  Semantic lesson retrieval     — 2 hours
  5.2  Pattern recognition           — 1 hour
  6.3  Circuit breaker               — 1 hour
  8.4  Exit strategy agent           — 2 hours

Week 5 (New Agents + Observability):
  8.1  Contrarian agent              — 2 hours
  8.2  News velocity agent           — 1 hour
  9.1  Decision trace logging        — 2 hours
  9.4  Backtesting framework         — 3 hours
```

---

## EXPECTED IMPACT

| Improvement              | Accuracy Δ | Latency Δ | Token Cost Δ |
| ------------------------ | ---------- | --------- | ------------ |
| Multi-query research     | +5-8%      | +2s       | +40%         |
| Concurrent analysis      | —          | -60%      | —            |
| Category-specific prompts| +3-5%      | —         | —            |
| Chain-of-thought         | +5-10%     | +1s       | +20%         |
| Adversarial self-check   | +3-5%      | +3s       | +50%         |
| Bayesian updates         | +5-8%      | +2s       | +25%         |
| Calibration bucketing    | +3-5%      | —         | —            |
| Response caching         | —          | -30%      | -30%         |
| Exit strategy agent      | +5-10% PnL | —         | +10%         |

---

## AGENT ARCHITECTURE (Current)

```
┌──────────────────────────────────────────────────────────┐
│                     ORCHESTRATOR                          │
│  ┌──────────┐                                            │
│  │  Scanner  │──→ Market List                            │
│  └──────────┘                                            │
│       │                                                   │
│       ▼                                                   │
│  ┌──────────┐   ┌────────┐   ┌─────────────┐            │
│  │ Research  │──→│ Signal │──→│ Probability │            │
│  └──────────┘   └────────┘   └─────────────┘            │
│       │                            │                      │
│       │  ┌────────────┐            │                      │
│       └──│   Memory   │────────────┘                      │
│          └────────────┘                                   │
│                                    │                      │
│                                    ▼                      │
│                ┌──────────┐   ┌──────────┐                │
│                │ Strategy │──→│   Risk   │                │
│                └──────────┘   └──────────┘                │
│                                    │                      │
│                                    ▼                      │
│                ┌──────────┐   ┌───────────┐               │
│                │ Execute  │──→│ Reflect   │               │
│                └──────────┘   └───────────┘               │
└──────────────────────────────────────────────────────────┘
```

## AGENT ARCHITECTURE (Target)

```
┌──────────────────────────────────────────────────────────────────┐
│                     ORCHESTRATOR (Concurrent)                     │
│  ┌──────────┐                                                    │
│  │  Scanner  │──→ Priority-Scored Market List                    │
│  └──────────┘                                                    │
│       │                                                           │
│       ▼            ┌────────────────┐                             │
│  ┌──────────┐ ═══> │  News Velocity │  (parallel)                │
│  │ Research  │      └────────────────┘                            │
│  │ (multi-   │                                                    │
│  │  query)   │ ═══> ┌────────┐  (parallel)                       │
│  └──────────┘       │ Signal │                                    │
│       │             │ (order │                                    │
│       │             │  book) │                                    │
│       │             └────────┘                                    │
│       │                  │                                        │
│       │     ┌────────────┘                                        │
│       ▼     ▼                                                     │
│  ┌─────────────┐   ┌─────────────┐                                │
│  │ Probability │──→│ Contrarian  │  (adversarial check)          │
│  │ (Bayesian)  │   │   Agent     │                                │
│  └─────────────┘   └─────────────┘                                │
│       │                  │                                        │
│       │  ┌────────────┐  │                                        │
│       └──│   Memory   │──┘  (semantic retrieval)                  │
│          │ (embedded) │                                            │
│          └────────────┘                                            │
│                │                                                   │
│                ▼                                                   │
│  ┌──────────┐   ┌──────────┐   ┌───────────┐                     │
│  │ Strategy │──→│   Risk   │──→│  Execute  │                     │
│  │ (auto-   │   │(circuit  │   └───────────┘                     │
│  │ tuned)   │   │ breaker) │         │                            │
│  └──────────┘   └──────────┘         ▼                            │
│                              ┌───────────┐   ┌──────────┐        │
│                              │  Reflect  │──→│  Exit    │        │
│                              │(meta-learn)│  │ Strategy │        │
│                              └───────────┘   └──────────┘        │
│                                                                    │
│  ┌─────────────────────────────────────────┐                      │
│  │         Pipeline Trace Logger           │  (every step)        │
│  └─────────────────────────────────────────┘                      │
└──────────────────────────────────────────────────────────────────┘
```
