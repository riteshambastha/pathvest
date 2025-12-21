"""
Pytest configuration and fixtures for PathVest test suite.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.base import Base
from app.core.config import settings


# Test database URL (in-memory SQLite)
TEST_DATABASE_URL = "sqlite:///:memory:"

# Create test engine
engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db():
    """Create a fresh database for each test."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="module")
def client():
    """FastAPI test client."""
    with TestClient(app) as c:
        yield c


@pytest.fixture
def mock_sec_data():
    """Mock SEC 13F filing data."""
    return {
        "filing_date": "2023-01-15",
        "filing_manager": "Berkshire Hathaway",
        "cik": "0001067983",
        "report_period_end": "2022-12-31",
        "holdings": [
            {
                "ticker": "AAPL",
                "cusip": "037833100",
                "shares": 915560000,
                "value": 115000000000,
                "investment_discretion": "SOLE"
            },
            {
                "ticker": "BAC",
                "cusip": "060505104",
                "shares": 1032852006,
                "value": 33500000000,
                "investment_discretion": "SOLE"
            }
        ]
    }


@pytest.fixture
def mock_market_data():
    """Mock market data (OHLCV)."""
    return {
        "ticker": "AAPL",
        "date": "2023-01-15",
        "open": 150.00,
        "high": 152.50,
        "low": 149.00,
        "close": 151.75,
        "volume": 75000000,
        "adjusted_close": 151.75
    }


@pytest.fixture
def sample_strategy_config():
    """Sample strategy configuration for testing."""
    return {
        "name": "Test Strategy",
        "backtest_period": {
            "start_date": "2020-01-01",
            "end_date": "2023-12-31"
        },
        "initial_capital": 1000000,
        "universe_filters": {
            "market_cap_min": 3000000000,
            "index_membership": "ALL",
            "lookback_quarters": 9
        },
        "sub_universe_filters": {
            "investor": {
                "aum_min": 1000000000,
                "track_record_quarters": 8,
                "concentration_max": 0.35,
                "turnover_max": 0.40
            },
            "transaction": {
                "min_buy_value": 10000000,
                "share_increase_min": 0.05
            },
            "insider": {
                "roles": ["CEO", "CFO"],
                "value_min": 100000
            }
        },
        "entry_signals": {
            "enable_doubling_down": True,
            "enable_insider_buying": True,
            "enable_herding": True,
            "technical_confirmation": {
                "price_breakout_days": 10,
                "sma_period": 50,
                "rsi_period": 14,
                "rsi_threshold": 45
            }
        },
        "position_sizing": {
            "method": "static",
            "percent_per_position": 0.05,
            "min_positions": 5,
            "max_positions": 20,
            "rank_buffer": 5
        },
        "exit_rules": {
            "enable_thesis_drift": True,
            "enable_insider_reversal": False,
            "enable_trailing_stop": True,
            "trailing_stop_percent": 0.15,
            "enable_dead_money": True,
            "dead_money_quarters": 4
        },
        "transaction_costs": {
            "commission_per_share": 0.005,
            "slippage_bps": 25
        },
        "heartbeat": {
            "rebalance_frequency": "monthly"
        },
        "enable_validation": False
    }


@pytest.fixture
def sample_backtest_response():
    """Sample backtest response for testing."""
    return {
        "backtest_id": "test_backtest_001",
        "status": "completed",
        "execution_time_seconds": 45.2,
        "summary": {
            "total_return": 0.35,
            "cagr": 0.12,
            "volatility": 0.18,
            "sharpe_ratio": 1.25,
            "sortino_ratio": 1.45,
            "max_drawdown": -0.15,
            "romad": 0.80,
            "alpha": 0.05,
            "beta": 0.85,
            "information_ratio": 0.45,
            "var_95": -0.025,
            "cvar_95": -0.035,
            "win_rate_daily": 0.52,
            "win_rate_monthly": 0.65,
            "win_rate_yearly": 0.75,
            "best_day": 0.08,
            "worst_day": -0.06,
            "benchmark_total_return": 0.25,
            "benchmark_cagr": 0.09
        },
        "trades": [
            {
                "entry_date": "2020-02-15",
                "exit_date": "2020-08-20",
                "ticker": "AAPL",
                "entry_price": 150.00,
                "exit_price": 165.00,
                "shares": 333.33,
                "pnl": 5000.00,
                "return_pct": 0.10,
                "holding_period_days": 187,
                "exit_reason": "trailing_stop",
                "signal_type": "doubling_down"
            }
        ]
    }


@pytest.fixture(autouse=True)
def reset_environment(monkeypatch):
    """Reset environment variables for each test."""
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("ENABLE_MOCK_DATA", "True")

