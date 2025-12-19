"""
Backtest Request Schemas
Defines the JSON schema for backtest configuration requests
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import date


class BacktestPeriod(BaseModel):
    """Backtest time period"""
    start_date: date = Field(..., description="Backtest start date (YYYY-MM-DD)")
    end_date: date = Field(..., description="Backtest end date (YYYY-MM-DD)")


class UniverseFilters(BaseModel):
    """Universe filtering criteria"""
    market_cap_min: float = Field(
        default=500_000_000,
        description="Minimum market capitalization in dollars"
    )
    index_membership: str = Field(
        default="SP1500",
        description="Index membership requirement (SP500, SP400, SP600, SP1500)"
    )
    lookback_quarters: int = Field(
        default=9,
        description="Number of quarters to look back for active signals"
    )


class InvestorFilters(BaseModel):
    """Investor qualification criteria"""
    aum_min: float = Field(
        default=1_000_000_000,
        description="Minimum AUM in dollars (default: $1B)"
    )
    track_record_quarters: int = Field(
        default=8,
        description="Minimum consecutive quarters of filings"
    )
    concentration_max: float = Field(
        default=0.35,
        description="Maximum single position as % of portfolio"
    )
    turnover_max: float = Field(
        default=0.40,
        description="Maximum quarterly turnover rate"
    )


class TransactionFilters(BaseModel):
    """Transaction-based filtering criteria"""
    min_buy_value: float = Field(
        default=10_000_000,
        description="Minimum buy value per quarter in dollars"
    )
    share_increase_min: float = Field(
        default=0.05,
        description="Minimum share count increase percentage"
    )


class InsiderFilters(BaseModel):
    """Insider trading filtering criteria"""
    roles: List[str] = Field(
        default=["CEO", "CFO", "COO", "President", "Chairman"],
        description="Qualified C-Level roles"
    )
    value_min: float = Field(
        default=100_000,
        description="Minimum transaction value in dollars"
    )


class SubUniverseFilters(BaseModel):
    """Complete sub-universe filtering configuration"""
    selected_institutions: List[str] = Field(
        default_factory=list,
        description="List of institution CIKs to track"
    )
    investor: InvestorFilters = Field(default_factory=InvestorFilters)
    transaction: TransactionFilters = Field(default_factory=TransactionFilters)
    insider: InsiderFilters = Field(default_factory=InsiderFilters)


class TechnicalConfirmation(BaseModel):
    """Technical confirmation filter parameters"""
    price_breakout_days: int = Field(
        default=10,
        description="Number of days for price breakout calculation"
    )
    sma_period: int = Field(
        default=50,
        description="Simple Moving Average period"
    )
    rsi_period: int = Field(
        default=14,
        description="RSI calculation period"
    )
    rsi_threshold: float = Field(
        default=45,
        description="Minimum RSI threshold"
    )


class EntrySignals(BaseModel):
    """Entry signal configuration"""
    enable_doubling_down: bool = Field(
        default=True,
        description="Enable Signal A: Doubling Down"
    )
    enable_insider_buying: bool = Field(
        default=True,
        description="Enable Signal B: Insider Buying"
    )
    enable_herding: bool = Field(
        default=True,
        description="Enable Signal C: Institutional Herding"
    )
    technical_confirmation: TechnicalConfirmation = Field(
        default_factory=TechnicalConfirmation
    )


class PositionSizing(BaseModel):
    """Position sizing configuration"""
    method: str = Field(
        default="static",
        description="Position sizing method (static, risk_parity, etc.)"
    )
    percent_per_position: float = Field(
        default=0.05,
        description="Target position size as % of portfolio"
    )
    min_positions: int = Field(
        default=5,
        description="Minimum number of positions"
    )
    max_positions: int = Field(
        default=20,
        description="Maximum number of positions"
    )
    rank_buffer: int = Field(
        default=5,
        description="Rank buffer to prevent churn"
    )


class ConvictionWeights(BaseModel):
    """Conviction scoring weights"""
    herding: float = Field(
        default=0.6,
        description="Weight for institutional herding score"
    )
    insider: float = Field(
        default=0.4,
        description="Weight for insider confidence score"
    )


class ExitRules(BaseModel):
    """Exit module configuration"""
    enable_thesis_drift: bool = Field(
        default=True,
        description="Enable Module 1: Thesis Drift Exit"
    )
    enable_insider_reversal: bool = Field(
        default=True,
        description="Enable Module 2: Insider Reversal Exit"
    )
    enable_trailing_stop: bool = Field(
        default=True,
        description="Enable Module 3: Trailing Stop"
    )
    trailing_stop_percent: float = Field(
        default=0.15,
        description="Trailing stop percentage (15% default)"
    )
    enable_dead_money: bool = Field(
        default=True,
        description="Enable Module 4: Dead Money Exit"
    )
    dead_money_quarters: int = Field(
        default=4,
        description="Quarters before dead money exit"
    )


class TransactionCosts(BaseModel):
    """Transaction cost configuration"""
    commission_per_share: float = Field(
        default=0.005,
        description="Commission per share in dollars"
    )
    slippage_bps: float = Field(
        default=25,
        description="Slippage in basis points"
    )


class Heartbeat(BaseModel):
    """Rebalancing frequency configuration"""
    rebalance_frequency: str = Field(
        default="monthly",
        description="Rebalancing frequency (daily, weekly, monthly, quarterly)"
    )


class StrategyConfig(BaseModel):
    """Complete strategy configuration"""
    name: str = Field(..., description="Strategy name")
    backtest_period: BacktestPeriod
    initial_capital: float = Field(default=1_000_000, description="Initial capital in dollars")
    
    universe_filters: UniverseFilters = Field(default_factory=UniverseFilters)
    sub_universe_filters: SubUniverseFilters = Field(default_factory=SubUniverseFilters)
    entry_signals: EntrySignals = Field(default_factory=EntrySignals)
    position_sizing: PositionSizing = Field(default_factory=PositionSizing)
    conviction_weights: ConvictionWeights = Field(default_factory=ConvictionWeights)
    exit_rules: ExitRules = Field(default_factory=ExitRules)
    transaction_costs: TransactionCosts = Field(default_factory=TransactionCosts)
    heartbeat: Heartbeat = Field(default_factory=Heartbeat)


class BacktestRequest(BaseModel):
    """Complete backtest request"""
    strategy_config: StrategyConfig
    
    # Optional parameters
    enable_logging: bool = Field(
        default=False,
        description="Enable detailed logging"
    )
    save_results: bool = Field(
        default=True,
        description="Save results to database"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "strategy_config": {
                    "name": "Combined Professional",
                    "backtest_period": {
                        "start_date": "2013-01-01",
                        "end_date": "2023-12-31"
                    },
                    "initial_capital": 1000000,
                    "universe_filters": {
                        "market_cap_min": 3000000000,
                        "index_membership": "SP1500",
                        "lookback_quarters": 9
                    }
                },
                "enable_logging": False,
                "save_results": True
            }
        }

