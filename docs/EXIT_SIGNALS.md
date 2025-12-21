# Exit Signals Implementation

## Overview

PathVest implements three types of exit signals to manage risk and lock in profits during backtesting:

1. **Stop-Loss** - Exit when position drops below a threshold from entry price
2. **Take-Profit** - Exit when position gains exceed a target percentage
3. **Trailing Stop** - Dynamic stop-loss that rises with the stock's peak price

These exit modules are integrated into the `HistoricalBacktestEngine` and are checked daily during backtest execution.

---

## Configuration

### Exit Configuration Object

```python
exit_config = {
    'enable_stop_loss': True,        # Enable/disable stop-loss
    'enable_take_profit': True,      # Enable/disable take-profit
    'enable_trailing_stop': True,    # Enable/disable trailing stop
    'stop_loss_pct': 0.10,           # 10% stop-loss threshold
    'take_profit_pct': 0.30,         # 30% take-profit threshold
    'trailing_stop_pct': 0.15        # 15% trailing stop from peak
}
```

### Default Values

| Parameter | Default | Description |
|-----------|---------|-------------|
| `stop_loss_pct` | 10% | Maximum loss before exit |
| `take_profit_pct` | 30% | Minimum gain to trigger profit-taking |
| `trailing_stop_pct` | 15% | Maximum drawdown from peak price |

---

## Exit Signal Types

### 1. Stop-Loss 🛑

**Purpose:** Limit downside risk by exiting when a position loses too much value.

**Trigger Condition:**
```
return_from_entry <= -stop_loss_pct
```

**Example:**
- Entry price: $100
- Stop-loss: 10%
- Trigger price: $90 or below

**Behavior:**
- Fixed percentage from entry price
- Does not adjust with price movements
- Highest priority among exit signals

### 2. Take-Profit 🎯

**Purpose:** Lock in gains when a position reaches a target profit level.

**Trigger Condition:**
```
return_from_entry >= take_profit_pct
```

**Example:**
- Entry price: $100
- Take-profit: 30%
- Trigger price: $130 or above

**Behavior:**
- Fixed percentage from entry price
- Ensures profits are captured
- Prevents "round-tripping" gains

### 3. Trailing Stop 📉

**Purpose:** Protect profits by setting a dynamic stop that rises with the stock's peak price.

**Trigger Condition:**
```
drawdown_from_peak >= trailing_stop_pct
```

**Example:**
- Entry price: $100
- Peak price reached: $150
- Trailing stop: 15%
- Trigger price: $127.50 (15% below $150)

**Behavior:**
- Tracks the highest price (peak) since entry
- Stop level rises as stock appreciates
- Never falls below entry-based stop-loss
- Balances profit protection with letting winners run

---

## Implementation Details

### Position Details Tracking

Each position tracks:
```python
position_details = {
    'ticker': 'AAPL',
    'entry_date': datetime(2024, 1, 15),
    'entry_price': 150.00,
    'peak_price': 175.00,  # Updated daily
    'shares': 100
}
```

### Check Exit Signals Method

```python
def check_exit_signals(self, date: datetime, current_prices: Dict[str, float]) -> List[Dict]:
    """
    Check all positions for exit signals.
    
    Returns list of exit signals:
    [
        {
            'ticker': 'AAPL',
            'reason': 'Take-profit triggered: +32.5% gain',
            'exit_type': 'take_profit',
            'return_pct': 0.325,
            'confidence': 95.0
        }
    ]
    """
```

### Execute Exit Method

```python
def execute_exit(self, date, ticker, price, reason, exit_type) -> bool:
    """
    Execute an exit trade with:
    - Slippage calculation (0.1%)
    - P&L calculation
    - Trade logging with exit reason
    - Position cleanup
    """
```

---

## Trade Logging

Exit trades are recorded with detailed information:

```python
{
    'date': datetime(2024, 3, 15),
    'ticker': 'AAPL',
    'action': 'SELL',
    'shares': 100,
    'price': 195.00,
    'proceeds': 19480.50,  # After slippage
    'cash_after': 54321.00,
    'exit_reason': 'Take-profit triggered: +30.2% gain',
    'exit_type': 'take_profit',
    'entry_price': 150.00,
    'pnl': 4480.50,
    'return_pct': 0.299
}
```

