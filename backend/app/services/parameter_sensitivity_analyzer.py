"""
Parameter Sensitivity Analysis

Purpose:
- Test how strategy performance changes with different parameters
- Identify stable vs unstable parameter ranges
- Prevent over-optimization to specific parameter values

Method:
- Vary each parameter across a range
- Run backtest for each parameter combination
- Generate heatmap data showing performance sensitivity
- Calculate stability scores

Example Parameters to Test:
- Position size (3%, 5%, 7%, 10%)
- Stop loss (5%, 10%, 15%, 20%)
- Take profit (15%, 20%, 25%, 30%)
- Minimum conviction score (60, 70, 80, 90)
- Rebalancing frequency (weekly, monthly, quarterly)
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Callable
from datetime import datetime
import itertools


class ParameterSensitivityAnalyzer:
    """
    Analyze strategy sensitivity to parameter variations
    """
    
    def __init__(self):
        pass
    
    def run_sensitivity_analysis(
        self,
        base_config: Dict,
        parameters_to_test: Dict[str, List],
        backtest_func: Callable,
        start_date: str,
        end_date: str,
        max_tests: int = 100
    ) -> Dict:
        """
        Run parameter sensitivity analysis
        
        Args:
            base_config: Base strategy configuration
            parameters_to_test: Dict of {param_name: [list of values to test]}
            backtest_func: Function to run backtest
            start_date: Start date for backtests
            end_date: End date for backtests
            max_tests: Maximum number of parameter combinations to test
            
        Returns:
            Dict with sensitivity results
        """
        
        print(f"\n🔬 Parameter Sensitivity Analysis")
        print(f"="*60)
        print(f"Parameters to test: {list(parameters_to_test.keys())}")
        print(f"Date range: {start_date} to {end_date}")
        print()
        
        # Generate parameter combinations
        param_names = list(parameters_to_test.keys())
        param_values = list(parameters_to_test.values())
        
        # Generate all combinations
        all_combinations = list(itertools.product(*param_values))
        
        # Limit number of tests
        if len(all_combinations) > max_tests:
            print(f"⚠️  {len(all_combinations)} combinations found, limiting to {max_tests}")
            # Use evenly spaced sampling
            indices = np.linspace(0, len(all_combinations)-1, max_tests, dtype=int)
            all_combinations = [all_combinations[i] for i in indices]
        
        print(f"✅ Testing {len(all_combinations)} parameter combinations\n")
        
        # Run backtests
        results = []
        
        for idx, combination in enumerate(all_combinations, 1):
            # Create config with this parameter combination
            test_config = base_config.copy()
            param_dict = dict(zip(param_names, combination))
            test_config.update(param_dict)
            
            # Display current test
            if idx % 10 == 1 or idx == len(all_combinations):
                param_str = ', '.join([f"{k}={v}" for k, v in param_dict.items()])
                print(f"📊 Test {idx}/{len(all_combinations)}: {param_str[:50]}")
            
            # Run backtest
            backtest_result = backtest_func(start_date, end_date, test_config)
            
            # Store result
            results.append({
                'params': param_dict,
                'total_return': backtest_result.get('total_return', 0),
                'sharpe_ratio': backtest_result.get('sharpe_ratio', 0),
                'max_drawdown': backtest_result.get('max_drawdown', 0),
                'volatility': backtest_result.get('volatility', 0)
            })
        
        # Analyze results
        analysis = self._analyze_sensitivity(
            results,
            param_names,
            parameters_to_test
        )
        
        print(f"\n✅ Sensitivity Analysis Complete!")
        print(f"   Best Return: {analysis['best_result']['total_return']*100:.2f}%")
        print(f"   Worst Return: {analysis['worst_result']['total_return']*100:.2f}%")
        print(f"   Range: {analysis['performance_range']*100:.2f}%")
        print(f"   Stability Score: {analysis['stability_score']:.1f}/100")
        
        return {
            'results': results,
            'analysis': analysis,
            'config': {
                'base_config': base_config,
                'parameters_tested': parameters_to_test,
                'num_tests': len(results)
            },
            'timestamp': datetime.now().isoformat()
        }
    
    def _analyze_sensitivity(
        self,
        results: List[Dict],
        param_names: List[str],
        parameters_to_test: Dict
    ) -> Dict:
        """
        Analyze sensitivity results
        """
        
        # Extract returns
        returns = [r['total_return'] for r in results]
        sharpes = [r['sharpe_ratio'] for r in results]
        
        # Find best and worst
        best_idx = np.argmax(returns)
        worst_idx = np.argmin(returns)
        
        # Calculate statistics
        mean_return = float(np.mean(returns))
        std_return = float(np.std(returns))
        median_return = float(np.median(returns))
        
        # Performance range (how much variation)
        performance_range = float(max(returns) - min(returns))
        
        # Calculate parameter impact (which parameters matter most)
        param_impacts = {}
        
        for param_name in param_names:
            # Group results by this parameter's value
            param_returns = {}
            for result in results:
                param_value = result['params'][param_name]
                if param_value not in param_returns:
                    param_returns[param_value] = []
                param_returns[param_value].append(result['total_return'])
            
            # Calculate variance across parameter values
            param_means = [np.mean(returns) for returns in param_returns.values()]
            param_variance = float(np.std(param_means))
            
            param_impacts[param_name] = {
                'impact_score': param_variance,
                'by_value': {str(k): float(np.mean(v)) for k, v in param_returns.items()}
            }
        
        # Rank parameters by impact
        ranked_params = sorted(
            param_impacts.items(),
            key=lambda x: x[1]['impact_score'],
            reverse=True
        )
        
        # Calculate stability score (0-100)
        # Lower variance = higher stability
        cv = std_return / abs(mean_return) if mean_return != 0 else 999
        stability_score = max(0, min(100, 100 * (1 - cv)))
        
        # Generate heatmap data (for 2-parameter case)
        heatmap_data = None
        if len(param_names) == 2:
            heatmap_data = self._generate_heatmap_data(
                results,
                param_names,
                parameters_to_test
            )
        
        return {
            # Overall stats
            'mean_return': mean_return,
            'median_return': median_return,
            'std_return': std_return,
            'performance_range': performance_range,
            
            # Best/Worst
            'best_result': {
                'params': results[best_idx]['params'],
                'total_return': results[best_idx]['total_return'],
                'sharpe_ratio': results[best_idx]['sharpe_ratio']
            },
            'worst_result': {
                'params': results[worst_idx]['params'],
                'total_return': results[worst_idx]['total_return'],
                'sharpe_ratio': results[worst_idx]['sharpe_ratio']
            },
            
            # Parameter impacts
            'parameter_impacts': param_impacts,
            'ranked_parameters': [p[0] for p in ranked_params],
            
            # Stability
            'stability_score': float(stability_score),
            'coefficient_of_variation': float(cv),
            
            # Heatmap (if 2 parameters)
            'heatmap_data': heatmap_data
        }
    
    def _generate_heatmap_data(
        self,
        results: List[Dict],
        param_names: List[str],
        parameters_to_test: Dict
    ) -> Dict:
        """
        Generate 2D heatmap data for visualization
        """
        
        if len(param_names) != 2:
            return None
        
        param1_name, param2_name = param_names
        param1_values = parameters_to_test[param1_name]
        param2_values = parameters_to_test[param2_name]
        
        # Create 2D grid
        heatmap = np.zeros((len(param1_values), len(param2_values)))
        
        for result in results:
            p1_val = result['params'][param1_name]
            p2_val = result['params'][param2_name]
            
            try:
                i = param1_values.index(p1_val)
                j = param2_values.index(p2_val)
                heatmap[i, j] = result['total_return']
            except (ValueError, IndexError):
                continue
        
        return {
            'param1_name': param1_name,
            'param2_name': param2_name,
            'param1_values': [str(v) for v in param1_values],
            'param2_values': [str(v) for v in param2_values],
            'returns_grid': heatmap.tolist()
        }
    
    def run_single_parameter_sweep(
        self,
        base_config: Dict,
        parameter_name: str,
        parameter_values: List,
        backtest_func: Callable,
        start_date: str,
        end_date: str
    ) -> Dict:
        """
        Sweep a single parameter while holding others constant
        
        Useful for quick analysis of one parameter's impact
        """
        
        print(f"\n🔍 Single Parameter Sweep: {parameter_name}")
        print(f"   Values: {parameter_values}")
        print()
        
        results = []
        
        for idx, value in enumerate(parameter_values, 1):
            print(f"   Testing {parameter_name}={value} ({idx}/{len(parameter_values)})")
            
            test_config = base_config.copy()
            test_config[parameter_name] = value
            
            backtest_result = backtest_func(start_date, end_date, test_config)
            
            results.append({
                'value': value,
                'total_return': backtest_result.get('total_return', 0),
                'sharpe_ratio': backtest_result.get('sharpe_ratio', 0),
                'max_drawdown': backtest_result.get('max_drawdown', 0)
            })
        
        # Find optimal value
        best_idx = np.argmax([r['total_return'] for r in results])
        
        print(f"\n✅ Best {parameter_name}: {results[best_idx]['value']}")
        print(f"   Return: {results[best_idx]['total_return']*100:.2f}%")
        
        return {
            'parameter_name': parameter_name,
            'results': results,
            'optimal_value': results[best_idx]['value'],
            'optimal_return': results[best_idx]['total_return']
        }


# Mock backtest for testing
def mock_backtest_func(start: str, end: str, config: Dict) -> Dict:
    """Mock backtest for testing"""
    import random
    
    # Make performance sensitive to parameters
    position_size = config.get('position_size', 0.05)
    stop_loss = config.get('stop_loss', 0.10)
    
    # Optimal around position_size=0.05, stop_loss=0.10
    position_penalty = abs(position_size - 0.05) * 2
    stop_penalty = abs(stop_loss - 0.10) * 0.5
    
    base_return = 0.20
    penalty = position_penalty + stop_penalty
    
    random.seed(hash(str(config)))
    noise = random.uniform(-0.05, 0.05)
    
    final_return = base_return - penalty + noise
    
    return {
        'total_return': final_return,
        'sharpe_ratio': final_return / 0.15,
        'max_drawdown': -0.15,
        'volatility': 0.15
    }


# Test function
if __name__ == "__main__":
    print("Testing Parameter Sensitivity Analyzer...")
    
    analyzer = ParameterSensitivityAnalyzer()
    
    # Define parameters to test
    parameters_to_test = {
        'position_size': [0.03, 0.05, 0.07, 0.10],
        'stop_loss': [0.05, 0.10, 0.15, 0.20]
    }
    
    base_config = {
        'initial_capital': 100000,
        'position_size': 0.05,
        'stop_loss': 0.10
    }
    
    # Run analysis
    results = analyzer.run_sensitivity_analysis(
        base_config=base_config,
        parameters_to_test=parameters_to_test,
        backtest_func=mock_backtest_func,
        start_date='2024-01-01',
        end_date='2024-12-31',
        max_tests=100
    )
    
    print("\n" + "="*60)
    print("📊 SENSITIVITY ANALYSIS RESULTS")
    print("="*60)
    
    print("\n📈 Performance Statistics:")
    print(f"   Mean Return: {results['analysis']['mean_return']*100:.2f}%")
    print(f"   Std Return: {results['analysis']['std_return']*100:.2f}%")
    print(f"   Performance Range: {results['analysis']['performance_range']*100:.2f}%")
    
    print("\n🎯 Best Configuration:")
    best = results['analysis']['best_result']
    print(f"   Params: {best['params']}")
    print(f"   Return: {best['total_return']*100:.2f}%")
    
    print("\n📊 Parameter Impacts (ranked):")
    for param_name in results['analysis']['ranked_parameters']:
        impact = results['analysis']['parameter_impacts'][param_name]
        print(f"   {param_name:20s} Impact: {impact['impact_score']:.4f}")
    
    print(f"\n🏆 STABILITY SCORE: {results['analysis']['stability_score']:.1f}/100")
    
    # Test single parameter sweep
    print("\n" + "="*60)
    sweep_results = analyzer.run_single_parameter_sweep(
        base_config=base_config,
        parameter_name='position_size',
        parameter_values=[0.03, 0.04, 0.05, 0.06, 0.07, 0.08, 0.09, 0.10],
        backtest_func=mock_backtest_func,
        start_date='2024-01-01',
        end_date='2024-12-31'
    )
    
    print("\n✅ Parameter Sensitivity Analyzer test complete!")

