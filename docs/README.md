# PathVest Documentation

Welcome to the PathVest documentation. This folder contains technical documentation for the various features and modules implemented in the PathVest Institutional Equity Backtesting Engine.

---

## Feature Documentation

### Trading & Execution

| Document | Description |
|----------|-------------|
| [Exit Signals](./EXIT_SIGNALS.md) | Stop-loss, take-profit, and trailing stop implementation |
| [Rebalancing Rules](./REBALANCING_RULES.md) | Portfolio rebalancing with multiple frequency modes |

---

## Quick Links

### Exit Signals
- **Purpose:** Risk management through automated exits
- **Types:** Stop-loss (🛑), Take-profit (🎯), Trailing stop (📉)
- **Default Config:** 10% stop-loss, 30% take-profit, 15% trailing stop
- **Test File:** `backend/tests/test_exit_signals.py`

### Rebalancing Rules
- **Purpose:** Maintain target position weights
- **Frequencies:** Never, Weekly, Monthly, Quarterly, Threshold-based
- **Default:** Monthly rebalancing with 5% target weight
- **Test File:** `backend/tests/test_rebalancing.py`

---

## Architecture Overview

```
PathVest
├── Frontend (React/TypeScript)
│   ├── Strategy Wizard (8 steps)
│   ├── Backtest Results Page
│   └── Components (charts, tables, forms)
│
├── Backend (FastAPI/Python)
│   ├── API Endpoints (/api/v1/...)
│   ├── Services
│   │   ├── HistoricalBacktestEngine  ← Exit signals, Rebalancing
│   │   ├── BacktestOrchestrator
│   │   ├── PositionSizer
│   │   └── ExitModules
│   └── Models/Schemas
│
└── Database (PostgreSQL)
    ├── Strategies
    ├── Backtests
    ├── Institutions
    └── Holdings (13F filings)
```

---

## Running Tests

### All Tests
```bash
cd backend
source venv/bin/activate
pytest tests/ -v
```

### Specific Feature Tests
```bash
# Exit Signals
pytest tests/test_exit_signals.py -v

# Rebalancing
pytest tests/test_rebalancing.py -v

# LEAN Integration
pytest lean/tests/ -v
```

---

## Related Guides

| Guide | Location |
|-------|----------|
| Deployment Guide | `DEPLOYMENT_GUIDE.md` (root) |
| User Guide | `USER_GUIDE.md` (root) |
| API Documentation | `http://localhost:8000/api/v1/docs` |

---

## Contributing

When adding new features:

1. Create implementation in appropriate service file
2. Add configuration extraction in orchestrator
3. Update API response schemas if needed
4. Write comprehensive tests
5. Create documentation in this folder
6. Update this README with the new feature