---

## Priority Order

When multiple exit signals fire simultaneously:

1. **Stop-Loss** (Highest priority - risk protection)
2. **Take-Profit** (Lock in gains)
3. **Trailing Stop** (Protect profits)

Only one exit signal is processed per position per day.

---

## Console Output

During backtest execution, exits are logged with emojis:

```
🎯 EXIT 100 AAPL @ $195.00 | Take-profit triggered: +30.2% gain | P&L: +$4,480.50 (+29.9%)
🛑 EXIT 50 GOOGL @ $135.00 | Stop-loss triggered: -10.5% loss | P&L: -$787.50 (-10.4%)
📉 EXIT 75 MSFT @ $380.00 | Trailing stop: 15.2% from peak $448.00 | P&L: +$2,250.00 (+8.5%)
```

---

## Integration with Strategy Config

Exit rules are extracted from the strategy configuration:

```python
# In backtest_orchestrator.py
exit_rules = strategy_config.get('exit_rules', {})
exit_config = {
    'enable_stop_loss': exit_rules.get('trailing_stop_enabled', True),
    'enable_take_profit': exit_rules.get('take_profit_enabled', True),
    'enable_trailing_stop': exit_rules.get('trailing_stop_enabled', True),
    'stop_loss_pct': exit_rules.get('trailing_stop_pct', 0.10),
    'take_profit_pct': exit_rules.get('take_profit_pct', 0.30),
    'trailing_stop_pct': exit_rules.get('trailing_stop_pct', 0.15)
}
```

---

## Frontend Display

Exit signals are displayed in the UI with:

### Summary Cards
- Total entries, stop-loss exits, take-profit exits, trailing stop exits
- Win rate and total P&L

### Exit Signal Legend
Gradient badges for each exit type:
- 📈 Entry (Blue)
- 🛑 Stop Loss (Red)
- 🎯 Take Profit (Green)
- 📉 Trailing Stop (Amber)

### Trade Table Enhancements
- Left border color indicates exit type
- Color-coded return percentages with arrows
- Styled chips for exit reasons

---

## Results Schema

Exit statistics are included in backtest results:

```python
{
    'trades': [
        {
            'ticker': 'AAPL',
            'action': 'SELL',
            'exit_reason': 'Take-profit triggered: +30.2% gain',
            'exit_type': 'take_profit',
            'pnl': 4480.50,
            'return_pct': 0.299,
            'holding_period_days': 45
        }
    ],
    'summary': {
        'total_trades': 15,
        'win_rate': 0.65,
        'max_drawdown': -0.12
    }
}
```

---

## Testing

Tests are located in `backend/tests/test_exit_signals.py` and cover:

1. Configuration initialization
2. Stop-loss trigger conditions
3. Take-profit trigger conditions
4. Trailing stop with peak tracking
5. Priority ordering
6. Trade execution and logging
7. Edge cases (zero prices, no positions)

Run tests:
```bash
cd backend
source venv/bin/activate
pytest tests/test_exit_signals.py -v
```

---

## Best Practices

1. **Conservative Stop-Losses**: Start with 10-15% for volatile stocks
2. **Generous Take-Profits**: 30-50% allows for trend following
3. **Balanced Trailing Stops**: 15% balances protection with upside
4. **Disable for Testing**: Set all to `False` to test pure signal performance
5. **Quarterly Review**: Adjust thresholds based on market volatility

---

## Related Files

| File | Purpose |
|------|---------|
| `backend/app/services/historical_backtest_engine.py` | Core implementation |
| `backend/app/services/backtest_orchestrator.py` | Config extraction |
| `backend/app/api/v1/endpoints/backtest.py` | API response formatting |
| `frontend/src/pages/BacktestResultsPage.tsx` | UI display |
| `frontend/src/components/strategy/steps/Step5_ExitRules.tsx` | User configuration |

