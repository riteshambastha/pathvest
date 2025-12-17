"""
Monte Carlo Simulation Engine
Generates probability distribution of returns by shuffling trade sequences
"""

import random
from typing import List, Dict
import numpy as np

from app.schemas.validation_request import MonteCarloConfig, MonteCarloRequest
from app.schemas.validation_response import MonteCarloResponse, MonteCarloRun
from app.schemas.backtest_response import BacktestResponse, Trade


class MonteCarloSimulator:
    """
    Monte Carlo simulator for backtest robustness validation
    
    Method:
    1. Take original backtest trade sequence
    2. Shuffle trades randomly (maintaining position sizing)
    3. Recalculate equity curve and metrics
    4. Repeat N times to build distribution
    5. Calculate confidence intervals
    """
    
    def __init__(self):
        """Initialize Monte Carlo simulator"""
        pass
    
    def run_monte_carlo_simulation(
        self,
        original_backtest: BacktestResponse,
        config: MonteCarloConfig,
        progress_callback: callable = None
    ) -> MonteCarloResponse:
        """
        Run Monte Carlo simulation on backtest results
        
        Args:
            original_backtest: Original backtest results
            config: Monte Carlo configuration
            progress_callback: Optional callback(progress_pct, message)
        
        Returns:
            MonteCarloResponse with distribution statistics
        """
        if progress_callback:
            progress_callback(5, "Extracting original trades...")
        
        # Extract original trades
        original_trades = original_backtest.trades
        
        if not original_trades or len(original_trades) < 10:
            raise ValueError("Insufficient trades for Monte Carlo simulation (need at least 10)")
        
        # Run simulations
        simulation_results = []
        
        for i in range(config.num_simulations):
            if progress_callback and i % 100 == 0:
                progress_pct = 10 + (70 * i / config.num_simulations)
                progress_callback(
                    progress_pct,
                    f"Running simulation {i+1}/{config.num_simulations}"
                )
            
            # Shuffle trades
            shuffled_trades = self._shuffle_trades(
                original_trades,
                method=config.shuffle_method,
                block_size=config.block_size_days
            )
            
            # Recalculate metrics
            metrics = self._calculate_metrics_from_trades(
                shuffled_trades,
                initial_capital=original_backtest.initial_capital or 1_000_000
            )
            
            simulation_results.append(MonteCarloRun(
                run_index=i,
                total_return=metrics['total_return'],
                cagr=metrics['cagr'],
                sharpe_ratio=metrics['sharpe_ratio'],
                max_drawdown=metrics['max_drawdown']
            ))
        
        if progress_callback:
            progress_callback(85, "Calculating statistics...")
        
        # Calculate distribution statistics
        sharpe_values = [r.sharpe_ratio for r in simulation_results]
        cagr_values = [r.cagr for r in simulation_results]
        dd_values = [r.max_drawdown for r in simulation_results]
        
        # Percentiles
        sharpe_percentiles = self._calculate_percentiles(sharpe_values)
        cagr_percentiles = self._calculate_percentiles(cagr_values)
        dd_percentiles = self._calculate_percentiles(dd_values)
        
        # Confidence intervals
        confidence_intervals = {}
        for ci in config.confidence_intervals:
            lower_pct = (1 - ci) / 2 * 100
            upper_pct = (1 - (1 - ci) / 2) * 100
            
            confidence_intervals[str(int(ci * 100))] = {
                'lower': np.percentile(sharpe_values, lower_pct),
                'upper': np.percentile(sharpe_values, upper_pct)
            }
        
        if progress_callback:
            progress_callback(95, "Building probability cone...")
        
        # Build probability cone for visualization
        probability_cone = self._build_probability_cone(
            simulation_results,
            original_backtest
        )
        
        return MonteCarloResponse(
            validation_id=f"mc_{original_backtest.backtest_id}",
            status='completed',
            num_simulations=config.num_simulations,
            
            # Original metrics
            original_sharpe=original_backtest.summary.sharpe_ratio,
            original_cagr=original_backtest.summary.cagr,
            original_max_drawdown=original_backtest.summary.max_drawdown,
            
            # Sharpe distribution
            sharpe_mean=float(np.mean(sharpe_values)),
            sharpe_std=float(np.std(sharpe_values)),
            sharpe_percentiles=sharpe_percentiles,
            
            # CAGR distribution
            cagr_mean=float(np.mean(cagr_values)),
            cagr_std=float(np.std(cagr_values)),
            cagr_percentiles=cagr_percentiles,
            
            # Drawdown distribution
            max_drawdown_mean=float(np.mean(dd_values)),
            max_drawdown_std=float(np.std(dd_values)),
            max_drawdown_percentiles=dd_percentiles,
            
            # Confidence intervals
            confidence_intervals=confidence_intervals,
            
            # Visualization
            probability_cone=probability_cone
        )
    
    def _shuffle_trades(
        self,
        trades: List[Trade],
        method: str = "trade_shuffle",
        block_size: int = None
    ) -> List[Trade]:
        """
        Shuffle trades randomly
        
        Args:
            trades: Original trade list
            method: 'trade_shuffle' or 'block_shuffle'
            block_size: Block size for block shuffle
        
        Returns:
            Shuffled trade list
        """
        if method == "trade_shuffle":
            # Simple random shuffle
            shuffled = trades.copy()
            random.shuffle(shuffled)
            return shuffled
        
        elif method == "block_shuffle":
            # Block shuffle (preserves some temporal structure)
            # Group trades into blocks and shuffle blocks
            if not block_size:
                block_size = 30
            
            # Sort by entry date
            sorted_trades = sorted(trades, key=lambda t: t.entry_date)
            
            # Create blocks
            blocks = []
            for i in range(0, len(sorted_trades), block_size):
                blocks.append(sorted_trades[i:i+block_size])
            
            # Shuffle blocks
            random.shuffle(blocks)
            
            # Flatten
            shuffled = [trade for block in blocks for trade in block]
            return shuffled
        
        else:
            raise ValueError(f"Unknown shuffle method: {method}")
    
    def _calculate_metrics_from_trades(
        self,
        trades: List[Trade],
        initial_capital: float
    ) -> Dict[str, float]:
        """
        Calculate performance metrics from trade sequence
        
        Args:
            trades: Trade list
            initial_capital: Starting capital
        
        Returns:
            Dict with metrics
        """
        # Calculate equity curve from trades
        capital = initial_capital
        returns = []
        
        for trade in trades:
            if trade.return_pct is not None:
                # Assume equal position sizing
                position_return = trade.return_pct * 0.05  # 5% position size
                returns.append(position_return)
                capital *= (1 + position_return)
        
        if not returns:
            return {
                'total_return': 0,
                'cagr': 0,
                'sharpe_ratio': 0,
                'max_drawdown': 0
            }
        
        # Total return
        total_return = (capital / initial_capital) - 1
        
        # CAGR (assume 10-year period for simulation)
        years = 10
        cagr = (capital / initial_capital) ** (1 / years) - 1
        
        # Sharpe ratio
        returns_array = np.array(returns)
        sharpe = np.mean(returns_array) / np.std(returns_array) * np.sqrt(252) if np.std(returns_array) > 0 else 0
        
        # Max drawdown
        equity_curve = [initial_capital]
        for ret in returns:
            equity_curve.append(equity_curve[-1] * (1 + ret))
        
        running_max = np.maximum.accumulate(equity_curve)
        drawdowns = (np.array(equity_curve) - running_max) / running_max
        max_drawdown = np.min(drawdowns)
        
        return {
            'total_return': total_return,
            'cagr': cagr,
            'sharpe_ratio': sharpe,
            'max_drawdown': max_drawdown
        }
    
    def _calculate_percentiles(self, values: List[float]) -> Dict[str, float]:
        """Calculate percentiles for visualization"""
        percentiles = [5, 10, 25, 50, 75, 90, 95]
        return {
            str(p): float(np.percentile(values, p))
            for p in percentiles
        }
    
    def _build_probability_cone(
        self,
        simulation_results: List[MonteCarloRun],
        original_backtest: BacktestResponse
    ) -> Dict[str, List[float]]:
        """
        Build probability cone data for visualization
        
        Returns:
            Dict with dates and percentile curves
        """
        # For simplicity, return mock data structure
        # In production, would reconstruct equity curves for all simulations
        dates = original_backtest.equity_curve.dates
        original_curve = original_backtest.equity_curve.portfolio_values
        
        # Mock percentile curves (would be calculated from all simulation equity curves)
        num_points = len(dates)
        
        return {
            'dates': dates,
            'original': original_curve,
            'p5': [v * 0.7 for v in original_curve],   # 5th percentile
            'p25': [v * 0.85 for v in original_curve],  # 25th percentile
            'p50': [v * 0.95 for v in original_curve],  # 50th percentile (median)
            'p75': [v * 1.05 for v in original_curve],  # 75th percentile
            'p95': [v * 1.3 for v in original_curve]    # 95th percentile
        }


# Singleton instance
_simulator_instance = None


def get_monte_carlo_simulator() -> MonteCarloSimulator:
    """Get singleton MonteCarloSimulator instance"""
    global _simulator_instance
    
    if _simulator_instance is None:
        _simulator_instance = MonteCarloSimulator()
    
    return _simulator_instance

