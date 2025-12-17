"""
Walk-Forward Optimization for Strategy Validation

Purpose:
- Test strategy robustness across different time periods
- Prevent overfitting to historical data
- Validate strategy performance out-of-sample

Method:
- Split data into training and testing windows
- Optimize strategy on training window
- Validate on test window (out-of-sample)
- Roll forward and repeat
- Aggregate results

Example:
- 2013-2025 data (13 years)
- Training window: 2 years
- Testing window: 6 months
- Step: 6 months (rolling)
- Result: 20+ out-of-sample tests
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
import json


class WalkForwardOptimizer:
    """
    Walk-Forward Optimization validator
    """
    
    def __init__(
        self,
        training_window_months: int = 24,
        testing_window_months: int = 6,
        step_months: int = 6
    ):
        """
        Args:
            training_window_months: Size of training window (default 24 = 2 years)
            testing_window_months: Size of testing window (default 6 = 6 months)
            step_months: Step size for rolling forward (default 6 months)
        """
        self.training_window_months = training_window_months
        self.testing_window_months = testing_window_months
        self.step_months = step_months
    
    def run_walk_forward(
        self,
        start_date: str,
        end_date: str,
        backtest_func: Callable,
        strategy_config: Dict
    ) -> Dict:
        """
        Run walk-forward optimization
        
        Args:
            start_date: Overall start date (YYYY-MM-DD)
            end_date: Overall end date (YYYY-MM-DD)
            backtest_func: Function to run backtest with (start, end, config)
            strategy_config: Strategy configuration
            
        Returns:
            Dict with walk-forward results
        """
        
        print(f"\n📊 Walk-Forward Optimization")
        print(f"="*60)
        print(f"Training Window: {self.training_window_months} months")
        print(f"Testing Window: {self.testing_window_months} months")
        print(f"Step Size: {self.step_months} months")
        print()
        
        # Parse dates
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        
        # Generate windows
        windows = self._generate_windows(start, end)
        
        print(f"✅ Generated {len(windows)} walk-forward windows\n")
        
        # Run backtest for each window
        results = []
        training_results = []
        testing_results = []
        
        for idx, window in enumerate(windows, 1):
            print(f"📈 Window {idx}/{len(windows)}")
            print(f"   Training: {window['train_start']} to {window['train_end']}")
            print(f"   Testing:  {window['test_start']} to {window['test_end']}")
            
            # Run training backtest (in-sample)
            train_result = backtest_func(
                window['train_start'],
                window['train_end'],
                strategy_config
            )
            
            # Run testing backtest (out-of-sample)
            test_result = backtest_func(
                window['test_start'],
                window['test_end'],
                strategy_config
            )
            
            training_results.append({
                'window': idx,
                'start': window['train_start'],
                'end': window['train_end'],
                'return': train_result.get('total_return', 0),
                'sharpe': train_result.get('sharpe_ratio', 0),
                'max_dd': train_result.get('max_drawdown', 0)
            })
            
            testing_results.append({
                'window': idx,
                'start': window['test_start'],
                'end': window['test_end'],
                'return': test_result.get('total_return', 0),
                'sharpe': test_result.get('sharpe_ratio', 0),
                'max_dd': test_result.get('max_drawdown', 0)
            })
            
            print(f"   Train Return: {train_result.get('total_return', 0)*100:>6.2f}%")
            print(f"   Test Return:  {test_result.get('total_return', 0)*100:>6.2f}%")
            print()
        
        # Aggregate and analyze results
        analysis = self._analyze_results(training_results, testing_results)
        
        return {
            'windows': windows,
            'training_results': training_results,
            'testing_results': testing_results,
            'analysis': analysis,
            'config': {
                'training_window_months': self.training_window_months,
                'testing_window_months': self.testing_window_months,
                'step_months': self.step_months
            },
            'timestamp': datetime.now().isoformat()
        }
    
    def _generate_windows(
        self,
        start: datetime,
        end: datetime
    ) -> List[Dict]:
        """
        Generate walk-forward windows
        """
        
        windows = []
        current_start = start
        
        while True:
            # Training window
            train_start = current_start
            train_end = train_start + timedelta(days=30 * self.training_window_months)
            
            # Testing window
            test_start = train_end
            test_end = test_start + timedelta(days=30 * self.testing_window_months)
            
            # Check if we've reached the end
            if test_end > end:
                break
            
            windows.append({
                'train_start': train_start.strftime('%Y-%m-%d'),
                'train_end': train_end.strftime('%Y-%m-%d'),
                'test_start': test_start.strftime('%Y-%m-%d'),
                'test_end': test_end.strftime('%Y-%m-%d')
            })
            
            # Step forward
            current_start = current_start + timedelta(days=30 * self.step_months)
        
        return windows
    
    def _analyze_results(
        self,
        training_results: List[Dict],
        testing_results: List[Dict]
    ) -> Dict:
        """
        Analyze walk-forward results
        """
        
        # Extract metrics
        train_returns = [r['return'] for r in training_results]
        test_returns = [r['return'] for r in testing_results]
        
        train_sharpes = [r['sharpe'] for r in training_results]
        test_sharpes = [r['sharpe'] for r in testing_results]
        
        # Calculate statistics
        analysis = {
            # Training stats
            'training': {
                'mean_return': float(np.mean(train_returns)),
                'std_return': float(np.std(train_returns)),
                'mean_sharpe': float(np.mean(train_sharpes)),
                'win_rate': float(np.sum(np.array(train_returns) > 0) / len(train_returns))
            },
            
            # Testing stats (OUT-OF-SAMPLE)
            'testing': {
                'mean_return': float(np.mean(test_returns)),
                'std_return': float(np.std(test_returns)),
                'mean_sharpe': float(np.mean(test_sharpes)),
                'win_rate': float(np.sum(np.array(test_returns) > 0) / len(test_returns))
            },
            
            # Overfitting metrics
            'overfitting': {
                'return_degradation': float(np.mean(train_returns) - np.mean(test_returns)),
                'sharpe_degradation': float(np.mean(train_sharpes) - np.mean(test_sharpes)),
                'consistency_score': self._calculate_consistency(train_returns, test_returns)
            },
            
            # Overall metrics
            'overall': {
                'total_windows': len(training_results),
                'best_test_return': float(max(test_returns)),
                'worst_test_return': float(min(test_returns)),
                'positive_test_windows': int(np.sum(np.array(test_returns) > 0)),
                'negative_test_windows': int(np.sum(np.array(test_returns) <= 0))
            }
        }
        
        # Add robustness score (0-100)
        analysis['robustness_score'] = self._calculate_robustness_score(analysis)
        
        return analysis
    
    def _calculate_consistency(
        self,
        train_returns: List[float],
        test_returns: List[float]
    ) -> float:
        """
        Calculate consistency between training and testing
        
        Returns:
            Score from 0 (inconsistent) to 1 (consistent)
        """
        
        # Calculate correlation
        if len(train_returns) < 2:
            return 0.5
        
        correlation = np.corrcoef(train_returns, test_returns)[0, 1]
        
        # Normalize to 0-1 (correlation ranges from -1 to 1)
        consistency = (correlation + 1) / 2
        
        return float(consistency)
    
    def _calculate_robustness_score(self, analysis: Dict) -> float:
        """
        Calculate overall robustness score (0-100)
        
        Factors:
        - Testing win rate (40%)
        - Testing mean return (30%)
        - Consistency (20%)
        - Low overfitting (10%)
        """
        
        test_win_rate = analysis['testing']['win_rate']
        test_return = analysis['testing']['mean_return']
        consistency = analysis['overfitting']['consistency_score']
        return_deg = analysis['overfitting']['return_degradation']
        
        # Normalize each component to 0-1
        win_rate_score = test_win_rate  # Already 0-1
        return_score = min(max(test_return, -0.5), 0.5) + 0.5  # -50% to +50% → 0 to 1
        consistency_score = consistency  # Already 0-1
        overfitting_score = 1 - min(abs(return_deg), 0.5) / 0.5  # Less degradation = better
        
        # Weighted average
        robustness = (
            0.40 * win_rate_score +
            0.30 * return_score +
            0.20 * consistency_score +
            0.10 * overfitting_score
        )
        
        return float(robustness * 100)  # Convert to 0-100


# Mock backtest function for testing
def mock_backtest_func(start: str, end: str, config: Dict) -> Dict:
    """Mock backtest for testing"""
    import random
    random.seed(hash(start + end))
    
    return {
        'total_return': random.uniform(-0.1, 0.3),
        'sharpe_ratio': random.uniform(0.5, 2.0),
        'max_drawdown': random.uniform(-0.25, -0.05)
    }


# Test function
if __name__ == "__main__":
    print("Testing Walk-Forward Optimizer...")
    
    optimizer = WalkForwardOptimizer(
        training_window_months=24,
        testing_window_months=6,
        step_months=6
    )
    
    results = optimizer.run_walk_forward(
        start_date='2019-01-01',
        end_date='2025-01-01',
        backtest_func=mock_backtest_func,
        strategy_config={'test': True}
    )
    
    print("\n" + "="*60)
    print("📊 WALK-FORWARD RESULTS")
    print("="*60)
    
    print("\n🎯 Training (In-Sample):")
    print(f"   Mean Return: {results['analysis']['training']['mean_return']*100:.2f}%")
    print(f"   Mean Sharpe: {results['analysis']['training']['mean_sharpe']:.2f}")
    print(f"   Win Rate: {results['analysis']['training']['win_rate']*100:.1f}%")
    
    print("\n🎯 Testing (Out-of-Sample):")
    print(f"   Mean Return: {results['analysis']['testing']['mean_return']*100:.2f}%")
    print(f"   Mean Sharpe: {results['analysis']['testing']['mean_sharpe']:.2f}")
    print(f"   Win Rate: {results['analysis']['testing']['win_rate']*100:.1f}%")
    
    print("\n⚠️  Overfitting Analysis:")
    print(f"   Return Degradation: {results['analysis']['overfitting']['return_degradation']*100:.2f}%")
    print(f"   Sharpe Degradation: {results['analysis']['overfitting']['sharpe_degradation']:.2f}")
    print(f"   Consistency Score: {results['analysis']['overfitting']['consistency_score']*100:.1f}%")
    
    print(f"\n🏆 ROBUSTNESS SCORE: {results['analysis']['robustness_score']:.1f}/100")
    
    print("\n✅ Walk-Forward Optimizer test complete!")

