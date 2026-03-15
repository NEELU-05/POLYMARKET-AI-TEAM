"""Pipeline Orchestrator — coordinates the full agent pipeline from scan to execution."""

import asyncio
from typing import Callable
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.event_bus import event_bus
from app.models.db_models import Trade, TradeStatus
from app.agents.market_scanner import market_scanner
from app.agents.market_classifier import market_classifier
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
    """Runs the full prediction pipeline."""

    async def run_full_pipeline(
        self,
        db: AsyncSession,
        stage_callback: Callable[[str], None] | None = None,
    ) -> dict:
        """Execute one full cycle with optional stage progress callback."""
        def stage(name: str) -> None:
            if stage_callback:
                stage_callback(name)

        try:
            return await asyncio.wait_for(
                self._run_pipeline(db, stage),
                timeout=600,
            )
        except asyncio.TimeoutError:
            log.error("pipeline_timeout")
            return {
                "stage": "timeout",
                "markets_scanned": 0,
                "opportunities": 0,
                "trades_executed": 0,
                "errors": ["Pipeline exceeded 10-minute timeout"],
            }
        except Exception as e:
            log.error("pipeline_error", error=str(e))
            return {
                "stage": "error",
                "markets_scanned": 0,
                "opportunities": 0,
                "trades_executed": 0,
                "errors": [str(e)[:200]],
            }

    async def _run_pipeline(
        self,
        db: AsyncSession,
        stage: Callable[[str], None],
    ) -> dict:
        log.info("pipeline_started")
        report = {
            "stage": "",
            "markets_scanned": 0,
            "opportunities": 0,
            "trades_executed": 0,
            "errors": [],
        }

        # Check trading allowed
        can_trade, reason = await paper_trading.can_trade(db)
        if not can_trade:
            log.warning("trading_blocked", reason=reason)
            report["stage"] = "blocked"
            report["errors"].append(reason)
            return report

        # Scan
        stage("scanning")
        markets = await market_scanner.run(limit=30)
        report["markets_scanned"] = len(markets)
        if not markets:
            report["stage"] = "no_markets"
            return report

        # Filter already-held condition IDs
        open_q = await db.execute(
            select(Trade.condition_id).where(Trade.status == TradeStatus.OPEN)
        )
        open_ids = set(open_q.scalars().all())
        if open_ids:
            before = len(markets)
            markets = [m for m in markets if m.condition_id not in open_ids]
            log.info("filtered_existing_positions", before=before, after=len(markets))

        if not markets:
            report["stage"] = "all_held"
            return report

        # Classify — skip untradeable and sports
        stage("classifying")
        classified = await market_classifier.run(markets)
        tradeable = [
            m for m, c in zip(markets, classified)
            if c.tradeable and c.category not in ("sports",)
        ]
        if not tradeable:
            log.info("no_tradeable_markets")
            report["stage"] = "no_tradeable"
            return report

        tradeable.sort(key=lambda m: m.volume, reverse=True)
        analyze_markets = tradeable[:5]

        # Load memory once for the whole cycle
        stage("analyzing")
        lessons = await memory_manager.get_lessons_for_prompt(db, limit=20)
        calibration = await memory_manager.get_calibration_data(db)

        estimates = []
        for market in analyze_markets:
            try:
                research = await research_agent.run(market, lessons=lessons)
                signal = await signal_agent.run(market, research)
                estimate = await probability_agent.run(
                    market, research, signal, calibration=calibration
                )
                estimates.append(estimate)
            except Exception as e:
                log.warning("analysis_error", market=market.question[:60], error=str(e))
                report["errors"].append(f"Analysis: {str(e)[:100]}")

        # Strategy
        stage("strategy")
        balance = await paper_trading.get_balance(db)
        opportunities = await strategy_agent.run(
            estimates, current_balance=balance, markets=analyze_markets
        )
        report["opportunities"] = len(opportunities)

        if not opportunities:
            report["stage"] = "no_opportunities"
            return report

        # Execute
        stage("executing")
        portfolio = await portfolio_manager.run(db)

        for opp in opportunities[:5]:
            try:
                assessment = await risk_manager.run(opp, portfolio)
                trade = await execution_agent.run(assessment, db)
                if trade:
                    report["trades_executed"] += 1
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
        return report

    async def run_reflection_cycle(self, db: AsyncSession) -> dict:
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
