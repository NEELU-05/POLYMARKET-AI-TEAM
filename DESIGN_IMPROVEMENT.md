# Design Improvement Plan

> Frontend UI/UX improvements for the Polymarket AI Dashboard.
> Current stack: Next.js 15, React 19, Tailwind CSS 3.4, Recharts, lucide-react

---

## PROGRESS OVERVIEW

| Priority | Name                     | Status          |
| -------- | ------------------------ | --------------- |
| 1        | Critical UX Fixes        | ✅ Done          |
| 2        | Visual Polish            | ✅ Done          |
| 3        | New Components           | ✅ Done          |
| 4        | Responsive & Mobile      | ⏳ In Progress   |
| 5        | Data Visualization       | ✅ Done          |
| 6        | Real-Time Features       | ✅ Done          |
| 7        | Premium Visual Upgrade   | ✅ Done          |
| 8        | Accessibility & Perf     | ✅ Done          |
| 9        | Micro-Interactions       | ✅ Done          |
| 10       | Whale Copy-Trade Dashboard | 🔜 Next        |
| 11       | Advanced Analytics Page  | 🔜 Planned       |
| 12       | Settings & Config Panel  | 🔜 Planned       |
| 13       | Dark/Light Theme Toggle  | 🔜 Planned       |
| 14       | Notification Center      | 🔜 Planned       |
| 15       | Agent Decision Trace     | 🔜 Planned       |
| 16       | Portfolio Management Hub | 🔜 Planned       |
| 17       | Social Sentiment Agg     | 🔜 Planned       |

---

## PRIORITY 1: CRITICAL UX FIXES ✅ [DONE]

### 1.1 — Toast Notifications
- Installed `react-hot-toast` — wrapped all action buttons with `toast.promise()` for instant green/red feedback.
- **Files modified:** `app/layout.tsx`, `components/Sidebar.tsx`, `app/page.tsx`

### 1.2 — Skeleton Loading States
- Created `<Skeleton>` component — replaced all "Loading..." text with pulsing skeleton cards on every page.
- **File created:** `components/Skeleton.tsx`

### 1.3 — Button Feedback States
- All action buttons now show spinner + disabled state during API calls. No more double-clicks.
- **Files modified:** `components/Sidebar.tsx`, `app/page.tsx`

---

## PRIORITY 2: VISUAL POLISH ✅ [DONE]

### 2.1 — Icon Library
- Installed `lucide-react` — replaced all emoji icons with crisp SVG icons (BarChart3, ClipboardList, TrendingUp, Bot, Brain).
- **File modified:** `components/Sidebar.tsx`

### 2.2 — Custom Font
- Integrated `Inter` via `next/font/google` — self-hosted, zero external requests.
- **File modified:** `app/layout.tsx`

### 2.3 — Status Indicator Redesign
- Full-width gradient status bar: green glow = LIVE with cycle count, grey = STOPPED, animated pulse dot.
- **File modified:** `components/Sidebar.tsx`

### 2.4 — Card Hover Effects
- Added `transition-all hover:border-slate-600 hover:shadow-lg hover:shadow-blue-500/5` to `.card` class.
- **File modified:** `app/globals.css`

---

## PRIORITY 3: NEW COMPONENTS ✅ [DONE]

### 3.1 — Live Pipeline Progress Bar
- Created `<PipelineProgress>` — 6-stage animated progress bar (Scanning → Done), polls system status.
- **File created:** `components/PipelineProgress.tsx`

### 3.2 — Trade Detail Modal
- Click any trade row to open a `<dialog>` modal with full reasoning, edge breakdown, entry/exit, confidence score.
- **File created:** `components/TradeModal.tsx` — **Modified:** `app/trades/page.tsx`

### 3.3 — Mini Sparkline Charts
- `MetricCard` now accepts `sparklineData` prop — renders inline 60×20px SVG sparklines with color-matched strokes.
- **File modified:** `components/MetricCard.tsx`

### 3.4 — Market Cards (Position Detail)
- Positions now show: time-to-expiry progress bar, entry→current price with delta coloring, inline sparkline, and exposure info.
- **File modified:** `app/positions/page.tsx`

---

## PRIORITY 4: RESPONSIVE & MOBILE ⏳ [IN PROGRESS]

