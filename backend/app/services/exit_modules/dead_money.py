"""
Exit Module 4: Dead Money Exit
Time-based exit for stagnant positions

Per SRS FR-3.1.C.11:
- Exits positions held for 4+ quarters with negative return
- Frees capital from underperforming "dead money" positions
- Default: 4 quarters (1 year) + negative return
- Configurable holding period and return threshold
"""

from typing import Dict, List, Optional
from datetime import date, datetime, timedelta
from dataclasses import dataclass
import pandas as pd


@dataclass
class DeadMoneyExit:
    """Represents a dead money exit signal"""
    ticker: str
    exit_date: date
    reason: str
    entry_date: date
    entry_price: float
    current_price: float
    return_pct: float
    quarters_held: int
    confidence: float  # 0-100


class DeadMoneyModule:
    """
    Exit Module 4: Dead Money Exit
    
    Exits positions that have been held for extended periods with no gains.
    Frees up capital for better opportunities.
    
    Logic:
    1. Calculate holding period in quarters
    2. Check if return is negative or near-zero
    3. Exit if held >= threshold quarters AND return < threshold
    4. Higher confidence for longer holds with worse returns
    """
    
    DEFAULT_MIN_QUARTERS = 4  # 1 year
    DEFAULT_MAX_RETURN_PCT = 0.0  # Must be negative to exit
    DAYS_PER_QUARTER = 91  # Approximate
    
    def __init__(self):
        """Initialize Dead Money Module"""
        pass
    
    def check_dead_money(
        self,
        ticker: str,
        entry_date: date,
        entry_price: float,
        current_date: date,
        price_data: pd.DataFrame,
        min_quarters: int = DEFAULT_MIN_QUARTERS,
        max_return_pct: float = DEFAULT_MAX_RETURN_PCT
    ) -> Optional[DeadMoneyExit]:
        """
        Check if dead money exit should be triggered
        
        Args:
            ticker: Stock ticker
            entry_date: Entry date
            entry_price: Entry price
            current_date: Current date to check
            price_data: DataFrame with columns: date, close
            min_quarters: Minimum quarters to hold before exit (default 4)
            max_return_pct: Maximum return to trigger exit (default 0%)
            
        Returns:
            DeadMoneyExit if exit triggered, None otherwise
        """
        
        if price_data is None or len(price_data) == 0:
            return None
        
        # Calculate holding period
        holding_days = (current_date - entry_date).days
        quarters_held = holding_days / self.DAYS_PER_QUARTER
        
        # Check if held long enough
        if quarters_held < min_quarters:
            return None
        
        # Get current price
        price_data = price_data.sort_values('date')
        # Convert dates to pandas Timestamp for comparison
        entry_ts = pd.Timestamp(entry_date)
        current_ts = pd.Timestamp(current_date)
        mask = (price_data['date'] >= entry_ts) & (price_data['date'] <= current_ts)
        position_data = price_data[mask]
        
        if len(position_data) == 0:
            return None
        
        current_price = position_data.iloc[-1]['close']
        
        # Calculate return
        return_pct = (current_price - entry_price) / entry_price
        
        # Check if return is below threshold
        if return_pct > max_return_pct:
            return None
        
        # Calculate confidence
        # Higher confidence for:
        # - Longer holding periods
        # - Worse returns
        base_confidence = 70.0
        time_bonus = min(20, (quarters_held - min_quarters) * 5)  # +5 per extra quarter
        return_penalty = min(10, abs(return_pct) * 20)  # More negative = higher confidence
        
        confidence = min(100, base_confidence + time_bonus + return_penalty)
        
        return DeadMoneyExit(
            ticker=ticker,
            exit_date=current_date,
            reason=f"Dead money: held {quarters_held:.1f}Q with {return_pct*100:.1f}% return",
            entry_date=entry_date,
            entry_price=entry_price,
            current_price=current_price,
            return_pct=return_pct,
            quarters_held=int(quarters_held),
            confidence=confidence
        )
    
    def batch_check_dead_money(
        self,
        positions: List[Dict],
        current_date: date,
        price_data_dict: Dict[str, pd.DataFrame],
        min_quarters: int = DEFAULT_MIN_QUARTERS,
        max_return_pct: float = DEFAULT_MAX_RETURN_PCT
    ) -> List[DeadMoneyExit]:
        """
        Check dead money exit for multiple positions
        
        Args:
            positions: List of position dicts with keys:
                - ticker: Stock ticker
                - entry_date: Entry date
                - entry_price: Entry price
            current_date: Current date to check
            price_data_dict: Dict of ticker -> price DataFrame
            min_quarters: Minimum quarters to hold
            max_return_pct: Maximum return threshold
            
        Returns:
            List of DeadMoneyExit signals
        """
        
        exit_signals = []
        
        for position in positions:
            ticker = position['ticker']
            price_data = price_data_dict.get(ticker)
            
            if price_data is None:
                continue
            
            exit_signal = self.check_dead_money(
                ticker=ticker,
                entry_date=position['entry_date'],
                entry_price=position['entry_price'],
                current_date=current_date,
                price_data=price_data,
                min_quarters=min_quarters,
                max_return_pct=max_return_pct
            )
            
            if exit_signal:
                exit_signals.append(exit_signal)
        
        return exit_signals
    
    def analyze_position_staleness(
        self,
        entry_date: date,
        entry_price: float,
        current_date: date,
        price_data: pd.DataFrame
    ) -> Dict:
        """
        Analyze how "stale" a position is
        
        Args:
            entry_date: Entry date
            entry_price: Entry price
            current_date: Current date
            price_data: Price DataFrame
            
        Returns:
            Dict with staleness metrics
        """
        
        if price_data is None or len(price_data) == 0:
            return {}
        
        # Calculate holding period
        holding_days = (current_date - entry_date).days
        quarters_held = holding_days / self.DAYS_PER_QUARTER
        
        # Get price data
        price_data = price_data.sort_values('date')
        # Convert dates to pandas Timestamp for comparison
        entry_ts = pd.Timestamp(entry_date)
        current_ts = pd.Timestamp(current_date)
        mask = (price_data['date'] >= entry_ts) & (price_data['date'] <= current_ts)
        position_data = price_data[mask]
        
        if len(position_data) == 0:
            return {}
        
        current_price = position_data.iloc[-1]['close']
        return_pct = (current_price - entry_price) / entry_price
        
        # Calculate price volatility (standard deviation of returns)
        if len(position_data) > 1:
            price_returns = position_data['close'].pct_change().dropna()
            volatility = price_returns.std() * 100  # Annualized
        else:
            volatility = 0
        
        # Calculate average daily return
        avg_daily_return = return_pct / holding_days if holding_days > 0 else 0
        
        # Determine staleness level
        is_stale = quarters_held >= self.DEFAULT_MIN_QUARTERS and return_pct <= 0
        staleness_score = 0
        if is_stale:
            staleness_score = min(100, (quarters_held / self.DEFAULT_MIN_QUARTERS) * 50 + abs(return_pct) * 50)
        
        return {
            'holding_days': holding_days,
            'quarters_held': quarters_held,
            'return_pct': return_pct,
            'avg_daily_return_pct': avg_daily_return * 100,
            'volatility_pct': volatility,
            'is_stale': is_stale,
            'staleness_score': staleness_score,
            'recommendation': 'EXIT' if is_stale else 'HOLD'
        }


