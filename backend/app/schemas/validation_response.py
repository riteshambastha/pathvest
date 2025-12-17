"""
Validation Framework Response Schemas
Defines responses for validation analyses
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any


class WalkForwardPeriod(BaseModel):
    """Results for one walk-forward period"""
    period_index: int
    train_start: str
    train_end: str
    test_start: str
    test_end: str
    
    # Best parameters from training
    best_parameters: Dict[str, Any]
    train_sharpe: float
    
    # Out-of-sample performance
    test_sharpe: float
    test_cagr: float
    test_max_drawdown: float
    
    # Walk-Forward Efficiency
    wfe: float = Field(
        ...,
        description="Walk-Forward Efficiency (OOS performance / IS performance)"
    )


class WalkForwardResponse(BaseModel):
    """Walk-forward optimization results"""
    validation_id: str
    status: str
    periods: List[WalkForwardPeriod]
    
    # Aggregate statistics
    avg_wfe: float = Field(..., description="Average Walk-Forward Efficiency")
    median_wfe: float
    robust_periods_count: int = Field(
        ...,
        description="Number of periods with WFE between 0.6-1.2"
    )
    total_periods: int
    
    # Visualization data for cluster matrix
    cluster_matrix: List[List[float]] = Field(
        ...,
        description="Matrix of WFE values for heatmap (period x run)"
    )


class MonteCarloRun(BaseModel):
    """One Monte Carlo simulation run"""
    run_index: int
    total_return: float
    cagr: float
    sharpe_ratio: float
    max_drawdown: float
    
    # Equity curve for this run
    equity_curve: Optional[List[float]] = None


class MonteCarloResponse(BaseModel):
    """Monte Carlo simulation results"""
    validation_id: str
    status: str
    num_simulations: int
    
    # Original backtest performance
    original_sharpe: float
    original_cagr: float
    original_max_drawdown: float
    
    # Distribution statistics
    sharpe_mean: float
    sharpe_std: float
    sharpe_percentiles: Dict[str, float] = Field(
        ...,
        description="Percentiles (e.g., {'5': 0.45, '50': 0.89, '95': 1.34})"
    )
    
    cagr_mean: float
    cagr_std: float
    cagr_percentiles: Dict[str, float]
    
    max_drawdown_mean: float
    max_drawdown_std: float
    max_drawdown_percentiles: Dict[str, float]
    
    # Confidence intervals
    confidence_intervals: Dict[str, Dict[str, float]] = Field(
        ...,
        description="e.g., {'95': {'lower': 0.45, 'upper': 1.34}}"
    )
    
    # Visualization data
    probability_cone: Dict[str, List[float]] = Field(
        ...,
        description="Keys: 'dates', 'original', 'p5', 'p25', 'p50', 'p75', 'p95'"
    )


class ParameterSensitivityResponse(BaseModel):
    """Parameter sensitivity analysis results"""
    validation_id: str
    status: str
    
    parameter1_name: str
    parameter1_values: List[Any]
    parameter2_name: str
    parameter2_values: List[Any]
    
    metric_name: str
    
    # Heatmap matrix (param1 x param2)
    heatmap_matrix: List[List[float]] = Field(
        ...,
        description="Matrix of metric values for heatmap"
    )
    
    # Best parameter combination
    best_param1_value: Any
    best_param2_value: Any
    best_metric_value: float
    
    # Robustness analysis
    robust_region_size: int = Field(
        ...,
        description="Number of parameter combinations within 90% of best performance"
    )
    total_combinations: int


class StressPeriodResult(BaseModel):
    """Results for one stress period"""
    period_name: str
    start_date: str
    end_date: str
    
    # Strategy performance
    strategy_max_drawdown: float
    strategy_volatility: float
    strategy_sharpe: Optional[float]
    
    # Benchmark performance
    benchmark_max_drawdown: float
    benchmark_volatility: float
    benchmark_sharpe: Optional[float]
    
    # Relative performance
    relative_drawdown: float = Field(
        ...,
        description="Strategy DD / Benchmark DD (< 1.0 is better)"
    )
    relative_volatility: float


class StressTestResponse(BaseModel):
    """Stress testing results"""
    validation_id: str
    status: str
    
    periods: List[StressPeriodResult]
    
    # Aggregate statistics
    avg_relative_drawdown: float = Field(
        ...,
        description="Average relative drawdown across all stress periods"
    )
    worst_stress_period: str
    best_stress_period: str
    
    # Visualization data for bar chart
    comparison_chart: Dict[str, List[float]] = Field(
        ...,
        description="Keys: 'period_names', 'strategy_drawdowns', 'benchmark_drawdowns'"
    )


class ValidationSuiteResponse(BaseModel):
    """Complete validation suite results"""
    suite_id: str
    status: str
    execution_time_seconds: float
    
    walk_forward_results: Optional[WalkForwardResponse] = None
    monte_carlo_results: Optional[MonteCarloResponse] = None
    sensitivity_results: Optional[ParameterSensitivityResponse] = None
    stress_test_results: Optional[StressTestResponse] = None
    
    # Overall robustness score
    robustness_score: float = Field(
        ...,
        description="Composite robustness score (0-100)"
    )
    robustness_grade: str = Field(
        ...,
        description="A+, A, B+, B, C+, C, D, F"
    )