### 4.1 — Collapsible Sidebar ✅
- **Mobile (<768px):** Hidden by default, hamburger button top-left opens slide-over with backdrop blur.
- **Tablet/Desktop collapsed:** Icon-only mode (64px) with chevron toggle — labels hidden, tooltips on hover.
- **Desktop expanded:** Full 256px sidebar (original behavior).
- Auto-closes on mobile route navigation.
- **File modified:** `components/Sidebar.tsx`

### 4.2 — Table to Cards on Mobile
**Problem:** Trade history table is unreadable on phones (horizontal scroll).

**Solution:**
- Below `md:` breakpoint, render trades as stacked cards instead of table rows
- Show key info (market, side, PnL, status) in card format
- Hide secondary columns (AI prob, edge, confidence) behind an expand toggle

**File:** `app/trades/page.tsx`

---

## PRIORITY 5: DATA VISUALIZATION ✅ [DONE]

### 5.1 — Win Rate by Category Donut Chart
- Recharts `PieChart` donut with inner overall win rate text. Color-coded: green >60%, yellow 50-60%, red <50%.
- **File created:** `components/CategoryChart.tsx`

### 5.2 — Edge Distribution Histogram
- Stacked `BarChart` showing edge buckets (0-5% to 20%+) colored by wins (green) vs losses (red).
- **File created:** `components/EdgeHistogram.tsx`

### 5.3 — PnL Calendar Heatmap
- GitHub-style heatmap (15 weeks, ~105 days). Green = profit, red = loss, grey = no trades. Custom scrollbar.
- **File created:** `components/PnLCalendar.tsx`

---

## PRIORITY 6: REAL-TIME FEATURES ✅ [DONE]

### 6.1 — WebSocket Event Stream
- Backend: `app/api/websocket.py` — FastAPI WebSocket endpoint broadcasting all event bus events to connected clients.
- Frontend: `services/ws.ts` — auto-reconnecting WebSocket client with topic-based subscription.
- Event bus modified to support wildcard `*` subscriptions.

### 6.2 — Live Activity Feed
- New `<LiveFeed>` component — terminal-style real-time event stream with colored fields, auto-scroll, agent filtering.
- Agents page now has **Live Feed / History** tab switcher.
- **File created:** `components/LiveFeed.tsx` — **Modified:** `app/agents/page.tsx`

---

## PRIORITY 7: PREMIUM VISUAL UPGRADE ✅ [DONE]

### 7.1 — Glassmorphism Cards

**Problem:** Cards are plain opaque blocks — look flat and dated.

**Solution:**
- Add `backdrop-blur-xl bg-slate-800/60` with subtle border glow
- Layer semi-transparent gradients on top for depth
- Apply to `.card` and `.stat-card` classes

**File:** `app/globals.css`

### 7.2 — Animated Gradient Accents

**Problem:** Dashboard header and key sections have no visual energy.

**Solution:**
- Animated gradient border on the dashboard header section
- Subtle gradient shimmer on emergency mode badge
- CSS animation: `@keyframes gradient-shift` with `background-size: 200%`

**File:** `app/globals.css`, `app/page.tsx`

### 7.3 — Animated Number Counters

**Problem:** Metric values appear instantly — no sense of change or movement.

**Solution:**
- Create `<AnimatedNumber>` component using `requestAnimationFrame`
- Numbers count up from 0 to target on initial load
- On data refresh, smoothly animate from old value to new value
- Duration: 600ms with ease-out curve

**File:** Create `components/AnimatedNumber.tsx`, update `components/MetricCard.tsx`

### 7.4 — Page Transition Animations

**Problem:** Pages swap instantly with no transition — feels jarring.

**Solution:**
- Wrap page content in a fade+slide animation on mount
- Use CSS `@keyframes fadeSlideIn` with `opacity: 0 → 1` + `translateY: 8px → 0`
- Apply via Tailwind `animate-` class on each page's root `<div>`
- Zero-dependency, CSS only

**File:** `app/globals.css`, all page files

### 7.5 — Gradient Stat Badges

**Problem:** Win/loss badges are flat colored backgrounds.