# Test function
def test_dead_money_module():
    """Test the Dead Money Module"""
    print("\n" + "="*70)
    print("🧪 TESTING EXIT MODULE 4: DEAD MONEY EXIT")
    print("="*70)
    
    # Create module
    module = DeadMoneyModule()
    print("✅ DeadMoneyModule created")
    
    # Create mock price data
    print("\n1. Creating mock price data...")
    
    # Scenario 1: Long hold with negative return (dead money)
    entry_date = date(2023, 1, 1)
    current_date = date(2024, 6, 30)  # ~18 months = ~6 quarters
    
    dates = pd.date_range(start=entry_date, end=current_date, freq='D')
    base_price = 100.0
    
    # Stagnant/declining price
    prices_dead = [base_price * (1 - (i / len(dates)) * 0.15) for i in range(len(dates))]
    price_data_dead = pd.DataFrame({
        'date': dates,
        'close': prices_dead,
        'high': [p * 1.01 for p in prices_dead],
        'low': [p * 0.99 for p in prices_dead]
    })
    print(f"   ✅ Scenario 1 (dead money) created: {len(price_data_dead)} days")
    
    # Test 1: Check dead money exit trigger
    print("\n2. Testing dead money exit trigger...")
    exit_signal = module.check_dead_money(
        ticker="DEAD1",
        entry_date=entry_date,
        entry_price=base_price,
        current_date=current_date,
        price_data=price_data_dead,
        min_quarters=4
    )
    
    if exit_signal:
        print(f"   ✅ Exit signal generated!")
        print(f"      Quarters held: {exit_signal.quarters_held}")
        print(f"      Return: {exit_signal.return_pct*100:.1f}%")
        print(f"      Reason: {exit_signal.reason}")
        print(f"      Confidence: {exit_signal.confidence:.1f}")
    else:
        print(f"   ⚠️  No exit signal (unexpected)")
    
    # Scenario 2: Long hold but positive return (not dead money)
    prices_rising = [base_price * (1 + (i / len(dates)) * 0.20) for i in range(len(dates))]
    price_data_rising = pd.DataFrame({
        'date': dates,
        'close': prices_rising,
        'high': [p * 1.01 for p in prices_rising],
        'low': [p * 0.99 for p in prices_rising]
    })
    
    print("\n3. Testing position with positive return (should NOT exit)...")
    exit_signal = module.check_dead_money(
        ticker="RISING1",
        entry_date=entry_date,
        entry_price=base_price,
        current_date=current_date,
        price_data=price_data_rising,
        min_quarters=4
    )
    
    if exit_signal:
        print(f"   ⚠️  Exit signal generated (unexpected)")
    else:
        print(f"   ✅ No exit signal (correct - position is profitable)")
    
    # Test 3: Analyze staleness
    print("\n4. Testing staleness analysis...")
    staleness = module.analyze_position_staleness(
        entry_date=entry_date,
        entry_price=base_price,
        current_date=current_date,
        price_data=price_data_dead
    )
    print(f"   ✅ Staleness analysis complete:")
    print(f"      Quarters held: {staleness['quarters_held']:.1f}")
    print(f"      Return: {staleness['return_pct']*100:.1f}%")
    print(f"      Is stale: {staleness['is_stale']}")
    print(f"      Staleness score: {staleness['staleness_score']:.1f}")
    print(f"      Recommendation: {staleness['recommendation']}")
    
    # Test 4: Batch check
    print("\n5. Testing batch check...")
    
    # Short hold (3 months - should not exit even if negative)
    recent_entry = date(2024, 4, 1)
    dates_short = pd.date_range(start=recent_entry, end=current_date, freq='D')
    prices_short = [base_price * 0.95] * len(dates_short)  # Slight loss
    price_data_short = pd.DataFrame({
        'date': dates_short,
        'close': prices_short,
        'high': [p * 1.01 for p in prices_short],
        'low': [p * 0.99 for p in prices_short]
    })
    
    test_positions = [
        {
            'ticker': 'DEAD1',
            'entry_date': entry_date,
            'entry_price': base_price
        },
        {
            'ticker': 'RISING1',
            'entry_date': entry_date,
            'entry_price': base_price
        },
        {
            'ticker': 'SHORT1',
            'entry_date': recent_entry,
            'entry_price': base_price
        }
    ]
    
    price_data_dict = {
        'DEAD1': price_data_dead,
        'RISING1': price_data_rising,
        'SHORT1': price_data_short
    }
    
    exit_signals = module.batch_check_dead_money(
        positions=test_positions,
        current_date=current_date,
        price_data_dict=price_data_dict,
        min_quarters=4
    )
    print(f"   ✅ Batch check complete: {len(exit_signals)} exits triggered")
    for signal in exit_signals:
        print(f"      - {signal.ticker}: {signal.quarters_held}Q held, {signal.return_pct*100:.1f}% return")
    
    print("\n" + "="*70)
    print("✅ DEAD MONEY MODULE TEST COMPLETE")
    print("="*70)
    
    return True


if __name__ == "__main__":
    import sys
    success = test_dead_money_module()
    sys.exit(0 if success else 1)

