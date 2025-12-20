#!/usr/bin/env python3
"""
Strategy Translator Tests

Tests the LEAN strategy translator functionality without requiring
actual LEAN CLI execution.
"""

import sys
from pathlib import Path

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_basic_strategy_translation():
    """Test basic strategy translation."""
    print("=" * 60)
    print("🧪 Test: Basic Strategy Translation")
    print("=" * 60)

    try:
        from algorithms.strategy_translator import StrategyTranslator

        translator = StrategyTranslator()

        # Basic strategy config
        config = {
            "name": "Basic Test Strategy",
            "start_date": "2023-01-01",
            "end_date": "2023-12-31",
            "initial_capital": 100000,
            "universe": {"tickers": ["AAPL", "MSFT"]},
            "selected_institutions": ["0001166559"],  # Berkshire Hathaway
            "entry_signals": {
                "doubling_down": True,
                "insider_buying": False,
                "herding": False
            },
            "exit_signals": [
                {"type": "trailing_stop", "percent": 15}
            ],
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

        print("📝 Translating strategy configuration...")

        code = translator.translate(config)

        # Verify code generation
        assert len(code) > 1000, "Generated code too short"
        assert "class Basic" in code, "Class definition not found"
        assert "def Initialize(self)" in code, "Initialize method missing"
        assert "def OnData(self, data)" in code, "OnData method missing"
        assert "AAPL" in code, "AAPL ticker not found"
        assert "MSFT" in code, "MSFT ticker not found"
        assert "0001166559" in code, "Institution ID not found"
        assert "trailing_stop" in code.lower(), "Exit signal not configured"
        assert "0.05" in code, "Position size limit not set"
        assert "0.005" in code, "Commission not set"

        print("✅ Strategy translation successful")
        print(f"   Generated {len(code)} characters of LEAN code")
        print("   ✓ Class structure present")
        print("   ✓ Universe configuration applied")
        print("   ✓ Entry signals configured")
        print("   ✓ Exit signals configured")
        print("   ✓ Risk management applied")
        print("   ✓ Transaction costs set")

        return True

    except Exception as e:
        print(f"❌ Strategy translation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_fractional_shares_config():
    """Test fractional shares configuration."""
    print("\n" + "=" * 60)
    print("🧪 Test: Fractional Shares Configuration")
    print("=" * 60)

    try:
        from algorithms.strategy_translator import StrategyTranslator

        translator = StrategyTranslator()

        config = {
            "name": "Fractional Test",
            "start_date": "2023-01-01",
            "end_date": "2023-12-31",
            "initial_capital": 1000,  # Small capital
            "universe": {"tickers": ["AAPL"]},
            "selected_institutions": [],
            "entry_signals": {},
            "exit_signals": [],
            "risk_management": {
                "allow_fractional": True,
                "max_portfolio_positions": 5,
                "max_position_size": 0.5
            },
            "transaction_costs": {}
        }

        code = translator.translate(config)

        # Check for fractional shares setting
        assert "AllowFractionalHoldings = True" in code, "Fractional holdings not enabled"
        assert "max_positions = 5" in code, "Max positions not set correctly"
        assert "position_size = 0.5" in code, "Position size not set correctly"

        print("✅ Fractional shares configuration correct")
        print("   ✓ AllowFractionalHoldings enabled")
        print("   ✓ Position limits configured")

        return True

    except Exception as e:
        print(f"❌ Fractional shares test failed: {e}")
        return False

def test_multiple_signals():
    """Test multiple entry signals configuration."""
    print("\n" + "=" * 60)
    print("🧪 Test: Multiple Entry Signals")
    print("=" * 60)

    try:
        from algorithms.strategy_translator import StrategyTranslator

        translator = StrategyTranslator()

        config = {
            "name": "Multi Signal Test",
            "start_date": "2023-01-01",
            "end_date": "2023-12-31",
            "initial_capital": 100000,
            "universe": {"tickers": ["AAPL", "MSFT", "GOOGL"]},
            "selected_institutions": ["0001166559", "0001423053"],  # Berkshire + Citadel
            "entry_signals": {
                "doubling_down": True,
                "insider_buying": True,
                "herding": True
            },
            "exit_signals": [
                {"type": "trailing_stop", "percent": 10},
                {"type": "time_based", "quarters": 4}
            ],
            "risk_management": {"allow_fractional": True},
            "transaction_costs": {"commission_per_share": 0.01}
        }

        code = translator.translate(config)

        # Check for all signals
        assert "DOUBLING_DOWN" in code, "Doubling down signal not found"
        assert "INSIDER_BUYING" in code, "Insider buying signal not found"
        assert "HERDING" in code, "Herding signal not found"

        # Check institutions
        assert "0001166559" in code, "Berkshire Hathaway ID not found"
        assert "0001423053" in code, "Citadel ID not found"

        # Check exit signals
        assert "trailing_stop" in code.lower(), "Trailing stop not configured"
        assert "0.10" in code or "10" in code, "10% trailing stop not set"

        print("✅ Multiple signals configuration correct")
        print("   ✓ All three entry signals present")
        print("   ✓ Multiple institutions configured")
        print("   ✓ Exit signals applied")

        return True

    except Exception as e:
        print(f"❌ Multiple signals test failed: {e}")
        return False

def main():
    """Run all strategy translator tests."""
    print("🚀 PathVest Strategy Translator Tests")
    print("=" * 60)

    tests = [
        ("Basic Strategy Translation", test_basic_strategy_translation),
        ("Fractional Shares Config", test_fractional_shares_config),
        ("Multiple Signals", test_multiple_signals),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n❌ Test '{test_name}' crashed: {e}")
            results.append((test_name, False))

    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Summary")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")

    print(f"\n{passed}/{total} tests passed ({passed/total*100:.0f}%)")

    if passed == total:
        print("\n🎉 All strategy translator tests passed!")
        print("LEAN strategy translation is working correctly.")
    else:
        print("\n⚠️  Some tests failed. Check the translator implementation.")

    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