**Solution:**
- Replace solid badge backgrounds with subtle gradients
- `.badge-green`: gradient from green-900/60 → emerald-900/40 with green-400 border glow
- `.badge-red`: gradient from red-900/60 → rose-900/40 with red-400 border glow
- Add a micro `box-shadow` glow matching the badge color

**File:** `app/globals.css`

---

## PRIORITY 8: ACCESSIBILITY & PERFORMANCE ✅ [DONE]

### 8.1 — Keyboard Navigation

**Problem:** No keyboard shortcuts — power users have to click everything.

**Solution:**
- `Ctrl+K` / `Cmd+K` → Command palette (fast page navigation + actions)
- `Ctrl+1-5` → Navigate to Dashboard/Trades/Positions/Agents/Memory
- `Escape` → Close any open modal
- `Ctrl+Enter` → Run Pipeline

**File:** Create `components/CommandPalette.tsx`, `hooks/useKeyboardShortcuts.ts`

### 8.2 — Reduced Motion Support

**Problem:** Animations can cause issues for users with motion sensitivities.

**Solution:**
- Wrap all animations in `@media (prefers-reduced-motion: reduce)` to disable them
- Respect user's OS setting automatically
- 1 CSS block in globals.css

**File:** `app/globals.css`

### 8.3 — Lazy Loading Charts

**Problem:** All chart components load on the dashboard even before data arrives.

**Solution:**
- Use `next/dynamic` with `ssr: false` for all Recharts-based components
- Show Skeleton placeholders while chart JS bundles load
- Reduces initial page load by ~40KB

**File:** `app/page.tsx`

### 8.4 — Image & Asset Optimization

**Problem:** No favicon, no Open Graph image, no PWA manifest.

**Solution:**
- Generate app icon (gradient P logo) and set as favicon
- Add Open Graph meta tags for link previews
- Add `manifest.json` for PWA installability

**Files:** `app/layout.tsx`, `public/favicon.ico`, `public/manifest.json`

---

## PRIORITY 9: MICRO-INTERACTIONS ✅ [DONE]

### 9.1 — Pulse on Data Refresh
- Flashes a brief blue `.metric-updated` pulse glow around any `MetricCard` when its value props change.

### 9.2 — Trade Row Entry Animation
- New trades in the table map render with a `.row-new` class that triggers a `slideInLeft` animation + green background highlight that slowly fades out.

### 9.3 — Tooltip Improvements
- Added an `<Info>` icon with CSS-only hover tooltips to `MetricCard` components.

---

## PRIORITY 10: WHALE COPY-TRADE DASHBOARD 🔜 [NEXT]

### 10.1 — Whale Wallets Page

**Problem:** No UI for the upcoming whale copy-trading system.

**Solution:**
- New `/whales` page accessible from sidebar
- Displays a list of watched whale wallets with: address, alias, win rate, PnL, trade count, last active
- Each wallet is a glassmorphism card with a colored border indicating profitability (green = profitable, red = losing)
- "Add Wallet" button opens a dialog to paste a Polygon address + assign an alias

**Files:** Create `app/whales/page.tsx`, update `components/Sidebar.tsx`

### 10.2 — Whale Trade Activity Feed

**Problem:** No real-time visibility into what whales are doing.

**Solution:**
- Real-time feed of whale trades streamed via WebSocket (`whale_trade` events)
- Each trade shows: whale alias, market question, side (YES/NO badge), size, timestamp
- Trades highlighted by size: normal = neutral, large (>$1K) = blue glow, mega (>$5K) = gold glow
- "Copy This Trade" button next to each entry → triggers the copy-trade pipeline

**Files:** Create `components/WhaleTradeCard.tsx`, update `app/whales/page.tsx`

### 10.3 — Whale Performance Comparison

**Problem:** No way to compare whale profitability at a glance.

**Solution:**
- Horizontal bar chart comparing whale PnL (ranked best → worst)
- Toggle between: All-time, 7 days, 30 days
- Sparkline mini-charts per whale showing equity curve
- Recharts `BarChart` with gradient fills matching whale profitability

**Files:** Create `components/WhaleLeaderboard.tsx`

### 10.4 — Copy Trade History

**Problem:** No record of which trades were copied vs original.

