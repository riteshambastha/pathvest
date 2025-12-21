# Rebalancing Rules Implementation

## Overview

PathVest implements portfolio rebalancing to maintain target position weights and prevent position drift. The rebalancing module supports multiple frequency modes and is integrated into the `HistoricalBacktestEngine`.

**Per SRS Specification FR-3.1.C:**
- Static 5% position size per stock
- Portfolio constraint: 5-20 stocks
- Rebalancing restores equal-weight allocation
- Rank buffer prevents excessive turnover

---

## Rebalancing Frequencies

| Frequency | Trigger | Use Case |
|-----------|---------|----------|
| `never` | Never rebalances | Buy and hold strategies |
| `weekly` | Every Monday | Active trading strategies |
| `monthly` | First trading day of month | **Default - Recommended** |
| `quarterly` | First trading day of quarter | Aligned with 13F filings |
| `threshold` | When drift exceeds 5% | Dynamic rebalancing |

---

## Configuration

### Rebalance Configuration Object

```python
rebalance_config = {
    'frequency': 'monthly',       # never, weekly, monthly, quarterly, threshold
    'drift_threshold': 0.05,      # 5% drift triggers threshold-based rebalancing
    'target_weight': 0.05,        # 5% per position (SRS requirement)
    'min_positions': 5,           # Minimum positions before 100% cash
    'max_positions': 20           # Maximum positions allowed
}
```

### Default Values

| Parameter | Default | Description |
|-----------|---------|-------------|
| `frequency` | `monthly` | Rebalancing schedule |
| `drift_threshold` | 5% | Threshold for drift-based rebalancing |
| `target_weight` | 5% | Target weight per position |
| `min_positions` | 5 | Minimum required positions |
| `max_positions` | 20 | Maximum allowed positions |

---

## How Rebalancing Works

### 1. Trigger Detection

On each trading day, the engine checks if rebalancing should occur:

```python
if self.positions and self.should_rebalance(date, current_prices):
    self.execute_rebalancing(date, current_prices)
```

### 2. Frequency-Specific Logic

#### Never (Buy and Hold)
```python
if frequency == 'never':
    return False  # Never rebalance
```

#### Weekly
```python
if frequency == 'weekly':
    # Rebalance every Monday (weekday 0)
    return current_date.weekday() == 0 and days_since_last >= 5
```

#### Monthly
```python
if frequency == 'monthly':
    # Rebalance on first trading day of new month
    return current_month != last_rebalance_month
```

#### Quarterly
```python
if frequency == 'quarterly':
    current_quarter = (current_date.month - 1) // 3
    last_quarter = (last_rebalance_date.month - 1) // 3
    return current_quarter != last_quarter
```

#### Threshold-Based
```python
if frequency == 'threshold':
    # Check if any position drifted beyond threshold
    return self.check_drift_threshold(current_prices)
```

### 3. Drift Detection

For threshold-based rebalancing:

```python
def check_drift_threshold(self, current_prices):
    for ticker, shares in self.positions.items():
        position_value = shares * current_prices[ticker]
        current_weight = position_value / portfolio_value
        drift = abs(current_weight - target_weight)
        
        if drift > self.drift_threshold:
            return True  # Trigger rebalancing
    
    return False
```

### 4. Target Allocation Calculation

```python
def calculate_target_allocation(self, current_prices):
    """
    Calculate equal-weight allocation for all positions.
    Each position gets 5% (or 1/N if fewer than 20 positions).
    """
    target_weight = min(0.05, 1.0 / len(positions))
    target_value = portfolio_value * target_weight
    
    for ticker in positions:
        target_shares[ticker] = target_value / current_prices[ticker]
    
    return target_shares
```

### 5. Trade Execution

```python
def execute_rebalancing(self, date, current_prices):
    target_allocation = self.calculate_target_allocation(current_prices)
    
    for ticker, target_shares in target_allocation.items():
        current_shares = self.positions[ticker]
        share_diff = target_shares - current_shares
        
        # Minimum trade threshold: $100
        if abs(share_diff * price) < 100:
            continue
        
        if share_diff > 0:
            # Buy more shares
            self.execute_trade(date, ticker, share_diff, price, 'BUY')
        elif share_diff < 0:
            # Sell excess shares
            self.execute_trade(date, ticker, abs(share_diff), price, 'SELL')
```

---

## Console Output

During backtest execution:

```
⚖️ Rebalancing: MONTHLY | Target Weight: 5% | Drift Threshold: 5%

⚖️ REBALANCING on 2024-02-01
   Portfolio positions: 3
  📉 SELL 101 AAPL @ $165.33 = $16,698.78
  📉 SELL 150 GOOGL @ $106.09 = $15,914.07
  📉 SELL 48 MSFT @ $290.41 = $13,939.65
   Executed 3 rebalancing trades

⚖️ REBALANCING on 2024-03-01
   Portfolio positions: 3
  📉 SELL 2 AAPL @ $179.82 = $359.64
  📉 SELL 2 GOOGL @ $111.89 = $223.78
   Executed 2 rebalancing trades

📊 Backtest Results:
   Rebalances: 2 (monthly)
```

---

## Integration with Strategy Config

Rebalancing config is extracted from multiple sources:

