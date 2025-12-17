"""
Metrics Calculator
Comprehensive performance and risk metrics calculation
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Tuple, Optional
from datetime import datetime


class MetricsCalculator:
    """
    Calculate comprehensive performance metrics
    
    Metrics Categories:
    1. Return Metrics: Total return, CAGR, best/worst periods
    2. Risk Metrics: Volatility, Max DD, VaR, cVaR
    3. Risk-Adjusted: Sharpe, Sortino, Calmar, RoMaD
    4. Benchmark Comparison: Alpha, Beta, Information Ratio, Tracking Error
    5. Statistical: Win rates, avg win/loss, profit factor
    """
    
    def __init__(self, risk_free_rate: float = 0.03):
        """
        Initialize metrics calculator
        
        Args:
            risk_free_rate: Annualized risk-free rate (default: 3%)
        """
        self.risk_free_rate = risk_free_rate
    
    def calculate_all_metrics(
        self,
        equity_curve: List[float],
        benchmark_curve: Optional[List[float]] = None,
        dates: Optional[List[str]] = None,
        trades: Optional[List[Dict]] = None
    ) -> Dict[str, float]:
        """
        Calculate all performance metrics
        
        Args:
            equity_curve: Portfolio equity values over time
            benchmark_curve: Benchmark equity values (optional)
            dates: Date strings (optional)
            trades: List of trade dictionaries (optional)
        
        Returns:
            Dict with all metrics
        """
        metrics = {}
        
        # Calculate returns
        returns = self._calculate_returns(equity_curve)
        
        # Return metrics
        metrics.update(self._calculate_return_metrics(equity_curve, returns, dates))
        
        # Risk metrics
        metrics.update(self._calculate_risk_metrics(equity_curve, returns))
        
        # Risk-adjusted metrics
        metrics.update(self._calculate_risk_adjusted_metrics(returns))
        
        # Benchmark comparison
        if benchmark_curve:
            benchmark_returns = self._calculate_returns(benchmark_curve)
            metrics.update(self._calculate_benchmark_metrics(returns, benchmark_returns))
        
        # Trade statistics
        if trades:
            metrics.update(self._calculate_trade_statistics(trades))
        
        return metrics
    
    def _calculate_returns(self, equity_curve: List[float]) -> np.ndarray:
        """Calculate period returns from equity curve"""
        equity_array = np.array(equity_curve)
        returns = np.diff(equity_array) / equity_array[:-1]
        return returns
    
    # ==================== Return Metrics ====================
    
    def _calculate_return_metrics(
        self,
        equity_curve: List[float],
        returns: np.ndarray,
        dates: Optional[List[str]] = None
    ) -> Dict[str, float]:
        """Calculate return-based metrics"""
        initial_value = equity_curve[0]
        final_value = equity_curve[-1]
        
        # Total return
        total_return = (final_value / initial_value) - 1
        
        # CAGR
        num_days = len(equity_curve)
        years = num_days / 252  # Trading days
        cagr = (final_value / initial_value) ** (1 / years) - 1 if years > 0 else 0
        
        # Best/Worst periods
        best_day = np.max(returns) if len(returns) > 0 else 0
        worst_day = np.min(returns) if len(returns) > 0 else 0
        
        # Monthly/yearly aggregation (simplified)
        monthly_returns = self._aggregate_returns(returns, period_size=21)  # ~21 trading days per month
        yearly_returns = self._aggregate_returns(returns, period_size=252)  # 252 trading days per year
        
        best_month = np.max(monthly_returns) if len(monthly_returns) > 0 else 0
        worst_month = np.min(monthly_returns) if len(monthly_returns) > 0 else 0
        best_year = np.max(yearly_returns) if len(yearly_returns) > 0 else 0
        worst_year = np.min(yearly_returns) if len(yearly_returns) > 0 else 0
        
        return {
            'total_return': float(total_return),
            'cagr': float(cagr),
            'best_day': float(best_day),
            'worst_day': float(worst_day),
            'best_month': float(best_month),
            'worst_month': float(worst_month),
            'best_year': float(best_year),
            'worst_year': float(worst_year)
        }
    
    # ==================== Risk Metrics ====================
    
    def _calculate_risk_metrics(
        self,
        equity_curve: List[float],
        returns: np.ndarray
    ) -> Dict[str, float]:
        """Calculate risk metrics"""
        # Volatility (annualized)
        volatility = np.std(returns) * np.sqrt(252) if len(returns) > 0 else 0
        
        # Maximum Drawdown
        max_drawdown = self._calculate_max_drawdown(equity_curve)
        
        # VaR and cVaR (95% confidence)
        var_95 = self._calculate_var(returns, confidence=0.95)
        cvar_95 = self._calculate_cvar(returns, confidence=0.95)
        
        # Downside deviation (for Sortino)
        downside_deviation = self._calculate_downside_deviation(returns, mar=0)
        
        return {
            'volatility': float(volatility),
            'max_drawdown': float(max_drawdown),
            'var_95': float(var_95),
            'cvar_95': float(cvar_95),
            'downside_deviation': float(downside_deviation)
        }
    
    def _calculate_max_drawdown(self, equity_curve: List[float]) -> float:
        """Calculate maximum drawdown"""
        equity_array = np.array(equity_curve)
        running_max = np.maximum.accumulate(equity_array)
        drawdowns = (equity_array - running_max) / running_max
        max_dd = np.min(drawdowns)
        return float(max_dd)
    
    def _calculate_var(self, returns: np.ndarray, confidence: float = 0.95) -> float:
        """Calculate Value at Risk"""
        if len(returns) == 0:
            return 0
        percentile = (1 - confidence) * 100
        var = np.percentile(returns, percentile)
        return float(var)
    
    def _calculate_cvar(self, returns: np.ndarray, confidence: float = 0.95) -> float:
        """Calculate Conditional VaR (Expected Shortfall)"""
        if len(returns) == 0:
            return 0
        var = self._calculate_var(returns, confidence)
        # cVaR is the average of returns below VaR
        losses = returns[returns <= var]
        cvar = np.mean(losses) if len(losses) > 0 else var
        return float(cvar)
    
    def _calculate_downside_deviation(self, returns: np.ndarray, mar: float = 0) -> float:
        """Calculate downside deviation (for Sortino ratio)"""
        downside_returns = returns[returns < mar]
        downside_dev = np.std(downside_returns) * np.sqrt(252) if len(downside_returns) > 0 else 0
        return float(downside_dev)
    
    # ==================== Risk-Adjusted Metrics ====================
    
    def _calculate_risk_adjusted_metrics(self, returns: np.ndarray) -> Dict[str, float]:
        """Calculate risk-adjusted performance metrics"""
        if len(returns) == 0:
            return {
                'sharpe_ratio': 0,
                'sortino_ratio': 0,
                'calmar_ratio': 0
            }
        
        # Annualized return
        mean_return = np.mean(returns) * 252
        
        # Volatility
        volatility = np.std(returns) * np.sqrt(252)
        
        # Sharpe Ratio
        sharpe = (mean_return - self.risk_free_rate) / volatility if volatility > 0 else 0
        
        # Sortino Ratio
        downside_dev = self._calculate_downside_deviation(returns, mar=0)
        sortino = (mean_return - self.risk_free_rate) / downside_dev if downside_dev > 0 else 0
        
        # Calmar Ratio (CAGR / Max DD)
        # Note: Would need full equity curve, placeholder for now
        calmar = 0  # Would be calculated with full context
        
        return {
            'sharpe_ratio': float(sharpe),
            'sortino_ratio': float(sortino),
            'calmar_ratio': float(calmar)
        }
    
    # ==================== Benchmark Comparison ====================
    
    def _calculate_benchmark_metrics(
        self,
        strategy_returns: np.ndarray,
        benchmark_returns: np.ndarray
    ) -> Dict[str, float]:
        """Calculate metrics vs benchmark"""
        # Align lengths
        min_len = min(len(strategy_returns), len(benchmark_returns))
        strategy_returns = strategy_returns[:min_len]
        benchmark_returns = benchmark_returns[:min_len]
        
        if len(strategy_returns) == 0:
            return {
                'alpha': 0,
                'beta': 0,
                'information_ratio': 0,
                'tracking_error': 0
            }
        
        # Beta
        covariance = np.cov(strategy_returns, benchmark_returns)[0, 1]
        benchmark_variance = np.var(benchmark_returns)
        beta = covariance / benchmark_variance if benchmark_variance > 0 else 0
        
        # Alpha
        strategy_mean = np.mean(strategy_returns) * 252
        benchmark_mean = np.mean(benchmark_returns) * 252
        alpha = strategy_mean - (self.risk_free_rate + beta * (benchmark_mean - self.risk_free_rate))
        
        # Tracking Error
        excess_returns = strategy_returns - benchmark_returns
        tracking_error = np.std(excess_returns) * np.sqrt(252)
        
        # Information Ratio
        information_ratio = np.mean(excess_returns) * 252 / tracking_error if tracking_error > 0 else 0
        
        return {
            'alpha': float(alpha),
            'beta': float(beta),
            'information_ratio': float(information_ratio),
            'tracking_error': float(tracking_error)
        }
    
    # ==================== Trade Statistics ====================
    
    def _calculate_trade_statistics(self, trades: List[Dict]) -> Dict[str, float]:
        """Calculate trade-level statistics"""
        if not trades:
            return {}
        
        # Extract P&L and returns
        pnls = [t.get('pnl', 0) for t in trades if t.get('exit_date') is not None]
        returns = [t.get('return_pct', 0) for t in trades if t.get('return_pct') is not None]
        
        if not pnls:
            return {}
        
        # Winning/losing trades
        winning_trades = [p for p in pnls if p > 0]
        losing_trades = [p for p in pnls if p < 0]
        
        # Win rate
        win_rate = len(winning_trades) / len(pnls) if pnls else 0
        
        # Average win/loss
        avg_win = np.mean(winning_trades) if winning_trades else 0
        avg_loss = np.mean(losing_trades) if losing_trades else 0
        
        # Profit factor
        total_wins = sum(winning_trades)
        total_losses = abs(sum(losing_trades))
        profit_factor = total_wins / total_losses if total_losses > 0 else 0
        
        # Average holding period
        holding_periods = [t.get('holding_period_days', 0) for t in trades if t.get('holding_period_days') is not None]
        avg_holding_period = np.mean(holding_periods) if holding_periods else 0
        
        return {
            'total_trades': len(trades),
            'win_rate': float(win_rate),
            'avg_win': float(avg_win),
            'avg_loss': float(avg_loss),
            'profit_factor': float(profit_factor),
            'avg_holding_period_days': float(avg_holding_period)
        }
    
    # ==================== Helper Methods ====================
    
    def _aggregate_returns(self, returns: np.ndarray, period_size: int) -> np.ndarray:
        """Aggregate daily returns into period returns"""
        if len(returns) == 0:
            return np.array([])
        
        period_returns = []
        
        for i in range(0, len(returns), period_size):
            period = returns[i:i+period_size]
            # Compound returns: (1+r1) * (1+r2) * ... - 1
            period_return = np.prod(1 + period) - 1
            period_returns.append(period_return)
        
        return np.array(period_returns)


# Singleton instance
_calculator_instance = None


def get_metrics_calculator() -> MetricsCalculator:
    """Get singleton MetricsCalculator instance"""
    global _calculator_instance
    
    if _calculator_instance is None:
        _calculator_instance = MetricsCalculator()
    
    return _calculator_instance

