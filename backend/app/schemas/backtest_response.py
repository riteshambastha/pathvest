"""
Backtest Response Schemas
Defines the JSON schema for backtest results
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from datetime import date


class BacktestSummary(BaseModel):
    """Summary performance metrics"""
    # Return metrics
    total_return: float = Field(..., description="Total cumulative return")
    cagr: float = Field(..., description="Compound Annual Growth Rate")
    volatility: float = Field(..., description="Annualized volatility (std dev)")
    
    # Risk-adjusted metrics
    sharpe_ratio: float = Field(..., description="Sharpe Ratio")
    sortino_ratio: float = Field(..., description="Sortino Ratio")
    max_drawdown: float = Field(..., description="Maximum drawdown (negative)")
    romad: float = Field(..., description="Return over Max Drawdown")
    
    # Benchmark comparison
    alpha: float = Field(..., description="Alpha vs benchmark")
    beta: float = Field(..., description="Beta vs benchmark")
    information_ratio: float = Field(..., description="Information Ratio")
    
    # Risk metrics
    var_95: float = Field(..., description="Value at Risk (95%)")
    cvar_95: float = Field(..., description="Conditional VaR / Expected Shortfall (95%)")
    
    # Win rates
    win_rate_daily: float = Field(..., description="Daily win rate")
    win_rate_monthly: float = Field(..., description="Monthly win rate")
    win_rate_yearly: float = Field(..., description="Yearly win rate")
    
    # Best/Worst
    best_day: float = Field(..., description="Best daily return")
    worst_day: float = Field(..., description="Worst daily return")
    
    # Benchmark
    benchmark_total_return: float = Field(..., description="Benchmark total return")
    benchmark_cagr: float = Field(..., description="Benchmark CAGR")


class EquityCurve(BaseModel):
    """Equity curve data"""
    dates: List[str] = Field(..., description="List of dates (YYYY-MM-DD)")
    portfolio_values: List[float] = Field(..., description="Portfolio values")
    benchmark_values: List[float] = Field(..., description="Benchmark values")


class Trade(BaseModel):
    """Individual trade record"""
    entry_date: str = Field(..., description="Entry date (YYYY-MM-DD)")
    exit_date: Optional[str] = Field(None, description="Exit date (YYYY-MM-DD)")
    ticker: str = Field(..., description="Stock ticker")
    entry_price: float = Field(..., description="Entry price")
    exit_price: Optional[float] = Field(None, description="Exit price")
    shares: float = Field(..., description="Number of shares (fractional allowed)")
    pnl: Optional[float] = Field(None, description="Profit/Loss in dollars")
    return_pct: Optional[float] = Field(None, description="Return percentage")
    holding_period_days: Optional[int] = Field(None, description="Days held")
    exit_reason: Optional[str] = Field(None, description="Reason for exit")
    
    # Signal metadata
    signal_type: Optional[str] = Field(None, description="Signal type that triggered entry")
    conviction_score: Optional[float] = Field(None, description="Conviction score at entry")
    rank: Optional[int] = Field(None, description="Rank at entry")


class PositionHistory(BaseModel):
    """Historical position data"""
    date: str = Field(..., description="Date (YYYY-MM-DD)")
    ticker: str = Field(..., description="Stock ticker")
    quantity: float = Field(..., description="Position size (shares)")
    value: float = Field(..., description="Position value in dollars")
    weight: float = Field(..., description="Position weight as % of portfolio")


class MonthlyReturns(BaseModel):
    """Monthly returns matrix"""
    year: int
    months: Dict[str, float] = Field(..., description="Month name to return mapping")


class YearlyReturns(BaseModel):
    """Yearly returns"""
    year: int
    return_pct: float
    benchmark_return_pct: float


class BacktestResponse(BaseModel):
    """Complete backtest response"""
    backtest_id: str = Field(..., description="Unique backtest identifier")
    status: str = Field(..., description="Backtest status (completed, failed, running)")
    execution_time_seconds: float = Field(..., description="Execution time in seconds")
    
    # Core results
    summary: BacktestSummary
    equity_curve: EquityCurve
    trades: List[Trade]
    
    # Optional detailed data
    positions_history: Optional[List[PositionHistory]] = Field(
        None,
        description="Historical position data"
    )
    monthly_returns: Optional[List[MonthlyReturns]] = Field(
        None,
        description="Monthly returns matrix"
    )
    yearly_returns: Optional[List[YearlyReturns]] = Field(
        None,
        description="Yearly returns comparison"
    )
    
    # Metadata
    strategy_name: Optional[str] = Field(None, description="Strategy name")
    start_date: Optional[str] = Field(None, description="Backtest start date")
    end_date: Optional[str] = Field(None, description="Backtest end date")
    initial_capital: Optional[float] = Field(None, description="Initial capital")
    
    class Config:
        json_schema_extra = {
            "example": {
                "backtest_id": "bt_abc123",
                "status": "completed",
                "execution_time_seconds": 45.3,
                "summary": {
                    "total_return": 0.847,
                    "cagr": 0.0623,
                    "volatility": 0.182,
                    "sharpe_ratio": 1.23,
                    "sortino_ratio": 1.67,
                    "max_drawdown": -0.234,
                    "romad": 0.266,
                    "alpha": 0.032,
                    "beta": 0.87,
                    "information_ratio": 0.45,
                    "var_95": -0.023,
                    "cvar_95": -0.031,
                    "win_rate_daily": 0.54,
                    "win_rate_monthly": 0.61,
                    "win_rate_yearly": 0.70,
                    "best_day": 0.068,
                    "worst_day": -0.052,
                    "benchmark_total_return": 0.612,
                    "benchmark_cagr": 0.048
                },
                "equity_curve": {
                    "dates": ["2013-01-01", "2013-01-02"],
                    "portfolio_values": [1000000, 1001234],
                    "benchmark_values": [1000000, 1000876]
                },
                "trades": [
                    {
                        "entry_date": "2013-03-15",
                        "exit_date": "2013-09-22",
                        "ticker": "AAPL",
                        "entry_price": 62.35,
                        "exit_price": 71.20,
                        "shares": 801.6,
                        "pnl": 7091.16,
                        "return_pct": 0.142,
                        "holding_period_days": 191,
                        "exit_reason": "trailing_stop"
                    }
                ]
            }
        }


class BacktestStatus(BaseModel):
    """Backtest status for polling"""
    backtest_id: str
    status: str = Field(..., description="running, completed, failed")
    progress_pct: Optional[float] = Field(None, description="Progress percentage (0-100)")
    message: Optional[str] = Field(None, description="Status message")
    estimated_completion_seconds: Optional[float] = Field(
        None,
        description="Estimated seconds until completion"
    )

