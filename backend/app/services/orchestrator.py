"""Pipeline Orchestrator — coordinates the full agent pipeline from scan to execution."""

import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.event_bus import event_bus
from app.models.db_models import Trade, TradeStatus
from app.agents.market_scanner import market_scanner
from app.agents.research_agent import research_agent
from app.agents.signal_agent import signal_agent
from app.agents.probability_agent import probability_agent
from app.agents.strategy_agent import strategy_agent
from app.agents.risk_manager import risk_manager
from app.agents.execution_agent import execution_agent
from app.agents.portfolio_manager import portfolio_manager
from app.agents.reflection_agent import reflection_agent
from app.agents.memory_manager import memory_manager
from app.trading.simulator import paper_trading

log = get_logger("orchestrator")


class Orchestrator:
    """Runs the full prediction pipeline: scan → classify → research → signal →
    probability → strategy → risk → execute → reflect."""

    async def run_full_pipeline(self, db: AsyncSession) -> dict:
        """Execute one full cycle of the prediction pipeline with 10-minute timeout."""
        try:
            # Wrap entire pipeline in asyncio timeout (10 minutes = 600 seconds)
            return await asyncio.wait_for(
                self._run_full_pipeline_internal(db),
                timeout=600
            )
        except asyncio.TimeoutError:
            log.error("pipeline_timeout", timeout_seconds=600)
            return {
                "stage": "timeout",
                "markets_scanned": 0,
                "opportunities": 0,
                "trades_executed": 0,
                "errors": ["Pipeline exceeded 10-minute timeout"]
            }
        except Exception as e:
            log.error("pipeline_error", error=str(e))
            return {
                "stage": "error",
                "markets_scanned": 0,
                "opportunities": 0,
                "trades_executed": 0,
                "errors": [str(e)[:200]]
            }

    async def _run_full_pipeline_internal(self, db: AsyncSession) -> dict:
        """Internal pipeline implementation."""
        log.info("pipeline_started")
        report = {"stage": "", "markets_scanned": 0, "opportunities": 0, "trades_executed": 0, "errors": []}

        try:
            # Stage 1: Check if trading is allowed
            can_trade, reason = await paper_trading.can_trade(db)
            if not can_trade:
                log.warning("trading_blocked", reason=reason)
                report["stage"] = "blocked"
                report["errors"].append(reason)
                return report

            # Stage 2: Scan markets
            report["stage"] = "scanning"
            markets = await market_scanner.run(limit=30)
            report["markets_scanned"] = len(markets)

            if not markets:
                log.info("no_markets_found")
                report["stage"] = "no_markets"
                return report

            # Stage 2.5: Filter out markets we already have open positions on
            open_q = await db.execute(
                select(Trade.condition_id).where(Trade.status == TradeStatus.OPEN)
            )
            open_condition_ids = set(open_q.scalars().all())
            if open_condition_ids:
                before = len(markets)
                markets = [m for m in markets if m.condition_id not in open_condition_ids]
                log.info("filtered_existing_positions",
                         before=before, after=len(markets),
                         skipped=before - len(markets))

            if not markets:
                log.info("all_markets_already_held")
                report["stage"] = "all_held"
                return report

            # Stage 3: Skip classifier — sort by volume and pick top markets
            markets.sort(key=lambda m: m.volume, reverse=True)
            analyze_markets = markets[:5]

            # Stage 4: Research + Signal + Probability (per market)
            report["stage"] = "analyzing"
            estimates = []

            # Retrieve memory and calibration for context injection
            memory = await memory_manager.run(db)
            lessons = await memory_manager.get_lessons_for_prompt(db, limit=20)
            calibration = await memory_manager.get_calibration_data(db)

            for market in analyze_markets:

                try:
                    research = await research_agent.run(market, lessons=lessons)
                    signal = await signal_agent.run(market, research)
                    estimate = await probability_agent.run(
                        market, research, signal, calibration=calibration
                    )
                    estimates.append(estimate)
                except Exception as e:
                    log.warning(
                        "analysis_error",
                        market=market.question[:60],
                        error=str(e),
                    )
                    report["errors"].append(f"Analysis: {str(e)[:100]}")

            # Stage 5: Strategy — find opportunities
            report["stage"] = "strategy"
            balance = await paper_trading.get_balance(db)
            opportunities = await strategy_agent.run(
                estimates, current_balance=balance, markets=analyze_markets
            )
            report["opportunities"] = len(opportunities)

            if not opportunities:
                log.info("no_opportunities")
                report["stage"] = "no_opportunities"
                return report

            # Stage 6: Risk management + Execution
            report["stage"] = "executing"
            portfolio = await portfolio_manager.run(db)

            for opp in opportunities[:5]:  # Max 5 trades per cycle
                try:
                    assessment = await risk_manager.run(opp, portfolio)
                    trade = await execution_agent.run(assessment, db)

                    if trade:
                        report["trades_executed"] += 1
                        # Refresh portfolio state after each trade
                        portfolio = await portfolio_manager.run(db)
                except Exception as e:
                    log.warning("execution_error", error=str(e))
                    report["errors"].append(f"Execution: {str(e)[:100]}")

            report["stage"] = "completed"
            log.info(
                "pipeline_completed",
                markets=report["markets_scanned"],
                opportunities=report["opportunities"],
                trades=report["trades_executed"],
            )

        except Exception as e:
            log.error("pipeline_error", error=str(e))
            report["errors"].append(f"Pipeline: {str(e)[:200]}")
            report["stage"] = "error"

        return report

    async def run_reflection_cycle(self, db: AsyncSession) -> dict:
        """Check resolved markets and learn from outcomes."""
        log.info("reflection_cycle_started")
        try:
            reflections = await reflection_agent.run(db)
            return {
                "reflections": len(reflections),
                "lessons": [r.lesson for r in reflections],
            }
        except Exception as e:
            log.error("reflection_cycle_error", error=str(e))
            return {"reflections": 0, "error": str(e)}


orchestrator = Orchestrator()
