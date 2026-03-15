"""Memory Manager — stores and retrieves lessons, patterns, and calibration data."""

from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import BaseAgent
from app.models.schemas import MemoryEntry
from app.models.db_models import LessonLearned, Trade, TradeStatus


class MemoryManager(BaseAgent):
    name = "memory_manager"

    async def run(self, db: AsyncSession) -> dict:
        """Retrieve aggregated memory for agent decision-making."""

        # Fetch recent lessons
        lessons_q = await db.execute(
            select(LessonLearned)
            .order_by(desc(LessonLearned.created_at))
            .limit(50)
        )
        lessons = lessons_q.scalars().all()

        # Aggregate by mistake type
        mistake_counts: dict[str, int] = {}
        for l in lessons:
            mt = l.mistake_type or "unknown"
            mistake_counts[mt] = mistake_counts.get(mt, 0) + 1

        # Extract top lessons
        critical_lessons = [
            {"lesson": l.lesson, "type": l.mistake_type, "severity": l.severity}
            for l in lessons
            if l.severity in ("high", "critical")
        ][:10]

        recent_lessons = [
            {"lesson": l.lesson, "type": l.mistake_type}
            for l in lessons[:10]
        ]

        # Category performance
        category_stats: dict[str, dict] = {}
        for l in lessons:
            cat = l.category or "unknown"
            if cat not in category_stats:
                category_stats[cat] = {"total": 0, "mistakes": 0}
            category_stats[cat]["total"] += 1
            if l.mistake_type and l.mistake_type != "correct_prediction":
                category_stats[cat]["mistakes"] += 1

        memory = {
            "total_lessons": len(lessons),
            "mistake_distribution": mistake_counts,
            "critical_lessons": critical_lessons,
            "recent_lessons": recent_lessons,
            "category_performance": category_stats,
        }

        self.log.info("memory_retrieved", total_lessons=len(lessons))
        return memory

    async def get_lessons_for_prompt(
        self, db: AsyncSession, limit: int = 20
    ) -> list[dict]:
        """Get recent lessons formatted for injection into agent prompts."""
        q = await db.execute(
            select(LessonLearned)
            .order_by(desc(LessonLearned.created_at))
            .limit(limit)
        )
        lessons = q.scalars().all()
        return [
            {
                "lesson": l.lesson,
                "mistake_type": l.mistake_type or "unknown",
                "severity": l.severity or "medium",
                "category": l.category or "general",
            }
            for l in lessons
        ]

    async def get_calibration_data(self, db: AsyncSession) -> dict:
        """Compute calibration stats from closed trades for probability agent.

        Returns per-category win rate, avg error, and bias direction.
        """
        closed_q = await db.execute(
            select(Trade).where(Trade.status == TradeStatus.CLOSED)
        )
        closed_trades = closed_q.scalars().all()

        if not closed_trades:
            return {}

        # Overall stats
        total_error = 0.0
        total_bias = 0.0  # positive = overestimates YES
        wins = 0
        by_category: dict[str, dict] = {}

        for t in closed_trades:
            actual = 1.0 if t.resolution_outcome == t.side.value else 0.0
            error = abs(t.ai_probability - actual)
            bias = t.ai_probability - actual
            total_error += error
            total_bias += bias

            if t.resolution_outcome == t.side.value:
                wins += 1

            # Per-category tracking (use lesson category if available)
            cat = "general"
            # Look up category from lessons for this trade
            lesson_q = await db.execute(
                select(LessonLearned.category)
                .where(LessonLearned.trade_id == t.id)
                .limit(1)
            )
            lesson_cat = lesson_q.scalar_one_or_none()
            if lesson_cat:
                cat = lesson_cat

            if cat not in by_category:
                by_category[cat] = {
                    "wins": 0, "total": 0, "total_error": 0.0, "total_bias": 0.0
                }
            by_category[cat]["total"] += 1
            by_category[cat]["total_error"] += error
            by_category[cat]["total_bias"] += bias
            if t.resolution_outcome == t.side.value:
                by_category[cat]["wins"] += 1

        n = len(closed_trades)
        avg_error = total_error / n
        avg_bias = total_bias / n

        calibration = {
            "overall": {
                "avg_error": round(avg_error, 4),
                "win_rate": round(wins / n, 4),
                "bias": "overestimates YES" if avg_bias > 0.05 else (
                    "overestimates NO" if avg_bias < -0.05 else "well-calibrated"
                ),
                "total_trades": n,
            },
            "by_category": {},
        }

        for cat, stats in by_category.items():
            cn = stats["total"]
            if cn >= 3:  # Only report categories with enough data
                calibration["by_category"][cat] = {
                    "win_rate": round(stats["wins"] / cn, 4),
                    "avg_error": round(stats["total_error"] / cn, 4),
                    "total": cn,
                }

        return calibration

    async def get_lessons_for_category(
        self, db: AsyncSession, category: str, limit: int = 10
    ) -> list[dict]:
        """Get lessons relevant to a specific market category."""
        q = await db.execute(
            select(LessonLearned)
            .where(LessonLearned.category == category)
            .order_by(desc(LessonLearned.created_at))
            .limit(limit)
        )
        lessons = q.scalars().all()
        return [
            {
                "lesson": l.lesson,
                "mistake_type": l.mistake_type,
                "severity": l.severity,
                "tags": l.tags,
            }
            for l in lessons
        ]

    async def store_manual_lesson(
        self, db: AsyncSession, entry: MemoryEntry
    ) -> None:
        """Store a manually created lesson or note."""
        lesson = LessonLearned(
            category=entry.category,
            description=entry.key,
            lesson=entry.value,
            severity="medium",
            tags=list(entry.metadata.keys()) if entry.metadata else [],
        )
        db.add(lesson)
        self.log.info("manual_lesson_stored", category=entry.category, key=entry.key)


memory_manager = MemoryManager()
