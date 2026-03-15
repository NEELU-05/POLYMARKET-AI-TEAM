"""Pydantic schemas for inter-agent communication."""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class MarketData(BaseModel):
    condition_id: str
    question: str
    description: str = ""
    category: str = "unknown"
    outcome_yes_price: float
    outcome_no_price: float
    volume: float = 0.0
    liquidity: float = 0.0
    end_date: Optional[datetime] = None
    market_slug: str = ""
    token_id: str = ""  # YES token ID for CLOB/Data API calls


class ClassifiedMarket(BaseModel):
    condition_id: str
    question: str
    category: str
    subcategory: str = ""
    relevance_score: float = Field(ge=0.0, le=1.0)
    tradeable: bool = True


class ResearchResult(BaseModel):
    condition_id: str
    question: str
    summary: str
    key_factors: list[str] = []
    data_sources: list[str] = []
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    bull_case: str = ""
    bear_case: str = ""


class Signal(BaseModel):
    condition_id: str
    signal_type: str
    direction: str  # "yes" or "no"
    strength: float = Field(ge=0.0, le=1.0)
    reasoning: str = ""
    factors: dict = {}


class ProbabilityEstimate(BaseModel):
    condition_id: str
    question: str
    ai_probability: float = Field(ge=0.0, le=1.0)
    market_probability: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    edge: float = 0.0
    reasoning: str = ""


class TradeOpportunity(BaseModel):
    condition_id: str
    question: str
    side: str  # "yes" or "no"
    ai_probability: float
    market_probability: float
    edge: float
    suggested_size: float
    confidence: float
    reasoning: str = ""


class RiskAssessment(BaseModel):
    approved: bool
    trade: TradeOpportunity
    adjusted_size: float
    risk_score: float = Field(ge=0.0, le=1.0)
    warnings: list[str] = []
    rejection_reason: str = ""


class TradeExecution(BaseModel):
    trade_id: int
    condition_id: str
    side: str
    entry_price: float
    size: float
    status: str = "open"
    timestamp: datetime


class PortfolioState(BaseModel):
    balance: float
    open_positions: int
    total_exposure: float
    total_pnl: float
    total_trades: int
    win_rate: float
    roi: float
    max_drawdown: float


class ReflectionResult(BaseModel):
    trade_id: int
    condition_id: str
    mistake_type: str = ""
    description: str
    lesson: str
    severity: str = "medium"
    tags: list[str] = []


class MemoryEntry(BaseModel):
    category: str
    key: str
    value: str
    metadata: dict = {}
