"""
Stress Testing Module
Tests strategy performance during historical crisis periods
"""

from typing import List, Dict
from datetime import date, datetime

from app.schemas.validation_request import StressTestConfig, StressTestRequest
from app.schemas.validation_response import StressTestResponse, StressPeriodResult
from app.schemas.backtest_response import BacktestResponse


class StressTester:
    """
    Stress testing module
    
    Purpose:
    - Evaluate strategy during historical crisis periods
    - Compare drawdown vs benchmark during crashes
    - Identify vulnerability to specific market conditions
    
    Default Crisis Periods:
    - Dot Com Bubble (2000-2002)
    - 2008 Financial Crisis (2007-2009)
    - COVID-19 Crash (2020)
    - 2022 Inflation Spike (2022)
    """
    
    def __init__(self):
        """Initialize stress tester"""
        pass
    
    def run_stress_test(
        self,
        original_backtest: BacktestResponse,
        config: StressTestConfig,
        progress_callback: callable = None
    ) -> StressTestResponse:
        """
        Run stress testing analysis
        
        Args:
            original_backtest: Original backtest results
            config: Stress test configuration
            progress_callback: Optional callback(progress_pct, message)
        
        Returns:
            StressTestResponse with crisis period analysis
        """
        if progress_callback:
            progress_callback(5, "Analyzing stress periods...")
        
        period_results = []
        
        for i, stress_period in enumerate(config.stress_periods):
            if progress_callback:
                progress_pct = 10 + (80 * i / len(config.stress_periods))
                progress_callback(
                    progress_pct,
                    f"Analyzing {stress_period['name']}..."
                )
            
            # Extract metrics for this period
            result = self._analyze_stress_period(
                backtest=original_backtest,
                period_name=stress_period['name'],
                start_date=stress_period['start'],
                end_date=stress_period['end'],
                metrics_to_compare=config.metrics_to_compare
            )
            
            period_results.append(result)
        
        if progress_callback:
            progress_callback(95, "Aggregating results...")
        
        # Calculate aggregate statistics
        relative_drawdowns = [p.relative_drawdown for p in period_results]
        avg_relative_dd = sum(relative_drawdowns) / len(relative_drawdowns)
        
        # Find worst and best stress periods
        worst_period = max(period_results, key=lambda p: abs(p.strategy_max_drawdown))
        best_period = min(period_results, key=lambda p: abs(p.strategy_max_drawdown))
        
        # Build comparison chart data
        comparison_chart = {
            'period_names': [p.period_name for p in period_results],
            'strategy_drawdowns': [p.strategy_max_drawdown * 100 for p in period_results],
            'benchmark_drawdowns': [p.benchmark_max_drawdown * 100 for p in period_results]
        }
        
        return StressTestResponse(
            validation_id=f"st_{original_backtest.backtest_id}",
            status='completed',
            periods=period_results,
            avg_relative_drawdown=avg_relative_dd,
            worst_stress_period=worst_period.period_name,
            best_stress_period=best_period.period_name,
            comparison_chart=comparison_chart
        )
    
    def _analyze_stress_period(
        self,
        backtest: BacktestResponse,
        period_name: str,
        start_date: str,
        end_date: str,
        metrics_to_compare: List[str]
    ) -> StressPeriodResult:
        """
        Analyze performance during a single stress period
        
        Args:
            backtest: Backtest results
            period_name: Name of crisis period
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            metrics_to_compare: Metrics to extract
        
        Returns:
            StressPeriodResult
        """
        # Parse dates
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        
        # Extract equity curve for this period
        strategy_curve_segment = self._extract_equity_segment(
            dates=backtest.equity_curve.dates,
            values=backtest.equity_curve.portfolio_values,
            start_date=start,
            end_date=end
        )
        
        benchmark_curve_segment = self._extract_equity_segment(
            dates=backtest.equity_curve.dates,
            values=backtest.equity_curve.benchmark_values,
            start_date=start,
            end_date=end
        )
        
        # Calculate metrics for this period
        strategy_metrics = self._calculate_period_metrics(strategy_curve_segment)
        benchmark_metrics = self._calculate_period_metrics(benchmark_curve_segment)
        
        # Calculate relative performance
        relative_drawdown = (
            strategy_metrics['max_drawdown'] / benchmark_metrics['max_drawdown']
            if benchmark_metrics['max_drawdown'] != 0
            else 1.0
        )
        
        relative_volatility = (
            strategy_metrics['volatility'] / benchmark_metrics['volatility']
            if benchmark_metrics['volatility'] != 0
            else 1.0
        )
        
        return StressPeriodResult(
            period_name=period_name,
            start_date=start_date,
            end_date=end_date,
            
            # Strategy metrics
            strategy_max_drawdown=strategy_metrics['max_drawdown'],
            strategy_volatility=strategy_metrics['volatility'],
            strategy_sharpe=strategy_metrics.get('sharpe_ratio'),
            
            # Benchmark metrics
            benchmark_max_drawdown=benchmark_metrics['max_drawdown'],
            benchmark_volatility=benchmark_metrics['volatility'],
            benchmark_sharpe=benchmark_metrics.get('sharpe_ratio'),
            
            # Relative performance
            relative_drawdown=relative_drawdown,
            relative_volatility=relative_volatility
        )
    
    def _extract_equity_segment(
        self,
        dates: List[str],
        values: List[float],
        start_date: datetime,
        end_date: datetime
    ) -> List[float]:
        """
        Extract equity curve segment for a date range
        
        Args:
            dates: List of dates (strings)
            values: List of equity values
            start_date: Start date
            end_date: End date
        
        Returns:
            List of values within date range
        """
        segment = []
        
        for i, date_str in enumerate(dates):
            try:
                date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                
                if start_date <= date_obj <= end_date:
                    segment.append(values[i])
            except:
                continue
        
        return segment if segment else [values[0]]  # Fallback to first value
    
    def _calculate_period_metrics(self, equity_curve: List[float]) -> Dict[str, float]:
        """
        Calculate performance metrics for equity curve segment
        
        Args:
            equity_curve: Equity values over time
        
        Returns:
            Dict with max_drawdown, volatility, sharpe_ratio
        """
        import numpy as np
        
        if len(equity_curve) < 2:
            return {
                'max_drawdown': 0,
                'volatility': 0,
                'sharpe_ratio': None
            }
        
        # Calculate returns
        returns = np.diff(equity_curve) / equity_curve[:-1]
        
        # Volatility (annualized)
        volatility = np.std(returns) * np.sqrt(252) if len(returns) > 0 else 0
        
        # Max drawdown
        running_max = np.maximum.accumulate(equity_curve)
        drawdowns = (np.array(equity_curve) - running_max) / running_max
        max_drawdown = np.min(drawdowns)
        
        # Sharpe ratio (simplified, using 0 risk-free rate)
        sharpe = (
            np.mean(returns) / np.std(returns) * np.sqrt(252)
            if np.std(returns) > 0 and len(returns) > 0
            else None
        )
        
        return {
            'max_drawdown': float(max_drawdown),
            'volatility': float(volatility),
            'sharpe_ratio': float(sharpe) if sharpe is not None else None
        }


# Singleton instance
_tester_instance = None


def get_stress_tester() -> StressTester:
    """Get singleton StressTester instance"""
    global _tester_instance
    
    if _tester_instance is None:
        _tester_instance = StressTester()
    
    return _tester_instance