**Solution:**
- New tab on `/whales` page: "Copy History"
- Table showing: copied trade, source whale, delay (ms), our entry vs whale entry, PnL delta
- Badge: `COPIED` (blue), `SKIPPED` (grey), `FILTERED_BY_RISK` (yellow)

**File:** Update `app/whales/page.tsx`

---

## PRIORITY 11: ADVANCED ANALYTICS PAGE 🔜 [PLANNED]

### 11.1 — Dedicated Analytics Route

**Problem:** Dashboard crams too many charts. No deep-dive analytics view.

**Solution:**
- New `/analytics` page with sidebar nav entry (TrendingUp icon)
- Sections: Performance, Calibration, Agent Analysis, Risk Metrics
- Each section is a collapsible card with full-width charts

**Files:** Create `app/analytics/page.tsx`, update `components/Sidebar.tsx`

### 11.2 — Calibration Curve Chart

**Problem:** No visual way to see if the AI's probability estimates are well-calibrated.

**Solution:**
- X-axis: AI predicted probability (0-100% in buckets)
- Y-axis: Actual outcome rate
- Perfect calibration = diagonal line
- Overlay the system's actual curve to show over/under confidence
- Recharts `ScatterChart` with reference line

**File:** Create `components/CalibrationCurve.tsx`

### 11.3 — Drawdown Chart

**Problem:** Max drawdown is a single number — no sense of timing or depth.

**Solution:**
- Area chart showing drawdown percentage over time
- Highlight the worst drawdown period with a red shaded zone
- Show recovery time from each drawdown
- Helps identify if losses are clustered or spread out

**File:** Create `components/DrawdownChart.tsx`

### 11.4 — Trade Duration Distribution

**Problem:** No insight into how long positions are held.

**Solution:**
- Histogram of trade duration (hours/days) colored by outcome (win=green, loss=red)
- Reveals: are quick trades more profitable, or do longer holds win?
- Helps tune strategy agent timing parameters

**File:** Create `components/DurationHistogram.tsx`

### 11.5 — Profit Factor & Sharpe Ratio Cards

**Problem:** ROI alone doesn't capture risk-adjusted performance.

**Solution:**
- New metrics: Profit Factor (gross wins / gross losses), Sharpe Ratio, Sortino Ratio, Win/Loss ratio
- Display as a row of premium MetricCards with tooltips explaining each metric
- Requires backend API endpoint: `GET /api/analytics/advanced-metrics`

**Files:** `app/analytics/page.tsx`, backend `api/routes.py`

---

## PRIORITY 12: SETTINGS & CONFIG PANEL 🔜 [PLANNED]

### 12.1 — Settings Page

**Problem:** All config is in `.env` — no UI to adjust parameters without restarting.

**Solution:**
- New `/settings` page with sidebar nav entry (Settings icon)
- Organized in sections: Trading, Risk, LLM, Notifications
- Form inputs with validation, live preview of changes
- "Save" button writes to config via API → hot-reload

**Files:** Create `app/settings/page.tsx`, backend `api/routes.py`

### 12.2 — Risk Parameters Editor

**Problem:** `min_edge`, `max_trade_size`, `max_open_positions` are hardcoded.

**Solution:**
- Slider controls for: Minimum Edge (1-20%), Max Trade Size ($1-$100), Max Open Positions (1-20)
- Real-time preview: "With these settings, you would have taken X of your last 50 opportunities"
- Warning badge if settings are too aggressive

### 12.3 — LLM Model Selector

**Problem:** Model is set in `.env` — can't switch without restart.

**Solution:**
- Dropdown selector showing available OpenRouter models
- Display per-model: cost/1K tokens, avg latency, context window
- "Test Model" button sends a sample prompt and shows response quality

### 12.4 — Wallet & API Key Manager

**Problem:** API keys are in `.env` — no visibility into which keys are active.

**Solution:**
- Masked display of configured API keys (show last 4 chars)
- Status indicator: ✅ valid, ❌ expired, ⚠️ rate limited
- "Add Backup Key" button for OpenRouter key rotation

---

## PRIORITY 13: DARK/LIGHT THEME TOGGLE 🔜 [PLANNED]

### 13.1 — Theme System

