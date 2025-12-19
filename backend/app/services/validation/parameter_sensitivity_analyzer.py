"""
Parameter Sensitivity Analyzer
Tests strategy robustness across parameter space to identify overfitting
"""

from typing import List, Dict, Any, Tuple, Optional
import itertools

from app.schemas.validation_request import ParameterSensitivityConfig, ParameterSensitivityRequest
from app.schemas.validation_response import ParameterSensitivityResponse
from app.schemas.backtest_request import StrategyConfig

# LEAN engine imports commented out until LEAN worker is implemented
# from lean_engine.worker.backtest_worker import get_backtest_worker


class ParameterSensitivityAnalyzer:
    """
    Parameter sensitivity analyzer
    
    Purpose:
    - Test strategy across 2D parameter grid
    - Identify "robustness islands" (broad regions of profitability)
    - Detect overfitting (single parameter peak surrounded by poor performance)
    
    Output:
    - Heatmap matrix for visualization
    - Best parameter combination
    - Robustness metrics
    """
    
    def __init__(self):
        """Initialize parameter sensitivity analyzer"""
        # TODO: Initialize backtest worker when LEAN engine is implemented
        self.backtest_worker = None  # get_backtest_worker()
    
    async def run_sensitivity_analysis(
        self,
        request: ParameterSensitivityRequest,
        progress_callback: callable = None
    ) -> ParameterSensitivityResponse:
        """
        Run parameter sensitivity analysis
        
        Args:
            request: ParameterSensitivityRequest configuration
            progress_callback: Optional callback(progress_pct, message)
        
        Returns:
            ParameterSensitivityResponse with heatmap and robustness metrics
        """
        config = request.sensitivity_config
        
        if progress_callback:
            progress_callback(5, "Generating parameter grid...")
        
        # Generate parameter combinations
        param1_values = config.parameter1_values
        param2_values = config.parameter2_values
        total_combinations = len(param1_values) * len(param2_values)
        
        # Initialize results matrix
        results_matrix = [[0.0 for _ in param2_values] for _ in param1_values]
        
        # Test each combination
        combination_index = 0
        
        for i, param1_val in enumerate(param1_values):
            for j, param2_val in enumerate(param2_values):
                combination_index += 1
                
                if progress_callback:
                    progress_pct = 10 + (80 * combination_index / total_combinations)
                    progress_callback(
                        progress_pct,
                        f"Testing combination {combination_index}/{total_combinations}: "
                        f"{config.parameter1_name}={param1_val}, {config.parameter2_name}={param2_val}"
                    )
                
                # Create strategy with these parameters
                test_strategy = self._apply_parameters(
                    request.base_strategy,
                    {
                        config.parameter1_name: param1_val,
                        config.parameter2_name: param2_val
                    }
                )
                
                # Run backtest (mock for now)
                # In production: result = await self.backtest_worker.execute_backtest(...)
                metric_value = self._mock_backtest_metric(
                    config.metric,
                    param1_val,
                    param2_val,
                    config.parameter1_name,
                    config.parameter2_name
                )
                
                results_matrix[i][j] = metric_value
        
        if progress_callback:
            progress_callback(95, "Analyzing robustness...")
        
        # Find best parameter combination
        best_i, best_j, best_value = self._find_best_combination(results_matrix)
        
        # Calculate robustness metrics
        robust_region_size = self._calculate_robust_region_size(
            results_matrix,
            best_value,
            threshold=0.90
        )
        
        return ParameterSensitivityResponse(
            validation_id=f"ps_{id(request)}",
            status='completed',
            parameter1_name=config.parameter1_name,
            parameter1_values=param1_values,
            parameter2_name=config.parameter2_name,
            parameter2_values=param2_values,
            metric_name=config.metric,
            heatmap_matrix=results_matrix,
            best_param1_value=param1_values[best_i],
            best_param2_value=param2_values[best_j],
            best_metric_value=best_value,
            robust_region_size=robust_region_size,
            total_combinations=total_combinations
        )
    
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
    
    def _mock_backtest_metric(
        self,
        metric_name: str,
        param1_val: Any,
        param2_val: Any,
        param1_name: str,
        param2_name: str
    ) -> float:
        """
        Mock backtest metric calculation
        
        Creates realistic parameter sensitivity surface with:
        - One optimal region
        - Gradual degradation away from optimal
        - Some noise
        """
        import random
        import math
        
        # Define optimal values (example)
        optimal_values = {
            'exit_rules.trailing_stop_percent': 0.15,
            'entry_signals.technical_confirmation.sma_period': 50,
            'position_sizing.rank_buffer': 5,
            'conviction_weights.herding': 0.6
        }
        
        # Get optimal for these parameters
        optimal1 = optimal_values.get(param1_name, param1_val)
        optimal2 = optimal_values.get(param2_name, param2_val)
        
        # Calculate distance from optimal
        if isinstance(param1_val, (int, float)) and isinstance(optimal1, (int, float)):
            dist1 = abs(float(param1_val) - float(optimal1)) / float(optimal1)
        else:
            dist1 = 0.1 if param1_val != optimal1 else 0
        
        if isinstance(param2_val, (int, float)) and isinstance(optimal2, (int, float)):
            dist2 = abs(float(param2_val) - float(optimal2)) / float(optimal2)
        else:
            dist2 = 0.1 if param2_val != optimal2 else 0
        
        # Metric-specific base values
        base_values = {
            'sharpe_ratio': 1.3,
            'cagr': 0.085,
            'max_drawdown': -0.20,
            'sortino_ratio': 1.8
        }
        
        base_value = base_values.get(metric_name, 1.0)
        
        # Apply gaussian degradation
        degradation = math.exp(-2 * (dist1**2 + dist2**2))
        
        # Add noise
        noise = random.uniform(-0.05, 0.05)
        
        result = base_value * degradation + noise
        
        # Ensure reasonable bounds
        if 'drawdown' in metric_name:
            result = max(result, -0.50)
        else:
            result = max(result, 0.1)
        
        return result
    
    def _find_best_combination(
        self,
        matrix: List[List[float]]
    ) -> Tuple[int, int, float]:
        """
        Find best parameter combination in matrix
        
        Args:
            matrix: Results matrix
        
        Returns:
            (best_i, best_j, best_value)
        """
        best_i = 0
        best_j = 0
        best_value = matrix[0][0]
        
        for i in range(len(matrix)):
            for j in range(len(matrix[i])):
                if matrix[i][j] > best_value:
                    best_value = matrix[i][j]
                    best_i = i
                    best_j = j
        
        return best_i, best_j, best_value
    
    def _calculate_robust_region_size(
        self,
        matrix: List[List[float]],
        best_value: float,
        threshold: float = 0.90
    ) -> int:
        """
        Calculate size of robust region
        
        A robust region is defined as parameter combinations that achieve
        at least `threshold` (e.g., 90%) of the best performance.
        
        Args:
            matrix: Results matrix
            best_value: Best metric value
            threshold: Percentage of best value to be considered robust
        
        Returns:
            Number of combinations in robust region
        """
        cutoff = best_value * threshold
        
        count = 0
        for row in matrix:
            for value in row:
                if value >= cutoff:
                    count += 1
        
        return count


# Singleton instance
_analyzer_instance = None


def get_parameter_sensitivity_analyzer() -> ParameterSensitivityAnalyzer:
    """Get singleton ParameterSensitivityAnalyzer instance"""
    global _analyzer_instance
    
    if _analyzer_instance is None:
        _analyzer_instance = ParameterSensitivityAnalyzer()
    
    return _analyzer_instance

