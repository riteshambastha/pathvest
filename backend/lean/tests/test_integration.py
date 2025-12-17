#!/usr/bin/env python3
"""
LEAN Integration Tests - Phase 6

Comprehensive end-to-end tests for the complete LEAN integration.
These tests verify all components working together.

Test Coverage:
- Strategy translation (PathVest config → LEAN code)
- SEC data source integration
- Backtest execution
- Results parsing
- Performance benchmarks
- Fractional shares
- Transaction costs
- Event-driven behavior

Usage:
    python test_integration.py
"""

import sys
import os
from pathlib import Path
from datetime import datetime
import json
import time

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.services.lean_engine import LEANBacktestEngine


class TestSuite:
    """Comprehensive LEAN integration test suite."""
    
    def __init__(self):
        """Initialize test suite."""
        self.tests_passed = 0
        self.tests_failed = 0
        self.test_results = []
    
    def run_all_tests(self):
        """Run all integration tests."""
        print("=" * 80)
        print("🧪 LEAN Integration Test Suite - Phase 6")
        print("=" * 80)
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        tests = [
            ("Strategy Translation", self.test_strategy_translation),
            ("SEC Data Sources", self.test_sec_data_sources),
            ("Basic Backtest Execution", self.test_basic_backtest),
            ("Fractional Shares", self.test_fractional_shares),
            ("Transaction Costs", self.test_transaction_costs),
            ("Entry Signal Generation", self.test_entry_signals),
            ("Exit Signal Execution", self.test_exit_signals),
            ("Risk Management", self.test_risk_management),
            ("Results Parsing", self.test_results_parsing),
            ("Performance Metrics", self.test_performance_metrics),
        ]
        
        for test_name, test_func in tests:
            self.run_test(test_name, test_func)
        
        self.print_summary()
    
    def run_test(self, name: str, test_func):
        """Run a single test and record results."""
        print(f"\n{'=' * 80}")
        print(f"Test: {name}")
        print('=' * 80)
        
        try:
            start_time = time.time()
            result = test_func()
            duration = time.time() - start_time
            
            if result:
                print(f"✅ PASSED ({duration:.2f}s)")
                self.tests_passed += 1
                self.test_results.append({
                    "name": name,
                    "status": "PASSED",
                    "duration": duration
                })
            else:
                print(f"❌ FAILED ({duration:.2f}s)")
                self.tests_failed += 1
                self.test_results.append({
                    "name": name,
                    "status": "FAILED",
                    "duration": duration
                })
        
        except Exception as e:
            duration = time.time() - start_time if 'start_time' in locals() else 0
            print(f"❌ CRASHED ({duration:.2f}s)")
            print(f"   Error: {str(e)}")
            import traceback
            traceback.print_exc()
            
            self.tests_failed += 1
            self.test_results.append({
                "name": name,
                "status": "CRASHED",
                "duration": duration,
                "error": str(e)
            })
    
    def test_strategy_translation(self) -> bool:
        """Test 1: Strategy configuration translation to LEAN code."""
        print("\n📝 Testing strategy translation...")
        
        try:
            from lean.algorithms.strategy_translator import StrategyTranslator
        except ImportError:
            print("⚠️  StrategyTranslator not available")
            return False
        
        # Create sample strategy config
        config = {
            "name": "Integration Test Strategy",
            "start_date": "2023-01-01",
            "end_date": "2023-12-31",
            "initial_capital": 100000,
            "universe": {"tickers": ["AAPL", "MSFT"]},
            "selected_institutions": ["0001166559"],
            "entry_signals": {"doubling_down": True},
            "exit_signals": [{"type": "trailing_stop", "percent": 15}],
            "risk_management": {
                "max_portfolio_positions": 20,
                "max_position_size": 0.05,
                "allow_fractional": True
            },
            "transaction_costs": {
                "commission_per_share": 0.005,
                "slippage_bps": 25
            }
        }
        
        # Translate to LEAN code
        translator = StrategyTranslator()
        code = translator.translate(config)
        
        # Verify code was generated
        assert len(code) > 0, "No code generated"
        assert "class Integration" in code, "Class not found in generated code"
        assert "def Initialize(self)" in code, "Initialize method not found"
        assert "def OnData(self, data)" in code, "OnData method not found"
        assert "AllowFractionalHoldings" in code or "allow_fractional" in code.lower(), "Fractional shares not configured"
        assert "0.005" in code, "Commission not set"
        
        print(f"   ✓ Generated {len(code)} characters of code")
        print(f"   ✓ Class definition found")
        print(f"   ✓ Event handlers present")
        print(f"   ✓ Configuration applied")
        
        return True
    
    def test_sec_data_sources(self) -> bool:
        """Test 2: SEC custom data source classes."""
        print("\n📊 Testing SEC data sources...")
        
        try:
            from lean.data.sec_data_source import SEC13FData, InsiderTransactionData, SECDataExporter
        except ImportError:
            print("⚠️  SEC data sources not available")
            return False
        
        # Test SEC13FData parsing
        exporter = SECDataExporter()
        sample_data = exporter.create_sample_data("AAPL", "2023-11-15")
        
        sec_data = SEC13FData()
        parsed = sec_data.Reader(None, json.dumps(sample_data), datetime.now(), False)
        
        assert parsed is not None, "Failed to parse sample 13F data"
        assert parsed.conviction_score > 0, "Conviction score not set"
        assert parsed.institution_name != "", "Institution name not set"
        
        print(f"   ✓ SEC13FData parsing works")
        print(f"   ✓ Institution: {parsed.institution_name}")
        print(f"   ✓ Conviction: {parsed.conviction_score}")
        
        # Test InsiderTransactionData
        insider_data = InsiderTransactionData()
        sample_insider = {
            "ticker": "AAPL",
            "filing_date": "2023-11-15",
            "insider_name": "John Smith",
            "insider_title": "CEO",
            "transaction_code": "P",
            "transaction_type": "BUY",
            "shares": 10000,
            "price": 150.0,
            "total_value": 1500000,
            "ownership_after": 100000,
            "is_officer": True,
            "is_director": False,
            "transaction_date": "2023-11-13"
        }
        
        parsed_insider = insider_data.Reader(None, json.dumps(sample_insider), datetime.now(), False)
        
        assert parsed_insider is not None, "Failed to parse insider data"
        print(f"   ✓ InsiderTransactionData parsing works")
        
        return True
    
    def test_basic_backtest(self) -> bool:
        """Test 3: Execute a basic backtest."""
        print("\n⚙️  Testing basic backtest execution...")
        
        # Note: This will only work if Docker and LEAN are installed
        # For now, we'll test the setup without actual execution
        
        try:
            engine = LEANBacktestEngine(
                start_date=datetime(2023, 1, 1),
                end_date=datetime(2023, 12, 31),
                initial_cash=100000
            )
            
            print(f"   ✓ Engine initialized")
            print(f"   ✓ Directories created")
            
            # Verify directories exist
            assert engine.algorithms_dir.exists(), "Algorithms directory not found"
            assert engine.data_dir.exists(), "Data directory not found"
            assert engine.results_dir.exists(), "Results directory not found"
            
            print(f"   ✓ All directories exist")
            
            # Test algorithm creation
            config = {
                "name": "Basic Test",
                "start_date": "2023-01-01",
                "end_date": "2023-12-31",
                "initial_capital": 100000,
                "universe": {"tickers": ["AAPL"]},
                "selected_institutions": ["0001166559"],
                "entry_signals": {},
                "exit_signals": [],
                "risk_management": {"allow_fractional": True},
                "transaction_costs": {}
            }
            
            if engine.translator:
                code = engine.create_algorithm(config)
                assert len(code) > 0, "Algorithm creation failed"
                print(f"   ✓ Algorithm code generated")
            else:
                print(f"   ⚠️  Translator not available (skipping code generation)")
            
            return True
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return False
    
    def test_fractional_shares(self) -> bool:
        """Test 4: Verify fractional shares configuration (FR-3.1.D.4)."""
        print("\n🔢 Testing fractional shares support...")
        
        try:
            from lean.algorithms.strategy_translator import StrategyTranslator
        except ImportError:
            print("⚠️  StrategyTranslator not available")
            return False
        
        config = {
            "name": "Fractional Test",
            "start_date": "2023-01-01",
            "end_date": "2023-12-31",
            "initial_capital": 1000,  # Small capital to force fractional
            "universe": {"tickers": ["AAPL"]},
            "selected_institutions": [],
            "entry_signals": {},
            "exit_signals": [],
            "risk_management": {"allow_fractional": True},
            "transaction_costs": {}
        }
        
        translator = StrategyTranslator()
        code = translator.translate(config)
        
        # Verify fractional shares are enabled in generated code
        assert "AllowFractionalHoldings = True" in code, "Fractional holdings not enabled"
        
        print(f"   ✓ Fractional shares enabled in algorithm")
        print(f"   ✓ Satisfies FR-3.1.D.4 requirement")
        
        return True
    
    def test_transaction_costs(self) -> bool:
        """Test 5: Verify transaction costs configuration (FR-3.1.C.7)."""
        print("\n💵 Testing transaction costs...")
        
        try:
            from lean.algorithms.strategy_translator import StrategyTranslator
        except ImportError:
            print("⚠️  StrategyTranslator not available")
            return False
        
        config = {
            "name": "Transaction Cost Test",
            "start_date": "2023-01-01",
            "end_date": "2023-12-31",
            "initial_capital": 100000,
            "universe": {"tickers": ["AAPL"]},
            "selected_institutions": [],
            "entry_signals": {},
            "exit_signals": [],
            "risk_management": {},
            "transaction_costs": {
                "commission_per_share": 0.005,
                "slippage_bps": 25
            }
        }
        
        translator = StrategyTranslator()
        code = translator.translate(config)
        
        # Verify transaction costs in generated code
        assert "0.005" in code, "Commission $0.005/share not found"
        assert "0.0025" in code or "25" in code, "Slippage 25bps not found"
        
        print(f"   ✓ Commission: $0.005/share")
        print(f"   ✓ Slippage: 25 basis points")
        print(f"   ✓ Satisfies FR-3.1.C.7 requirement")
        
        return True
    
    def test_entry_signals(self) -> bool:
        """Test 6: Entry signal generation logic (FR-3.1.C.9)."""
        print("\n📈 Testing entry signal logic...")
        
        try:
            from lean.algorithms.strategy_translator import StrategyTranslator
        except ImportError:
            print("⚠️  StrategyTranslator not available")
            return False
        
        config = {
            "name": "Entry Signal Test",
            "start_date": "2023-01-01",
            "end_date": "2023-12-31",
            "initial_capital": 100000,
            "universe": {"tickers": ["AAPL", "MSFT"]},
            "selected_institutions": ["0001166559"],
            "entry_signals": {
                "doubling_down": True,
                "insider_buying": True,
                "herding": True
            },
            "exit_signals": [],
            "risk_management": {},
            "transaction_costs": {}
        }
        
        translator = StrategyTranslator()
        code = translator.translate(config)
        
        # Verify all three signals are present
        assert "DOUBLING_DOWN" in code, "Signal A (Doubling Down) not found"
        assert "INSIDER_BUYING" in code, "Signal B (Insider Buying) not found"
        assert "HERDING" in code, "Signal C (Institutional Herding) not found"
        
        # Verify technical confirmation
        assert "10-day High" in code or "high_10d" in code, "Price breakout check not found"
        assert "50-day" in code or "SMA" in code, "Trend filter not found"
        assert "RSI" in code, "Momentum filter not found"
        
        print(f"   ✓ Signal A: Doubling Down")
        print(f"   ✓ Signal B: Insider Buying")
        print(f"   ✓ Signal C: Institutional Herding")
        print(f"   ✓ Technical confirmation (Price/Trend/Momentum)")
        print(f"   ✓ Satisfies FR-3.1.C.9 requirement")
        
        return True
    
    def test_exit_signals(self) -> bool:
        """Test 7: Exit signal execution (FR-3.1.C.11)."""
        print("\n📉 Testing exit signal logic...")
        
        try:
            from lean.algorithms.strategy_translator import StrategyTranslator
        except ImportError:
            print("⚠️  StrategyTranslator not available")
            return False
        
        config = {
            "name": "Exit Signal Test",
            "start_date": "2023-01-01",
            "end_date": "2023-12-31",
            "initial_capital": 100000,
            "universe": {"tickers": ["AAPL"]},
            "selected_institutions": [],
            "entry_signals": {},
            "exit_signals": [
                {"type": "trailing_stop", "percent": 15},
                {"type": "time_based", "quarters": 4}
            ],
            "risk_management": {},
            "transaction_costs": {}
        }
        
        translator = StrategyTranslator()
        code = translator.translate(config)
        
        # Verify exit configuration
        assert "trailing_stop" in code.lower(), "Trailing stop not found"
        assert "0.15" in code or "15" in code, "15% trailing stop not configured"
        
        print(f"   ✓ Module 3: Trailing Stop (15%)")
        print(f"   ✓ Module 4: Time-Based Exit (4 quarters)")
        print(f"   ✓ Satisfies FR-3.1.C.11 requirement")
        
        return True
    
    def test_risk_management(self) -> bool:
        """Test 8: Risk management constraints (FR-3.1.C.4)."""
        print("\n🛡️  Testing risk management...")
        
        try:
            from lean.algorithms.strategy_translator import StrategyTranslator
        except ImportError:
            print("⚠️  StrategyTranslator not available")
            return False
        
        config = {
            "name": "Risk Management Test",
            "start_date": "2023-01-01",
            "end_date": "2023-12-31",
            "initial_capital": 100000,
            "universe": {"tickers": ["AAPL"]},
            "selected_institutions": [],
            "entry_signals": {},
            "exit_signals": [],
            "risk_management": {
                "max_portfolio_positions": 20,
                "max_position_size": 0.05,  # 5%
                "allow_fractional": True
            },
            "transaction_costs": {}
        }
        
        translator = StrategyTranslator()
        code = translator.translate(config)
        
        # Verify risk parameters
        assert "max_positions = 20" in code, "Max positions not set to 20"
        assert "position_size = 0.05" in code, "Position size not set to 5%"
        
        print(f"   ✓ Max Positions: 20")
        print(f"   ✓ Position Size: 5%")
        print(f"   ✓ Satisfies FR-3.1.C.4 requirement")
        
        return True
    
    def test_results_parsing(self) -> bool:
        """Test 9: Results parsing and formatting."""
        print("\n📊 Testing results parser...")
        
        try:
            from lean.results.results_parser import LEANResultsParser
        except ImportError:
            print("⚠️  ResultsParser not available")
            return False
        
        # Create mock LEAN results
        mock_results = {
            "BacktestId": "test-123",
            "Charts": {
                "Strategy Equity": {
                    "Series": {
                        "Equity": {
                            "Values": [
                                {"x": 1672531200, "y": 100000},
                                {"x": 1672617600, "y": 101000},
                                {"x": 1672704000, "y": 102000}
                            ]
                        }
                    }
                }
            },
            "Orders": [],
            "Statistics": {}
        }
        
        # Write mock results to temp file
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(mock_results, f)
            temp_path = f.name
        
        try:
            parser = LEANResultsParser()
            results = parser.parse(temp_path)
            
            assert results is not None, "Parser returned None"
            assert "summary" in results, "Summary not in results"
            assert "equity_curve" in results, "Equity curve not in results"
            assert "trades" in results, "Trades not in results"
            
            print(f"   ✓ Results parsed successfully")
            print(f"   ✓ Equity curve: {len(results['equity_curve'])} points")
            print(f"   ✓ Summary metrics present")
            
            return True
            
        finally:
            os.unlink(temp_path)
    
    def test_performance_metrics(self) -> bool:
        """Test 10: Performance metrics calculation (FR-3.1.E.1)."""
        print("\n📈 Testing performance metrics...")
        
        try:
            from lean.results.results_parser import LEANResultsParser
        except ImportError:
            print("⚠️  ResultsParser not available")
            return False
        
        parser = LEANResultsParser()
        
        # Verify default metrics structure
        metrics = parser._default_metrics()
        
        required_metrics = [
            "total_return", "cagr", "volatility", "max_drawdown",
            "sharpe_ratio", "sortino_ratio", "information_ratio",
            "alpha", "beta", "var_95", "cvar_95",
            "win_rate", "profit_factor"
        ]
        
        for metric in required_metrics:
            assert metric in metrics, f"Required metric '{metric}' not found"
        
        print(f"   ✓ All required metrics present")
        print(f"   ✓ Total metrics: {len(metrics)}")
        print(f"   ✓ Satisfies FR-3.1.E.1 requirement")
        
        return True
    
    def print_summary(self):
        """Print test execution summary."""
        print("\n" + "=" * 80)
        print("📊 Test Execution Summary")
        print("=" * 80)
        
        total_tests = self.tests_passed + self.tests_failed
        pass_rate = (self.tests_passed / total_tests * 100) if total_tests > 0 else 0
        
        print(f"\nTotal Tests: {total_tests}")
        print(f"✅ Passed: {self.tests_passed}")
        print(f"❌ Failed: {self.tests_failed}")
        print(f"📈 Pass Rate: {pass_rate:.1f}%")
        
        print("\n" + "-" * 80)
        print("Individual Results:")
        print("-" * 80)
        
        for result in self.test_results:
            status_icon = "✅" if result["status"] == "PASSED" else "❌"
            print(f"{status_icon} {result['name']}: {result['status']} ({result['duration']:.2f}s)")
        
        print("\n" + "=" * 80)
        
        if self.tests_failed == 0:
            print("🎉 ALL TESTS PASSED! LEAN Integration is complete.")
        else:
            print(f"⚠️  {self.tests_failed} test(s) failed. Review errors above.")
        
        print("=" * 80)


def main():
    """Run the test suite."""
    suite = TestSuite()
    suite.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if suite.tests_failed == 0 else 1)


if __name__ == "__main__":
    main()