**Problem:** Dashboard is dark-only. Some users prefer light mode, and demo screenshots look better in light.

**Solution:**
- CSS custom properties switch via `data-theme="dark"` / `data-theme="light"` on `<html>`
- Theme toggle button in sidebar footer (Sun/Moon icon)
- Persist choice in `localStorage`
- Respect OS `prefers-color-scheme` on first visit

**Files:** `app/globals.css`, `app/layout.tsx`, `components/Sidebar.tsx`

### 13.2 — Light Theme Design Tokens

```css
[data-theme="light"] {
  --bg-primary:    #f8fafc;  /* slate-50   */
  --bg-card:       #ffffff;  /* white      */
  --bg-hover:      #f1f5f9;  /* slate-100  */
  --border:        #e2e8f0;  /* slate-200  */
  --text-primary:  #0f172a;  /* slate-900  */
  --text-secondary:#64748b;  /* slate-500  */
  --text-muted:    #94a3b8;  /* slate-400  */
}
```

### 13.3 — Chart Theme Adaptation

**Problem:** Recharts colors are hardcoded for dark background.

**Solution:**
- Create a `useTheme()` hook that returns current theme + toggle function
- Pass theme-aware colors to all Recharts components
- Axis text, grid lines, and tooltips adapt to light/dark

**File:** Create `hooks/useTheme.ts`, update all chart components

---

## PRIORITY 14: NOTIFICATION CENTER 🔜 [PLANNED]

### 14.1 — Notification Bell & Drawer

**Problem:** Toasts disappear after 3 seconds. No history of important events.

**Solution:**
- Bell icon in top-right corner with unread count badge
- Click opens a slide-over drawer with notification history
- Notifications: trade executed, trade closed (with PnL), pipeline error, emergency mode triggered, whale alert
- Mark as read, dismiss, "view details" link to relevant page

**Files:** Create `components/NotificationCenter.tsx`, update `app/layout.tsx`

### 14.2 — Notification Categories & Priority

**Solution:**
- Categories with icons: `trade` (green), `alert` (yellow), `error` (red), `info` (blue), `whale` (purple)
- High-priority notifications (emergency mode, large loss) float to top and persist until dismissed
- Low-priority (pipeline completed, scan finished) auto-archive after 1 hour

### 14.3 — Sound Alerts (Optional)

**Problem:** No audio cue for critical events when browser tab is in background.

**Solution:**
- Subtle notification sound for: trade executed, emergency mode, whale alert
- Toggle on/off in settings
- Use Web Audio API — no external files needed

---

## PRIORITY 15: AGENT DECISION TRACE VIEWER 🔜 [PLANNED]

### 15.1 — Decision Trace Page

**Problem:** When a trade goes wrong, there's no way to see the full reasoning chain.

**Solution:**
- New section in `TradeModal`: "Decision Trace" tab
- Shows the full pipeline for that trade:
  1. Market Data (what the scanner saw)
  2. Research (search results + LLM summary)
  3. Signal (momentum, volume, factors)
  4. Probability (estimate + reasoning)
  5. Strategy (edge, Kelly sizing)
  6. Risk Assessment (approved/rejected + why)
- Each step is a collapsible card with input → output

**Files:** Update `components/TradeModal.tsx`, backend `api/routes.py`

### 15.2 — LLM Prompt Inspector

**Problem:** No way to see what prompt was sent to the LLM or what it responded.

**Solution:**
- Within each Decision Trace step, expandable "View Prompt" / "View Response" sections
- Syntax-highlighted JSON for structured responses
- Token count display per call
- Copy-to-clipboard button for prompt debugging

### 15.3 — Agent Timeline Visualization

**Problem:** Pipeline flow is invisible — users can't see which agent took how long.

**Solution:**
- Horizontal Gantt-style timeline showing all agent executions per pipeline cycle
- Each bar = one agent's run time, color-coded by agent
- Hover reveals: agent name, duration (ms), status (success/fail)
- Identify bottleneck agents at a glance

**File:** Create `components/AgentTimeline.tsx`

### 15.4 — Replay Pipeline Run

**Problem:** Can't replay or simulate what would happen with different parameters.