```python
# In backtest_orchestrator.py
risk_management = strategy_config.get('risk_management', {})
heartbeat = strategy_config.get('heartbeat', {})

# Priority: heartbeat > risk_management > default
rebalance_frequency = (
    heartbeat.get('rebalance_frequency') or 
    risk_management.get('rebalancing_frequency', 'monthly')
)

rebalance_config = {
    'frequency': rebalance_frequency,
    'drift_threshold': risk_management.get('drift_threshold', 0.05),
    'target_weight': 0.05,  # Fixed per SRS
    'min_positions': strategy_config.get('min_positions', 5),
    'max_positions': strategy_config.get('max_positions', 20)
}
```

---

## Results Schema

Rebalancing statistics are included in backtest results:

```python
{
    'rebalance_count': 2,
    'rebalance_frequency': 'monthly',
    'rebalance_config': {
        'frequency': 'monthly',
        'drift_threshold': 0.05,
        'target_weight': 0.05,
        'min_positions': 5,
        'max_positions': 20
    },
    'summary': {
        'total_trades': 15,
        'total_return': 0.125
    }
}
```

---

## Testing

### Test File Location
`backend/tests/test_rebalancing.py`

### Test Categories

1. **TestRebalancingConfiguration** (2 tests)
   - Default configuration values
   - Custom configuration values

2. **TestShouldRebalance** (6 tests)
   - Never frequency
   - Weekly frequency (Monday trigger)
   - Monthly frequency (new month)
   - Quarterly frequency (new quarter)
   - Threshold-based (drift detection)
   - First day initialization

3. **TestCheckDriftThreshold** (3 tests)
   - Empty positions
   - Positions within threshold
   - Positions exceeding threshold

4. **TestCalculateTargetAllocation** (3 tests)
   - Empty positions
   - Single position allocation
   - Multiple positions equal weight

5. **TestExecuteRebalancing** (3 tests)
   - Empty positions no trades
   - Last date update
   - Counter increment

6. **TestRebalancingIntegration** (2 tests)
   - Monthly rebalancing execution
   - Never rebalancing zero count

7. **TestRebalancingEdgeCases** (3 tests)
   - Zero price handling
   - Year boundary for quarterly
   - Minimum trade threshold

### Running Tests

```bash
cd backend
source venv/bin/activate
pytest tests/test_rebalancing.py -v

# Expected output:
# 22 passed
```

---

## Frontend Configuration

Users configure rebalancing in **Step 6: Risk Management**:

```tsx
// Step6_RiskManagement.tsx
<select
  value={riskManagement.rebalancing_frequency}
  onChange={(e) => updateRiskManagement({ rebalancing_frequency: e.target.value })}
>
  <option value="never">Never (Buy and Hold)</option>
  <option value="weekly">Weekly</option>
  <option value="monthly">Monthly (Recommended)</option>
  <option value="quarterly">Quarterly</option>
  <option value="threshold">Threshold-Based (when drift > 5%)</option>
</select>
```

---

## Best Practices

### Frequency Selection

| Strategy Type | Recommended Frequency |
|--------------|----------------------|
| Long-term investing | `quarterly` or `never` |
| Momentum following | `never` (let winners run) |
| Mean reversion | `monthly` or `weekly` |
| Balanced growth | `monthly` (default) |

### Transaction Cost Considerations

- More frequent rebalancing = higher transaction costs
- Monthly balances between drift correction and cost efficiency
- Threshold-based avoids unnecessary trades in stable markets

### Minimum Trade Threshold

- Default: $100 minimum trade value
- Prevents tiny trades that incur fixed costs
- Adjustable based on commission structure

---

## Comparison with LEAN Engine

| Feature | Custom Engine | LEAN Engine |
|---------|--------------|-------------|
| Monthly Rebalancing | ✅ `should_rebalance()` | ✅ `Schedule.On(DateRules.MonthStart())` |
| Quarterly Rebalancing | ✅ Quarter detection | ✅ `DateRules.Every(DayOfWeek.Monday)` |
| Threshold-Based | ✅ `check_drift_threshold()` | ⚠️ Requires custom implementation |
| Rank Buffer | ⚠️ Planned | ✅ Built-in with `position_sizer` |

---

## Related Files

| File | Purpose |
|------|---------|
| `backend/app/services/historical_backtest_engine.py` | Core rebalancing implementation |
| `backend/app/services/backtest_orchestrator.py` | Config extraction and engine initialization |
| `backend/app/services/position_sizing/static_sizer.py` | Position sizing with rebalance support |
| `backend/tests/test_rebalancing.py` | Comprehensive test suite |
| `frontend/src/components/strategy/steps/Step6_RiskManagement.tsx` | UI configuration |

---

## Future Enhancements

1. **Rank Buffer Integration**
   - Prevent selling positions within B=5 rank buffer
   - Reduce portfolio turnover

2. **Tax-Loss Harvesting**
   - Sell losing positions before year-end
   - Replace with similar securities

3. **Sector Rebalancing**
   - Maintain sector weight limits
   - Prevent concentration risk

4. **Dynamic Thresholds**
   - Adjust drift threshold based on volatility
   - Wider thresholds in volatile markets

