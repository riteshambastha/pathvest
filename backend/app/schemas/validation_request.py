"""
Validation Framework Request Schemas
Defines requests for walk-forward optimization, Monte Carlo, parameter sensitivity, and stress testing
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import date
from app.schemas.backtest_request import StrategyConfig


class WalkForwardConfig(BaseModel):
    """Walk-forward optimization configuration"""
    train_period_months: int = Field(
        default=24,
        description="Training period length in months"
    )
    test_period_months: int = Field(
        default=6,
        description="Testing period length in months"
    )
    anchor_mode: bool = Field(
        default=False,
        description="Anchored (expanding window) vs rolling window"
    )
    min_train_months: int = Field(
        default=12,
        description="Minimum training period for anchored mode"
    )


class WalkForwardRequest(BaseModel):
    """Request for walk-forward optimization"""
    base_strategy: StrategyConfig
    walk_forward_config: WalkForwardConfig = Field(default_factory=WalkForwardConfig)
    
    # Parameters to optimize (key: parameter path, value: list of values to test)
    parameter_grid: Dict[str, List[Any]] = Field(
        default={
            "exit_rules.trailing_stop_percent": [0.10, 0.15, 0.20],
            "position_sizing.rank_buffer": [3, 5, 7]
        },
        description="Parameters to optimize with grid search"
    )


class MonteCarloConfig(BaseModel):
    """Monte Carlo simulation configuration"""
    num_simulations: int = Field(
        default=1000,
        description="Number of Monte Carlo runs"
    )
    confidence_intervals: List[float] = Field(
        default=[0.95, 0.99],
        description="Confidence intervals to compute (e.g., 0.95 = 95%)"
    )
    shuffle_method: str = Field(
        default="trade_shuffle",
        description="Method: 'trade_shuffle' or 'block_shuffle'"
    )
    block_size_days: Optional[int] = Field(
        default=30,
        description="Block size for block shuffle method"
    )


class MonteCarloRequest(BaseModel):
    """Request for Monte Carlo simulation"""
    backtest_id: str = Field(
        ...,
        description="ID of completed backtest to simulate"
    )
    monte_carlo_config: MonteCarloConfig = Field(default_factory=MonteCarloConfig)


class ParameterSensitivityConfig(BaseModel):
    """Parameter sensitivity analysis configuration"""
    parameter1_name: str = Field(
        ...,
        description="First parameter to vary (e.g., 'exit_rules.trailing_stop_percent')"
    )
    parameter1_values: List[Any] = Field(
        ...,
        description="Values to test for parameter 1"
    )
    parameter2_name: str = Field(
        ...,
        description="Second parameter to vary (e.g., 'entry_signals.technical_confirmation.sma_period')"
    )
    parameter2_values: List[Any] = Field(
        ...,
        description="Values to test for parameter 2"
    )
    metric: str = Field(
        default="sharpe_ratio",
        description="Metric to visualize (sharpe_ratio, cagr, max_drawdown, etc.)"
    )


class ParameterSensitivityRequest(BaseModel):
    """Request for parameter sensitivity analysis"""
    base_strategy: StrategyConfig
    sensitivity_config: ParameterSensitivityConfig


class StressTestConfig(BaseModel):
    """Stress testing configuration"""
    stress_periods: List[Dict[str, str]] = Field(
        default=[
            {"name": "Dot Com Bubble", "start": "2000-03-01", "end": "2002-10-31"},
            {"name": "2008 Financial Crisis", "start": "2007-10-01", "end": "2009-03-31"},
            {"name": "COVID-19 Crash", "start": "2020-02-01", "end": "2020-04-30"},
            {"name": "2022 Inflation Spike", "start": "2022-01-01", "end": "2022-10-31"}
        ],
        description="Historical stress periods to test"
    )
    metrics_to_compare: List[str] = Field(
        default=["max_drawdown", "volatility", "sharpe_ratio"],
        description="Metrics to compare during stress periods"
    )


class StressTestRequest(BaseModel):
    """Request for stress testing analysis"""
    backtest_id: str = Field(
        ...,
        description="ID of completed backtest to analyze"
    )
    stress_test_config: StressTestConfig = Field(default_factory=StressTestConfig)


class ValidationSuite(BaseModel):
    """Request for complete validation suite"""
    base_strategy: StrategyConfig
    
    enable_walk_forward: bool = Field(default=True)
    walk_forward_config: Optional[WalkForwardConfig] = None
    parameter_grid: Optional[Dict[str, List[Any]]] = None
    
    enable_monte_carlo: bool = Field(default=True)
    monte_carlo_config: Optional[MonteCarloConfig] = None
    
    enable_parameter_sensitivity: bool = Field(default=True)
    sensitivity_config: Optional[ParameterSensitivityConfig] = None
    
    enable_stress_test: bool = Field(default=True)
    stress_test_config: Optional[StressTestConfig] = None

