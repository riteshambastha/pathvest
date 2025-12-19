"""
Walk-Forward Optimization Engine
Implements train-test split methodology for robust strategy validation
"""

from typing import List, Dict, Any, Tuple, Optional
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
import itertools
import asyncio

from app.schemas.validation_request import WalkForwardConfig, WalkForwardRequest
from app.schemas.validation_response import WalkForwardResponse, WalkForwardPeriod
from app.schemas.backtest_request import StrategyConfig

# LEAN engine imports commented out until LEAN worker is implemented
# from lean_engine.worker.backtest_worker import get_backtest_worker


class WalkForwardOptimizer:
    """
    Walk-forward optimization engine
    
    Process:
    1. Split date range into train/test periods
    2. For each period:
       a. Optimize parameters on train set (grid search)
       b. Apply best parameters to test set
       c. Calculate Walk-Forward Efficiency (WFE)
    3. Aggregate results across periods
    """
    
    def __init__(self):
        """Initialize walk-forward optimizer"""
        # TODO: Initialize backtest worker when LEAN engine is implemented
        self.backtest_worker = None  # get_backtest_worker()
    
    async def run_walk_forward_optimization(
        self,
        request: WalkForwardRequest,
        progress_callback: callable = None
    ) -> WalkForwardResponse:
        """
        Execute walk-forward optimization
        
        Args:
            request: WalkForwardRequest configuration
            progress_callback: Optional callback(progress_pct, message)
        
        Returns:
            WalkForwardResponse with results
        """
        # Generate period splits
        periods = self._generate_periods(
            start_date=request.base_strategy.backtest_period.start_date,
            end_date=request.base_strategy.backtest_period.end_date,
            config=request.walk_forward_config
        )
        
        if progress_callback:
            progress_callback(5, f"Generated {len(periods)} walk-forward periods")
        
        # Run optimization for each period
        period_results = []
        
        for i, (train_start, train_end, test_start, test_end) in enumerate(periods):
            if progress_callback:
                progress_pct = 10 + (80 * i / len(periods))
                progress_callback(
                    progress_pct,
                    f"Processing period {i+1}/{len(periods)}: Train {train_start} to {train_end}"
                )
            
            # Optimize on training period
            best_params, train_sharpe = await self._optimize_on_train_set(
                base_strategy=request.base_strategy,
                parameter_grid=request.parameter_grid,
                train_start=train_start,
                train_end=train_end
            )
            
            # Test on out-of-sample period
            test_metrics = await self._test_on_oos_set(
                base_strategy=request.base_strategy,
                parameters=best_params,
                test_start=test_start,
                test_end=test_end
            )
            
            # Calculate WFE
            test_sharpe = test_metrics['sharpe_ratio']
            wfe = test_sharpe / train_sharpe if train_sharpe > 0 else 0
            
            # Store period result
            period_results.append(WalkForwardPeriod(
                period_index=i,
                train_start=str(train_start),
                train_end=str(train_end),
                test_start=str(test_start),
                test_end=str(test_end),
                best_parameters=best_params,
                train_sharpe=train_sharpe,
                test_sharpe=test_sharpe,
                test_cagr=test_metrics['cagr'],
                test_max_drawdown=test_metrics['max_drawdown'],
                wfe=wfe
            ))
        
        if progress_callback:
            progress_callback(95, "Aggregating results...")
        
        # Aggregate statistics
        wfe_values = [p.wfe for p in period_results]
        avg_wfe = sum(wfe_values) / len(wfe_values) if wfe_values else 0
        median_wfe = sorted(wfe_values)[len(wfe_values) // 2] if wfe_values else 0
        robust_count = sum(1 for wfe in wfe_values if 0.6 <= wfe <= 1.2)
        
        # Build cluster matrix for visualization
        cluster_matrix = [[p.wfe for p in period_results]]
        
        return WalkForwardResponse(
            validation_id=f"wf_{id(request)}",
            status='completed',
            periods=period_results,
            avg_wfe=avg_wfe,
            median_wfe=median_wfe,
            robust_periods_count=robust_count,
            total_periods=len(periods),
            cluster_matrix=cluster_matrix
        )
    
    def _generate_periods(
        self,
        start_date: date,
        end_date: date,
        config: WalkForwardConfig
    ) -> List[Tuple[date, date, date, date]]:
        """
        Generate train/test period splits
        
        Args:
            start_date: Overall start date
            end_date: Overall end date
            config: WalkForwardConfig
        
        Returns:
            List of (train_start, train_end, test_start, test_end) tuples
        """
        periods = []
        current_date = start_date
        
        while True:
            # Calculate train period
            if config.anchor_mode:
                # Anchored: train from start_date
                train_start = start_date
                train_end = current_date + relativedelta(months=config.train_period_months)
            else:
                # Rolling window
                train_start = current_date
                train_end = current_date + relativedelta(months=config.train_period_months)
            
            # Calculate test period
            test_start = train_end + timedelta(days=1)
            test_end = test_start + relativedelta(months=config.test_period_months)
            
            # Check if test period exceeds end date
            if test_end > end_date:
                break
            
            # Check minimum train period for anchored mode
            if config.anchor_mode:
                train_months = (train_end.year - train_start.year) * 12 + (train_end.month - train_start.month)
                if train_months < config.min_train_months:
                    current_date = test_end + timedelta(days=1)
                    continue
            
            periods.append((train_start, train_end, test_start, test_end))
            
            # Move to next period
            current_date = test_end + timedelta(days=1)
        
        return periods
    
    async def _optimize_on_train_set(
        self,
        base_strategy: StrategyConfig,
        parameter_grid: Dict[str, List[Any]],
        train_start: date,
        train_end: date
    ) -> Tuple[Dict[str, Any], float]:
        """
        Optimize parameters on training set using grid search
        
        Args:
            base_strategy: Base strategy configuration
            parameter_grid: Parameters to optimize
            train_start: Training start date
            train_end: Training end date
        
        Returns:
            (best_parameters, best_sharpe_ratio)
        """
        # Generate all parameter combinations
        param_names = list(parameter_grid.keys())
        param_values_lists = [parameter_grid[name] for name in param_names]
        combinations = list(itertools.product(*param_values_lists))
        
        best_params = {}
        best_sharpe = -999
        
        # Test each combination
        for combination in combinations:
            params = dict(zip(param_names, combination))
            
            # Create strategy with these parameters
            test_strategy = self._apply_parameters(base_strategy, params)
            test_strategy.backtest_period.start_date = train_start
            test_strategy.backtest_period.end_date = train_end
            
            # Run backtest (mock for now)
            # In production: result = await self.backtest_worker.execute_backtest(...)
            sharpe = self._mock_backtest_sharpe(params)
            
            if sharpe > best_sharpe:
                best_sharpe = sharpe
                best_params = params
        
        return best_params, best_sharpe
    
    async def _test_on_oos_set(
        self,
        base_strategy: StrategyConfig,
        parameters: Dict[str, Any],
        test_start: date,
        test_end: date
    ) -> Dict[str, float]:
        """
        Test parameters on out-of-sample period
        
        Args:
            base_strategy: Base strategy configuration
            parameters: Parameters to test
            test_start: Test start date
            test_end: Test end date
        
        Returns:
            Dict with metrics (sharpe_ratio, cagr, max_drawdown)
        """
        # Apply parameters
        test_strategy = self._apply_parameters(base_strategy, parameters)
        test_strategy.backtest_period.start_date = test_start
        test_strategy.backtest_period.end_date = test_end
        
        # Run backtest (mock for now)
        # In production: result = await self.backtest_worker.execute_backtest(...)
        return {
            'sharpe_ratio': self._mock_backtest_sharpe(parameters) * 0.85,  # OOS penalty
            'cagr': 0.08,
            'max_drawdown': -0.18
        }
    
    def _apply_parameters(
        self,
        base_strategy: StrategyConfig,
        parameters: Dict[str, Any]
    ) -> StrategyConfig:
        """
        Apply parameter values to strategy config
        
        Args:
            base_strategy: Base configuration
            parameters: Parameters to apply (dot notation paths)
        
        Returns:
            Modified StrategyConfig
        """
        # Create a copy
        strategy = base_strategy.copy(deep=True)
        
        # Apply each parameter
        for param_path, value in parameters.items():
            parts = param_path.split('.')
            
            # Navigate to nested attribute
            obj = strategy
            for part in parts[:-1]:
                obj = getattr(obj, part)
            
            # Set value
            setattr(obj, parts[-1], value)
        
        return strategy
    
    def _mock_backtest_sharpe(self, params: Dict[str, Any]) -> float:
        """Mock backtest Sharpe ratio calculation"""
        # Simulate parameter sensitivity
        base_sharpe = 1.2
        
        for param, value in params.items():
            if 'trailing_stop_percent' in param:
                # Optimal around 0.15
                deviation = abs(value - 0.15)
                base_sharpe -= deviation * 2
            elif 'rank_buffer' in param:
                # Optimal around 5
                deviation = abs(value - 5)
                base_sharpe -= deviation * 0.1
        
        return max(base_sharpe, 0.3)


# Singleton instance
_optimizer_instance = None


def get_walk_forward_optimizer() -> WalkForwardOptimizer:
    """Get singleton WalkForwardOptimizer instance"""
    global _optimizer_instance
    
    if _optimizer_instance is None:
        _optimizer_instance = WalkForwardOptimizer()
    
    return _optimizer_instance

