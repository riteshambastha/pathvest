"""
LEAN Engine Adapter
Provides a clean interface to run backtests using the LEAN/QuantConnect engine
"""

import os
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import pandas as pd


class LEANAdapter:
    """
    Adapter for running backtests using the LEAN engine
    Handles algorithm generation, LEAN CLI execution, and result parsing
    """
    
    def __init__(self):
        self.lean_root = Path(__file__).parent.parent.parent / "lean"
        self.algorithms_dir = self.lean_root / "algorithms"
        self.data_dir = self.lean_root / "data"
        self.results_dir = self.lean_root / "results"
        
        # Ensure directories exist
        self.algorithms_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.results_dir.mkdir(parents=True, exist_ok=True)
    
    def verify_docker(self) -> bool:
        """Verify Docker is running and LEAN CLI is available"""
        try:
            # Check Docker
            result = subprocess.run(
                ["docker", "ps"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode != 0:
                print(f"❌ Docker not running: {result.stderr}")
                return False
            
            # Check LEAN CLI
            result = subprocess.run(
                ["lean", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode != 0:
                print(f"❌ LEAN CLI not found: {result.stderr}")
                return False
            
            print(f"✅ Docker and LEAN CLI verified")
            return True
            
        except FileNotFoundError:
            print(f"❌ Docker or LEAN CLI not installed")
            return False
        except subprocess.TimeoutExpired:
            print(f"❌ Docker or LEAN CLI timeout")
            return False
        except Exception as e:
            print(f"❌ Verification error: {e}")
            return False
    
    def generate_algorithm(
        self,
        signals: List[Dict],
        strategy_config: Dict,
        algorithm_name: str = "pathvest_strategy"
    ) -> Path:
        """
        Generate a LEAN algorithm Python file from PathVest signals and config
        
        Args:
            signals: List of trading signals with dates, tickers, actions
            strategy_config: Strategy configuration dict
            algorithm_name: Name for the algorithm file
            
        Returns:
            Path to generated algorithm file
        """
        
        # Extract config parameters
        start_date = strategy_config.get('start_date', '2024-01-01')
        end_date = strategy_config.get('end_date', '2024-12-31')
        initial_capital = strategy_config.get('initial_capital', 100000)
        
        # Group signals by ticker
        tickers = list(set([s['ticker'] for s in signals]))
        
        # Generate algorithm code
        algorithm_code = f'''"""
PathVest Strategy - Generated Algorithm for LEAN
Generated: {datetime.now().isoformat()}
"""

from AlgorithmImports import *
import json

class PathVestStrategy(QCAlgorithm):
    """
    PathVest institutional following strategy
    Trades based on SEC 13F filing signals
    """
    
    def Initialize(self):
        """Initialize algorithm"""
        # Set dates and capital
        self.SetStartDate({start_date.split('-')[0]}, {start_date.split('-')[1]}, {start_date.split('-')[2]})
        self.SetEndDate({end_date.split('-')[0]}, {end_date.split('-')[1]}, {end_date.split('-')[2]})
        self.SetCash({initial_capital})
        
        # Enable fractional shares
        self.Settings.FreePortfolioValuePercentage = 0.05
        
        # Set transaction models
        self.SetBrokerageModel(BrokerageName.InteractiveBrokersBrokerage, AccountType.Margin)
        
        # Add securities
        self.tickers = {tickers}
        self.symbols = {{}}
        for ticker in self.tickers:
            symbol = self.AddEquity(ticker, Resolution.Daily)
            symbol.FeeModel = ConstantFeeModel(0)  # Zero commission
            symbol.SlippageModel = ConstantSlippageModel(0.001)  # 0.1% slippage
            self.symbols[ticker] = symbol.Symbol
        
        # Load signals from JSON
        self.signals = {json.dumps(signals, indent=8)}
        
        # Convert signal dates to datetime
        self.signals_by_date = {{}}
        for signal in self.signals:
            date_str = signal['date']
            if date_str not in self.signals_by_date:
                self.signals_by_date[date_str] = []
            self.signals_by_date[date_str].append(signal)
        
        self.Debug(f"Loaded {{len(self.signals)}} signals for {{len(self.tickers)}} tickers")
    
    def OnData(self, data):
        """Main event handler called on each bar"""
        current_date = self.Time.strftime('%Y-%m-%d')
        
        # Check for signals on this date
        if current_date not in self.signals_by_date:
            return
        
        signals_today = self.signals_by_date[current_date]
        self.Debug(f"Processing {{len(signals_today)}} signals on {{current_date}}")
        
        for signal in signals_today:
            ticker = signal['ticker']
            action = signal['action']
            signal_strength = signal.get('signal_strength', 1.0)
            
            if ticker not in self.symbols:
                continue
            
            symbol = self.symbols[ticker]
            
            # Skip if no data for this symbol
            if not data.ContainsKey(symbol):
                self.Debug(f"No data for {{ticker}} on {{current_date}}")
                continue
            
            if action == 'BUY':
                # Calculate position size (max 20% of portfolio)
                max_position_value = self.Portfolio.TotalPortfolioValue * 0.20 * signal_strength
                current_price = data[symbol].Close
                
                if current_price > 0:
                    shares_to_buy = int(max_position_value / current_price)
                    
                    if shares_to_buy > 0 and self.Portfolio.Cash > shares_to_buy * current_price:
                        self.MarketOrder(symbol, shares_to_buy)
                        self.Debug(f"BUY {{shares_to_buy}} {{ticker}} @ ${{current_price:.2f}}")
            
            elif action == 'SELL':
                # Sell entire position
                if self.Portfolio[symbol].Invested:
                    shares_to_sell = self.Portfolio[symbol].Quantity
                    self.MarketOrder(symbol, -shares_to_sell)
                    current_price = data[symbol].Close
                    self.Debug(f"SELL {{shares_to_sell}} {{ticker}} @ ${{current_price:.2f}}")
    
    def OnEndOfAlgorithm(self):
        """Called at end of backtest"""
        self.Debug(f"Final Portfolio Value: ${{self.Portfolio.TotalPortfolioValue:.2f}}")
        self.Debug(f"Total Return: {{(self.Portfolio.TotalPortfolioValue / {initial_capital} - 1) * 100:.2f}}%")
'''
        
        # Write algorithm file
        algo_file = self.algorithms_dir / f"{algorithm_name}.py"
        algo_file.write_text(algorithm_code)
        
        print(f"✅ Generated LEAN algorithm: {algo_file}")
        return algo_file
    
    def run_backtest(self, algorithm_name: str) -> Optional[Dict]:
        """
        Run a LEAN backtest using the CLI
        
        Args:
            algorithm_name: Name of the algorithm to run (without .py extension)
            
        Returns:
            Dict with backtest results or None if failed
        """
        
        print(f"\n{'='*60}")
        print(f"🚀 Running LEAN Backtest: {algorithm_name}")
        print(f"{'='*60}\n")
        
        try:
            # Run LEAN CLI command
            result = subprocess.run(
                [
                    "lean", "backtest",
                    str(self.algorithms_dir / algorithm_name),
                    "--output", str(self.results_dir)
                ],
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
                cwd=str(self.lean_root)
            )
            
            # Print output
            print("LEAN Output:")
            print(result.stdout)
            
            if result.stderr:
                print("LEAN Errors/Warnings:")
                print(result.stderr)
            
            if result.returncode != 0:
                print(f"❌ LEAN backtest failed with return code {result.returncode}")
                return None
            
            # Parse results
            results = self.parse_results(algorithm_name)
            return results
            
        except subprocess.TimeoutExpired:
            print(f"❌ LEAN backtest timeout (>5 minutes)")
            return None
        except Exception as e:
            print(f"❌ LEAN backtest error: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def parse_results(self, algorithm_name: str) -> Optional[Dict]:
        """
        Parse LEAN backtest results from JSON output
        
        Args:
            algorithm_name: Name of the algorithm that was run
            
        Returns:
            Dict with parsed results
        """
        
        # Find the most recent results file
        results_files = list(self.results_dir.glob(f"**/backtests/**/results.json"))
        
        if not results_files:
            print(f"⚠️  No results.json found in {self.results_dir}")
            return None
        
        # Get most recent
        results_file = max(results_files, key=lambda p: p.stat().st_mtime)
        print(f"📊 Parsing results from: {results_file}")
        
        try:
            with open(results_file, 'r') as f:
                lean_results = json.load(f)
            
            # Extract key metrics
            statistics = lean_results.get('Statistics', {})
            runtime_stats = lean_results.get('RuntimeStatistics', {})
            
            # Parse to PathVest format
            results = {
                'engine': 'LEAN',
                'algorithm_name': algorithm_name,
                
                # Performance metrics
                'total_return': self._parse_percent(statistics.get('Total Net Profit', '0%')),
                'cagr': self._parse_percent(statistics.get('Compounding Annual Return', '0%')),
                'sharpe_ratio': float(statistics.get('Sharpe Ratio', '0')),
                'sortino_ratio': float(statistics.get('Sortino Ratio', '0')),
                'max_drawdown': self._parse_percent(statistics.get('Drawdown', '0%')),
                'volatility': self._parse_percent(statistics.get('Tracking Error', '0%')),
                
                # Trading metrics
                'total_trades': int(statistics.get('Total Trades', '0')),
                'win_rate': self._parse_percent(statistics.get('Win Rate', '0%')),
                'profit_loss_ratio': float(statistics.get('Profit-Loss Ratio', '0')),
                
                # Portfolio metrics
                'initial_capital': float(statistics.get('Equity', '100000').replace('$', '').replace(',', '')),
                'final_value': float(runtime_stats.get('Equity', '100000').replace('$', '').replace(',', '')),
                
                # Risk metrics
                'alpha': float(statistics.get('Alpha', '0')),
                'beta': float(statistics.get('Beta', '0')),
                'information_ratio': float(statistics.get('Information Ratio', '0')),
                
                # Raw statistics for reference
                'lean_statistics': statistics,
                'lean_runtime_stats': runtime_stats
            }
            
            print(f"\n✅ LEAN Backtest Results:")
            print(f"   Total Return: {results['total_return']*100:.2f}%")
            print(f"   Sharpe Ratio: {results['sharpe_ratio']:.2f}")
            print(f"   Max Drawdown: {results['max_drawdown']*100:.2f}%")
            print(f"   Total Trades: {results['total_trades']}")
            print()
            
            return results
            
        except Exception as e:
            print(f"❌ Error parsing LEAN results: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _parse_percent(self, percent_str: str) -> float:
        """Convert percentage string like '15.3%' to float like 0.153"""
        try:
            return float(percent_str.replace('%', '')) / 100.0
        except:
            return 0.0
    
    def run_full_backtest(
        self,
        signals: List[Dict],
        strategy_config: Dict,
        algorithm_name: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Run a complete LEAN backtest from signals to results
        
        Args:
            signals: Trading signals
            strategy_config: Strategy configuration
            algorithm_name: Optional custom algorithm name
            
        Returns:
            Dict with backtest results or None if failed
        """
        
        # Verify prerequisites
        if not self.verify_docker():
            return {
                'error': 'Docker or LEAN CLI not available',
                'engine': 'LEAN',
                'status': 'failed'
            }
        
        # Generate algorithm name
        if not algorithm_name:
            algorithm_name = f"pathvest_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Step 1: Generate algorithm
        try:
            algo_file = self.generate_algorithm(signals, strategy_config, algorithm_name)
        except Exception as e:
            print(f"❌ Failed to generate algorithm: {e}")
            return {
                'error': f'Algorithm generation failed: {e}',
                'engine': 'LEAN',
                'status': 'failed'
            }
        
        # Step 2: Run backtest
        results = self.run_backtest(algorithm_name)
        
        if results is None:
            return {
                'error': 'LEAN backtest execution failed',
                'engine': 'LEAN',
                'status': 'failed'
            }
        
        # Add metadata
        results['status'] = 'completed'
        results['signals_count'] = len(signals)
        results['strategy_config'] = strategy_config
        
        return results


# Test function
if __name__ == "__main__":
    print("Testing LEAN Adapter...")
    
    adapter = LEANAdapter()
    
    # Test 1: Verify Docker and LEAN CLI
    print("\n" + "="*60)
    print("Test 1: Verify Prerequisites")
    print("="*60)
    adapter.verify_docker()
    
    # Test 2: Generate sample algorithm
    print("\n" + "="*60)
    print("Test 2: Generate Sample Algorithm")
    print("="*60)
    
    sample_signals = [
        {'date': '2024-01-15', 'ticker': 'AAPL', 'action': 'BUY', 'signal_strength': 1.0},
        {'date': '2024-03-10', 'ticker': 'MSFT', 'action': 'BUY', 'signal_strength': 0.8},
        {'date': '2024-06-15', 'ticker': 'AAPL', 'action': 'SELL', 'signal_strength': 1.0},
    ]
    
    sample_config = {
        'start_date': '2024-01-01',
        'end_date': '2024-12-31',
        'initial_capital': 100000
    }
    
    try:
        algo_file = adapter.generate_algorithm(sample_signals, sample_config, "test_algorithm")
        print(f"✅ Generated: {algo_file}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("\n" + "="*60)
    print("LEAN Adapter Tests Complete")
    print("="*60)

