"""
Stress Testing for Strategy Validation

Purpose:
- Test strategy performance under extreme market conditions
- Identify vulnerabilities and edge cases
- Assess downside risk in crisis scenarios

Stress Test Scenarios:
1. Market Crash (-30% in 3 months)
2. Flash Crash (-10% in 1 day, recovery in 1 week)
3. Bear Market (-20% over 12 months)
4. High Volatility (2x normal volatility)
5. Low Liquidity (slippage 2x)
6. Interest Rate Spike (+3% in 6 months)
7. Sector Rotation (tech -40%, value +20%)
8. Black Swan (5-sigma event)
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Callable
from datetime import datetime, timedelta


class StressTester:
    """
    Stress test strategy under extreme conditions
    """
    
    def __init__(self):
        # Define stress scenarios
        self.scenarios = {
            'market_crash': {
                'name': 'Market Crash 2008-style',
                'description': '-30% market drop in 3 months',
                'market_return': -0.30,
                'duration_days': 90,
                'volatility_multiplier': 2.5,
                'severity': 'extreme'
            },
            'flash_crash': {
                'name': 'Flash Crash',
                'description': '-10% in 1 day, quick recovery',
                'market_return': -0.10,
                'duration_days': 1,
                'volatility_multiplier': 5.0,
                'severity': 'high'
            },
            'bear_market': {
                'name': 'Prolonged Bear Market',
                'description': '-20% over 12 months',
                'market_return': -0.20,
                'duration_days': 365,
                'volatility_multiplier': 1.5,
                'severity': 'moderate'
            },
            'high_volatility': {
                'name': 'Volatility Spike',
                'description': '2x normal volatility',
                'market_return': 0.0,
                'duration_days': 180,
                'volatility_multiplier': 2.0,
                'severity': 'moderate'
            },
            'low_liquidity': {
                'name': 'Liquidity Crisis',
                'description': 'High slippage, wide spreads',
                'market_return': -0.10,
                'duration_days': 60,
                'volatility_multiplier': 1.8,
                'severity': 'high'
            },
            'interest_rate_shock': {
                'name': 'Interest Rate Shock',
                'description': '+3% rates in 6 months',
                'market_return': -0.15,
                'duration_days': 180,
                'volatility_multiplier': 1.3,
                'severity': 'moderate'
            },
            'sector_rotation': {
                'name': 'Sector Rotation Crisis',
                'description': 'Tech -40%, Value +20%',
                'market_return': -0.15,
                'duration_days': 120,
                'volatility_multiplier': 2.0,
                'severity': 'high'
            },
            'black_swan': {
                'name': 'Black Swan Event',
                'description': '5-sigma unprecedented event',
                'market_return': -0.40,
                'duration_days': 30,
                'volatility_multiplier': 4.0,
                'severity': 'catastrophic'
            }
        }
    
    def run_stress_tests(
        self,
        base_config: Dict,
        backtest_func: Callable,
        base_start_date: str,
        base_end_date: str,
        scenarios_to_test: Optional[List[str]] = None
    ) -> Dict:
        """
        Run stress tests on strategy
        
        Args:
            base_config: Base strategy configuration
            backtest_func: Function to run backtest
            base_start_date: Start date
            base_end_date: End date
            scenarios_to_test: List of scenario keys (None = all)
            
        Returns:
            Dict with stress test results
        """
        
        print(f"\n💥 Stress Testing Strategy")
        print(f"="*60)
        
        # Run baseline (normal conditions)
        print(f"📊 Running baseline backtest...")
        baseline_result = backtest_func(base_start_date, base_end_date, base_config)
        baseline_return = baseline_result.get('total_return', 0)
        baseline_sharpe = baseline_result.get('sharpe_ratio', 0)
        baseline_max_dd = baseline_result.get('max_drawdown', 0)
        
        print(f"   Baseline Return: {baseline_return*100:.2f}%")
        print(f"   Baseline Sharpe: {baseline_sharpe:.2f}")
        print()
        
        # Determine which scenarios to test
        if scenarios_to_test is None:
            scenarios_to_test = list(self.scenarios.keys())
        
        print(f"✅ Testing {len(scenarios_to_test)} stress scenarios\n")
        
        # Run stress tests
        results = []
        
        for scenario_key in scenarios_to_test:
            scenario = self.scenarios[scenario_key]
            
            print(f"💥 {scenario['name']}")
            print(f"   {scenario['description']}")
            
            # Modify config for stress scenario
            stress_config = self._apply_stress_scenario(base_config, scenario)
            
            # Run backtest under stress
            stress_result = self._simulate_stress_backtest(
                backtest_func,
                base_start_date,
                base_end_date,
                stress_config,
                scenario,
                baseline_result
            )
            
            # Calculate impact
            return_impact = stress_result['total_return'] - baseline_return
            sharpe_impact = stress_result['sharpe_ratio'] - baseline_sharpe
            dd_impact = stress_result['max_drawdown'] - baseline_max_dd
            
            results.append({
                'scenario_key': scenario_key,
                'scenario_name': scenario['name'],
                'description': scenario['description'],
                'severity': scenario['severity'],
                'baseline_return': baseline_return,
                'stress_return': stress_result['total_return'],
                'return_impact': return_impact,
                'baseline_sharpe': baseline_sharpe,
                'stress_sharpe': stress_result['sharpe_ratio'],
                'sharpe_impact': sharpe_impact,
                'baseline_max_dd': baseline_max_dd,
                'stress_max_dd': stress_result['max_drawdown'],
                'dd_impact': dd_impact,
                'survival_probability': stress_result['survival_probability']
            })
            
            print(f"   Stress Return: {stress_result['total_return']*100:>6.2f}% (Impact: {return_impact*100:+.2f}%)")
            print(f"   Stress Max DD: {stress_result['max_drawdown']*100:>6.2f}%")
            print()
        
        # Analyze results
        analysis = self._analyze_stress_results(results, baseline_result)
        
        print(f"✅ Stress Testing Complete!")
        print(f"   Worst Scenario: {analysis['worst_scenario']['scenario_name']}")
        print(f"   Worst Return: {analysis['worst_scenario']['stress_return']*100:.2f}%")
        print(f"   Risk Score: {analysis['risk_score']:.1f}/100")
        
        return {
            'baseline': {
                'total_return': baseline_return,
                'sharpe_ratio': baseline_sharpe,
                'max_drawdown': baseline_max_dd
            },
            'stress_results': results,
            'analysis': analysis,
            'timestamp': datetime.now().isoformat()
        }
    
    def _apply_stress_scenario(
        self,
        base_config: Dict,
        scenario: Dict
    ) -> Dict:
        """
        Apply stress scenario modifications to config
        """
        
        stress_config = base_config.copy()
        
        # Increase transaction costs during stress
        if 'commission_pct' in stress_config:
            stress_config['commission_pct'] *= 1.5
        
        # Increase slippage during low liquidity
        if scenario['severity'] in ['high', 'extreme', 'catastrophic']:
            stress_config['slippage_factor'] = stress_config.get('slippage_factor', 0.001) * 2
        
        return stress_config
    
    def _simulate_stress_backtest(
        self,
        backtest_func: Callable,
        start_date: str,
        end_date: str,
        stress_config: Dict,
        scenario: Dict,
        baseline_result: Dict
    ) -> Dict:
        """
        Simulate backtest under stress conditions
        
        This applies stress multipliers to baseline results
        """
        
        # Run backtest (or simulate based on baseline)
        # For now, we'll simulate by applying stress multipliers
        
        baseline_return = baseline_result.get('total_return', 0)
        baseline_volatility = baseline_result.get('volatility', 0.15)
        baseline_max_dd = baseline_result.get('max_drawdown', -0.10)
        
        # Apply market stress
        market_impact = scenario['market_return']
        volatility_mult = scenario['volatility_multiplier']
        
        # Estimate stressed return
        # Strategy will be impacted by market but may have some protection
        beta = 0.7  # Assume strategy has 0.7 beta to market
        stress_return = baseline_return + (market_impact * beta)
        
        # Increase drawdown under stress
        stress_max_dd = baseline_max_dd * volatility_mult
        stress_max_dd = max(stress_max_dd, market_impact * 1.2)  # At least 1.2x market drop
        
        # Stressed volatility
        stress_volatility = baseline_volatility * volatility_mult
        
        # Stressed Sharpe
        stress_sharpe = stress_return / stress_volatility if stress_volatility > 0 else 0
        
        # Survival probability (probability strategy doesn't blow up)
        if stress_max_dd < -0.50:  # More than 50% drawdown
            survival_prob = 0.5
        elif stress_max_dd < -0.30:
            survival_prob = 0.7
        elif stress_max_dd < -0.20:
            survival_prob = 0.9
        else:
            survival_prob = 0.99
        
        return {
            'total_return': float(stress_return),
            'sharpe_ratio': float(stress_sharpe),
            'max_drawdown': float(stress_max_dd),
            'volatility': float(stress_volatility),
            'survival_probability': float(survival_prob)
        }
    
    def _analyze_stress_results(
        self,
        results: List[Dict],
        baseline_result: Dict
    ) -> Dict:
        """
        Analyze stress test results
        """
        
        # Find worst and best scenarios
        worst_idx = np.argmin([r['stress_return'] for r in results])
        best_idx = np.argmax([r['stress_return'] for r in results])
        
        # Calculate average impacts
        avg_return_impact = float(np.mean([r['return_impact'] for r in results]))
        avg_dd_impact = float(np.mean([abs(r['dd_impact']) for r in results]))
        
        # Count severe scenarios
        severe_scenarios = [r for r in results if r['severity'] in ['extreme', 'catastrophic']]
        severe_survival = np.mean([r['survival_probability'] for r in severe_scenarios]) if severe_scenarios else 1.0
        
        # Calculate risk score (0-100, lower is riskier)
        # Based on: worst return, avg drawdown, survival probability
        worst_return = results[worst_idx]['stress_return']
        risk_from_return = max(0, min(100, (worst_return + 0.5) * 100))  # -50% return = 0 score
        risk_from_dd = max(0, min(100, (1 - avg_dd_impact) * 100))
        risk_from_survival = severe_survival * 100
        
        risk_score = 0.4 * risk_from_return + 0.3 * risk_from_dd + 0.3 * risk_from_survival
        
        return {
            'worst_scenario': results[worst_idx],
            'best_scenario': results[best_idx],
            'avg_return_impact': avg_return_impact,
            'avg_dd_impact': avg_dd_impact,
            'severe_survival_rate': float(severe_survival),
            'risk_score': float(risk_score),
            'scenarios_passed': sum(1 for r in results if r['stress_return'] > 0),
            'scenarios_failed': sum(1 for r in results if r['stress_return'] < -0.30)
        }


# Mock backtest for testing
def mock_backtest_func(start: str, end: str, config: Dict) -> Dict:
    """Mock backtest for testing"""
    import random
    random.seed(hash(start + end + str(config)))
    
    return {
        'total_return': random.uniform(0.10, 0.30),
        'sharpe_ratio': random.uniform(0.8, 1.5),
        'max_drawdown': random.uniform(-0.20, -0.10),
        'volatility': random.uniform(0.12, 0.18)
    }


# Test function
if __name__ == "__main__":
    print("Testing Stress Tester...")
    
    tester = StressTester()
    
    base_config = {
        'initial_capital': 100000,
        'position_size': 0.05,
        'commission_pct': 0.001,
        'slippage_factor': 0.0005
    }
    
    # Run stress tests
    results = tester.run_stress_tests(
        base_config=base_config,
        backtest_func=mock_backtest_func,
        base_start_date='2024-01-01',
        base_end_date='2024-12-31',
        scenarios_to_test=None  # Test all scenarios
    )
    
    print("\n" + "="*60)
    print("💥 STRESS TEST RESULTS")
    print("="*60)
    
    print("\n📊 Baseline Performance:")
    print(f"   Return: {results['baseline']['total_return']*100:.2f}%")
    print(f"   Sharpe: {results['baseline']['sharpe_ratio']:.2f}")
    print(f"   Max DD: {results['baseline']['max_drawdown']*100:.2f}%")
    
    print("\n💥 Worst Case Scenario:")
    worst = results['analysis']['worst_scenario']
    print(f"   Scenario: {worst['scenario_name']}")
    print(f"   Return: {worst['stress_return']*100:.2f}%")
    print(f"   Max DD: {worst['stress_max_dd']*100:.2f}%")
    print(f"   Survival Prob: {worst['survival_probability']*100:.0f}%")
    
    print("\n📈 Summary:")
    print(f"   Avg Return Impact: {results['analysis']['avg_return_impact']*100:.2f}%")
    print(f"   Severe Survival Rate: {results['analysis']['severe_survival_rate']*100:.0f}%")
    print(f"   Scenarios Passed: {results['analysis']['scenarios_passed']}/{len(results['stress_results'])}")
    
    print(f"\n🏆 RISK SCORE: {results['analysis']['risk_score']:.1f}/100")
    print("   (Higher = More Resilient)")
    
    print("\n✅ Stress Tester test complete!")

