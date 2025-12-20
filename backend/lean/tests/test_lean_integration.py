#!/usr/bin/env python3
"""
LEAN Integration Tests - Components Available in Current Setup

This script tests the LEAN integration components that are available
without requiring actual LEAN CLI installation.
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

def test_lean_engine_import():
    """Test 1: LEAN Engine can be imported."""
    print("=" * 60)
    print("🧪 Test 1: LEAN Engine Import")
    print("=" * 60)

    try:
        from app.services.lean_engine import LEANBacktestEngine
        print("✅ LEANBacktestEngine imported successfully")

        # Test initialization
        engine = LEANBacktestEngine(
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 12, 31),
            initial_cash=100000
        )
        print("✅ LEANBacktestEngine initialized successfully")

        # Check directories exist
        assert engine.algorithms_dir.exists(), "Algorithms directory not created"
        assert engine.data_dir.exists(), "Data directory not created"
        assert engine.results_dir.exists(), "Results directory not created"
        print("✅ All required directories created")

        return True

    except Exception as e:
        print(f"❌ LEAN Engine test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_strategy_translator_import():
    """Test 2: Strategy Translator can be imported."""
    print("\n" + "=" * 60)
    print("🧪 Test 2: Strategy Translator Import")
    print("=" * 60)

    try:
        # Test import from lean directory
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from algorithms.strategy_translator import StrategyTranslator
        print("✅ StrategyTranslator imported successfully")

        # Test initialization
        translator = StrategyTranslator()
        print("✅ StrategyTranslator initialized successfully")

        # Test basic functionality
        config = {
            "name": "Test Strategy",
            "start_date": "2023-01-01",
            "end_date": "2023-12-31",
            "initial_capital": 100000,
            "universe": {"tickers": ["AAPL"]},
            "selected_institutions": [],
            "entry_signals": {},
            "exit_signals": [],
            "risk_management": {"allow_fractional": True},
            "transaction_costs": {"commission_per_share": 0.005}
        }

        code = translator.translate(config)
        assert len(code) > 0, "No code generated"
        assert "class Test" in code, "Class not found in generated code"
        print("✅ Strategy translation works")
        print(f"   Generated {len(code)} characters of code")

        return True

    except ImportError:
        print("⚠️  StrategyTranslator not available (import failed)")
        return False
    except Exception as e:
        print(f"❌ Strategy Translator test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_lean_config():
    """Test 3: LEAN Configuration setup."""
    print("\n" + "=" * 60)
    print("🧪 Test 3: LEAN Configuration")
    print("=" * 60)

    try:
        # Check if config files exist in the correct location
        config_dir = Path(__file__).parent.parent / "config"
        lean_config = config_dir / "lean-config.json"

        if lean_config.exists():
            print("✅ LEAN config file exists")

            # Try to load config
            import json
            with open(lean_config, 'r') as f:
                config = json.load(f)

            print("✅ LEAN config is valid JSON")
            print(f"   Config keys: {list(config.keys())}")

            # Check required keys
            required_keys = ["environments", "data-folder"]
            for key in required_keys:
                assert key in config, f"Required key '{key}' not found"
            print("✅ Required configuration keys present")

        else:
            print("⚠️  LEAN config file not found")
            return False

        return True

    except Exception as e:
        print(f"❌ LEAN Configuration test failed: {e}")
        return False

def test_algorithm_templates():
    """Test 4: Algorithm templates exist."""
    print("\n" + "=" * 60)
    print("🧪 Test 4: Algorithm Templates")
    print("=" * 60)

    try:
        # Check in the correct location
        algorithms_dir = Path(__file__).parent.parent / "algorithms"

        # Check for key algorithm files
        required_files = [
            "pathvest_base_strategy.py",
            "strategy_translator.py",
            "test_algorithm.py"
        ]

        found_files = []
        for filename in required_files:
            filepath = algorithms_dir / filename
            if filepath.exists():
                found_files.append(filename)
                print(f"✅ {filename} exists")
            else:
                print(f"❌ {filename} missing")

        if len(found_files) == len(required_files):
            print("✅ All required algorithm files present")
            return True
        else:
            print(f"⚠️  {len(required_files) - len(found_files)} files missing")
            return False

    except Exception as e:
        print(f"❌ Algorithm templates test failed: {e}")
        return False

def test_custom_data_classes():
    """Test 5: Custom data classes for SEC integration."""
    print("\n" + "=" * 60)
    print("🧪 Test 5: Custom Data Classes")
    print("=" * 60)

    try:
        # Check if custom data directory exists in lean_engine
        custom_data_dir = Path(__file__).parent.parent.parent / "lean_engine" / "custom_data"

        if custom_data_dir.exists():
            print("✅ Custom data directory exists")

            # Check for key files
            required_files = [
                "sec_filing_13f.py",
                "insider_transaction_form4.py"
            ]

            found_files = []
            for filename in required_files:
                filepath = custom_data_dir / filename
                if filepath.exists():
                    found_files.append(filename)
                    print(f"✅ {filename} exists")
                else:
                    print(f"❌ {filename} missing")

            if len(found_files) == len(required_files):
                print("✅ All custom data classes present")
                return True
            else:
                print(f"⚠️  {len(required_files) - len(found_files)} files missing")
                return False
        else:
            print("⚠️  Custom data directory not found")
            return False

    except Exception as e:
        print(f"❌ Custom data classes test failed: {e}")
        return False

def main():
    """Run all LEAN integration tests."""
    print("🚀 PathVest LEAN Integration Component Tests")
    print("=" * 60)

    tests = [
        ("LEAN Engine Import", test_lean_engine_import),
        ("Strategy Translator Import", test_strategy_translator_import),
        ("LEAN Configuration", test_lean_config),
        ("Algorithm Templates", test_algorithm_templates),
        ("Custom Data Classes", test_custom_data_classes),
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
        print("\n🎉 All LEAN integration components are working!")
        print("Note: Actual LEAN CLI execution requires Docker and LEAN installation.")
    else:
        print("\n⚠️  Some components are missing or not working.")

    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