**Solution:**
- "Replay" button on any past pipeline cycle
- Shows: what if we had used a different `min_edge`? Different `max_trade_size`?
- Slider controls to adjust parameters and see which trades would change
- Requires backend backtesting API (see RESEARCH_AGENT_IMPROVEMENT.md §9.4)

---

## PRIORITY 16: PORTFOLIO MANAGEMENT HUB 🔜 [PLANNED]

### 16.1 — Multi-Wallet Support

**Problem:** User might have multiple Polymarket wallets for different strategies.

**Solution:**
- Unified view for multiple wallet addresses
- Toggle individual wallets on/off for global stats
- Aggregate PnL, equity, and positions across all connected accounts

### 16.2 — Exit Strategy Designer

**Problem:** Manual exits are hard to manage; AI exits need better UI controls.

**Solution:**
- Visual editor for exit rules: "Sell 50% if price > $0.80", "Trailing stop-loss: 5%"
- Preview potential exit scenarios on a price chart
- Real-time alerts when position price nears exit triggers

---

## PRIORITY 17: SOCIAL SENTIMENT AGGREGATOR 🔜 [PLANNED]

### 17.1 — Twitter/X & Reddit Signal Feed

**Problem:** Polymarket is deeply influenced by social sentiment that's not just "news".

**Solution:**
- Live feed of relevant tweets and Reddit threads for specific markets
- Sentiment score (Bullish/Bearish) per market based on social volume
- Correlation chart: Sentiment vs Market Price

### 17.2 — Influencer Tracking

**Problem:** Certain "crypto-influencers" move markets with single posts.

**Solution:**
- Watchlist of key accounts influencers
- Immediate "Sentiment Shift" alert when an influencer posts about a market we're in
- Auto-tagging influencer mentions in the research agent output

---

## INSTALLED PACKAGES

```bash
npm install react-hot-toast    # Toast notifications (3KB)
npm install lucide-react        # Icon library (tree-shakeable)
# Recharts already installed, next/font is built-in
```

---

## COMPONENTS CREATED

| Component            | File                              | Purpose                        |
| -------------------- | --------------------------------- | ------------------------------ |
| Skeleton             | `components/Skeleton.tsx`         | Pulsing loading placeholder    |
| PipelineProgress     | `components/PipelineProgress.tsx` | 6-stage pipeline tracker       |
| TradeModal           | `components/TradeModal.tsx`       | Trade detail dialog            |
| CategoryChart        | `components/CategoryChart.tsx`    | Win rate donut chart           |
| EdgeHistogram        | `components/EdgeHistogram.tsx`    | Edge distribution bars         |
| PnLCalendar          | `components/PnLCalendar.tsx`      | GitHub-style PnL heatmap       |
| LiveFeed             | `components/LiveFeed.tsx`         | Real-time event terminal       |
| AnimatedNumber       | `components/AnimatedNumber.tsx`   | Smooth number counter          |
| CommandPalette       | `components/CommandPalette.tsx`   | Ctrl+K command search          |

---

## NEW PAGES PLANNED

| Route          | Purpose                             | Priority |
| -------------- | ----------------------------------- | -------- |
| `/whales`      | Whale copy-trade dashboard          | 10       |
| `/analytics`   | Advanced performance analytics      | 11       |
| `/settings`    | Config panel for trading parameters | 12       |

---

## DESIGN TOKENS

```css
:root {
  --bg-primary:    #0f172a;  /* slate-900  — page background      */
  --bg-card:       #1e293b;  /* slate-800  — card/panel background */
  --bg-hover:      #334155;  /* slate-700  — hover states          */
  --border:        #334155;  /* slate-700  — card borders          */
  --border-subtle: #1e293b;  /* slate-800  — subtle dividers       */
  --text-primary:  #f1f5f9;  /* slate-100  — headings              */
  --text-secondary:#94a3b8;  /* slate-400  — labels, descriptions  */
  --text-muted:    #64748b;  /* slate-500  — timestamps, tertiary  */
  --accent:        #3b82f6;  /* blue-500   — primary actions       */
  --success:       #22c55e;  /* green-500  — wins, positive PnL    */
  --danger:        #ef4444;  /* red-500    — losses, errors        */
  --warning:       #eab308;  /* yellow-500 — alerts, caution       */
}
```
