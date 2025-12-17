"""
Exit Module 3: Trailing Stop/Take-Profit
Price-based exit triggers

Per SRS FR-3.1.C.11:
- Trailing stop: Exits if price drops X% from peak
- Take profit: Exits if price rises Y% from entry
- Default trailing stop: 15%
- Default take profit: 50%
- Configurable thresholds
"""

from typing import Dict, List, Optional, Tuple
from datetime import date, datetime
from dataclasses import dataclass
import pandas as pd


@dataclass
class TrailingStopExit:
    """Represents a trailing stop/take-profit exit signal"""
    ticker: str
    exit_date: date
    exit_price: float
    reason: str
    entry_price: float
    peak_price: float
    return_pct: float
    trigger_type: str  # 'trailing_stop' or 'take_profit'
    confidence: float  # 0-100


class TrailingStopModule:
    """
    Exit Module 3: Trailing Stop and Take-Profit
    
    Price-based exit logic:
    1. Trailing Stop: Exit if current price < peak price * (1 - threshold)
    2. Take Profit: Exit if current price > entry price * (1 + target)
    
    Logic:
    - Track peak price since entry
    - Calculate trailing stop level dynamically
    - Exit when price breaks stop or hits target
    - Higher confidence for clean breakdowns
    """
    
    DEFAULT_TRAILING_STOP_PCT = 0.15  # 15%
    DEFAULT_TAKE_PROFIT_PCT = 0.50    # 50%
    
    def __init__(self):
        """Initialize Trailing Stop Module"""
        pass
    
    def check_trailing_stop(
        self,
        ticker: str,
        entry_date: date,
        entry_price: float,
        current_date: date,
        price_data: pd.DataFrame,
        trailing_stop_pct: float = DEFAULT_TRAILING_STOP_PCT,
        take_profit_pct: float = DEFAULT_TAKE_PROFIT_PCT
    ) -> Optional[TrailingStopExit]:
        """
        Check if trailing stop or take profit exit should be triggered
        
        Args:
            ticker: Stock ticker
            entry_date: Entry date
            entry_price: Entry price
            current_date: Current date to check
            price_data: DataFrame with columns: date, close, high, low
            trailing_stop_pct: Trailing stop percentage (default 15%)
            take_profit_pct: Take profit percentage (default 50%)
            
        Returns:
            TrailingStopExit if exit triggered, None otherwise
        """
        
        if price_data is None or len(price_data) == 0:
            return None
        
        # Filter price data from entry to current date
        price_data = price_data.sort_values('date')
        # Convert dates to pandas Timestamp for comparison
        entry_ts = pd.Timestamp(entry_date)
        current_ts = pd.Timestamp(current_date)
        mask = (price_data['date'] >= entry_ts) & (price_data['date'] <= current_ts)
        position_data = price_data[mask].copy()
        
        if len(position_data) == 0:
            return None
        
        # Get current price
        current_price = position_data.iloc[-1]['close']
        
        # Calculate peak price since entry
        peak_price = position_data['close'].max()
        
        # Calculate return from entry
        return_pct = (current_price - entry_price) / entry_price
        
        # Check take profit first (exit on gains)
        if return_pct >= take_profit_pct:
            return TrailingStopExit(
                ticker=ticker,
                exit_date=position_data.iloc[-1]['date'],
                exit_price=current_price,
                reason=f"Take profit triggered at +{return_pct*100:.1f}% return",
                entry_price=entry_price,
                peak_price=peak_price,
                return_pct=return_pct,
                trigger_type='take_profit',
                confidence=95.0  # High confidence for profitable exits
            )
        
        # Check trailing stop
        trailing_stop_level = peak_price * (1 - trailing_stop_pct)
        
        if current_price <= trailing_stop_level:
            drawdown_from_peak = (peak_price - current_price) / peak_price
            
            # Confidence based on how clean the breakdown is
            confidence = 80.0
            if drawdown_from_peak > trailing_stop_pct * 1.5:
                confidence = 90.0  # Clear breakdown
            
            return TrailingStopExit(
                ticker=ticker,
                exit_date=position_data.iloc[-1]['date'],
                exit_price=current_price,
                reason=f"Trailing stop hit: {drawdown_from_peak*100:.1f}% from peak",
                entry_price=entry_price,
                peak_price=peak_price,
                return_pct=return_pct,
                trigger_type='trailing_stop',
                confidence=confidence
            )
        
        return None
    
    def batch_check_trailing_stop(
        self,
        positions: List[Dict],
        current_date: date,
        price_data_dict: Dict[str, pd.DataFrame],
        trailing_stop_pct: float = DEFAULT_TRAILING_STOP_PCT,
        take_profit_pct: float = DEFAULT_TAKE_PROFIT_PCT
    ) -> List[TrailingStopExit]:
        """
        Check trailing stop for multiple positions
        
        Args:
            positions: List of position dicts with keys:
                - ticker: Stock ticker
                - entry_date: Entry date
                - entry_price: Entry price
            current_date: Current date to check
            price_data_dict: Dict of ticker -> price DataFrame
            trailing_stop_pct: Trailing stop percentage
            take_profit_pct: Take profit percentage
            
        Returns:
            List of TrailingStopExit signals
        """
        
        exit_signals = []
        
        for position in positions:
            ticker = position['ticker']
            price_data = price_data_dict.get(ticker)
            
            if price_data is None:
                continue
            
            exit_signal = self.check_trailing_stop(
                ticker=ticker,
                entry_date=position['entry_date'],
                entry_price=position['entry_price'],
                current_date=current_date,
                price_data=price_data,
                trailing_stop_pct=trailing_stop_pct,
                take_profit_pct=take_profit_pct
            )
            
            if exit_signal:
                exit_signals.append(exit_signal)
        
        return exit_signals
    
    def calculate_position_metrics(
        self,
        entry_date: date,
        entry_price: float,
        current_date: date,
        price_data: pd.DataFrame
    ) -> Dict:
        """
        Calculate position metrics for monitoring
        
        Args:
            entry_date: Entry date
            entry_price: Entry price
            current_date: Current date
            price_data: Price DataFrame
            
        Returns:
            Dict with position metrics
        """
        
        if price_data is None or len(price_data) == 0:
            return {}
        
        # Filter price data
        price_data = price_data.sort_values('date')
        # Convert dates to pandas Timestamp for comparison
        entry_ts = pd.Timestamp(entry_date)
        current_ts = pd.Timestamp(current_date)
        mask = (price_data['date'] >= entry_ts) & (price_data['date'] <= current_ts)
        position_data = price_data[mask].copy()
        
        if len(position_data) == 0:
            return {}
        
        current_price = position_data.iloc[-1]['close']
        peak_price = position_data['close'].max()
        trough_price = position_data['close'].min()
        
        return_pct = (current_price - entry_price) / entry_price
        peak_return = (peak_price - entry_price) / entry_price
        max_drawdown = (peak_price - trough_price) / peak_price
        drawdown_from_peak = (peak_price - current_price) / peak_price
        
        return {
            'entry_price': entry_price,
            'current_price': current_price,
            'peak_price': peak_price,
            'trough_price': trough_price,
            'return_pct': return_pct,
            'peak_return_pct': peak_return,
            'max_drawdown_pct': max_drawdown,
            'drawdown_from_peak_pct': drawdown_from_peak,
            'days_held': len(position_data)
        }


# Test function
def test_trailing_stop_module():
    """Test the Trailing Stop Module"""
    print("\n" + "="*70)
    print("🧪 TESTING EXIT MODULE 3: TRAILING STOP/TAKE-PROFIT")
    print("="*70)
    
    # Create module
    module = TrailingStopModule()
    print("✅ TrailingStopModule created")
    
    # Create mock price data
    print("\n1. Creating mock price data...")
    dates = pd.date_range(start='2024-01-01', end='2024-06-30', freq='D')
    
    # Scenario 1: Price rises then falls (trailing stop trigger)
    prices_scenario1 = []
    base_price = 100.0
    for i, d in enumerate(dates):
        if i < 60:
            # Price rises
            price = base_price + (i * 0.5)
        else:
            # Price falls
            price = base_price + 30 - ((i - 60) * 0.7)
        prices_scenario1.append(price)
    
    price_data_1 = pd.DataFrame({
        'date': dates,
        'close': prices_scenario1,
        'high': [p * 1.01 for p in prices_scenario1],
        'low': [p * 0.99 for p in prices_scenario1]
    })
    print(f"   ✅ Scenario 1 data created: {len(price_data_1)} days")
    
    # Test 1: Check trailing stop trigger
    print("\n2. Testing trailing stop trigger...")
    exit_signal = module.check_trailing_stop(
        ticker="TEST1",
        entry_date=dates[0],
        entry_price=base_price,
        current_date=dates[-1],
        price_data=price_data_1,
        trailing_stop_pct=0.15
    )
    
    if exit_signal:
        print(f"   ✅ Exit signal generated!")
        print(f"      Type: {exit_signal.trigger_type}")
        print(f"      Exit price: ${exit_signal.exit_price:.2f}")
        print(f"      Peak price: ${exit_signal.peak_price:.2f}")
        print(f"      Return: {exit_signal.return_pct*100:.1f}%")
        print(f"      Confidence: {exit_signal.confidence:.1f}")
    else:
        print(f"   ⚠️  No exit signal (unexpected)")
    
    # Scenario 2: Price rises significantly (take profit trigger)
    prices_scenario2 = [base_price + (i * 0.8) for i in range(len(dates))]
    price_data_2 = pd.DataFrame({
        'date': dates,
        'close': prices_scenario2,
        'high': [p * 1.01 for p in prices_scenario2],
        'low': [p * 0.99 for p in prices_scenario2]
    })
    
    print("\n3. Testing take profit trigger...")
    exit_signal = module.check_trailing_stop(
        ticker="TEST2",
        entry_date=dates[0],
        entry_price=base_price,
        current_date=dates[-1],
        price_data=price_data_2,
        take_profit_pct=0.50
    )
    
    if exit_signal:
        print(f"   ✅ Exit signal generated!")
        print(f"      Type: {exit_signal.trigger_type}")
        print(f"      Exit price: ${exit_signal.exit_price:.2f}")
        print(f"      Return: {exit_signal.return_pct*100:.1f}%")
        print(f"      Confidence: {exit_signal.confidence:.1f}")
    else:
        print(f"   ⚠️  No exit signal (unexpected)")
    
    # Test 3: Calculate position metrics
    print("\n4. Testing position metrics calculation...")
    metrics = module.calculate_position_metrics(
        entry_date=dates[0],
        entry_price=base_price,
        current_date=dates[-1],
        price_data=price_data_1
    )
    print(f"   ✅ Metrics calculated:")
    print(f"      Current return: {metrics['return_pct']*100:.1f}%")
    print(f"      Peak return: {metrics['peak_return_pct']*100:.1f}%")
    print(f"      Max drawdown: {metrics['max_drawdown_pct']*100:.1f}%")
    print(f"      Days held: {metrics['days_held']}")
    
    # Test 4: Batch check
    print("\n5. Testing batch check...")
    test_positions = [
        {
            'ticker': 'TEST1',
            'entry_date': dates[0],
            'entry_price': base_price
        },
        {
            'ticker': 'TEST2',
            'entry_date': dates[0],
            'entry_price': base_price
        }
    ]
    
    price_data_dict = {
        'TEST1': price_data_1,
        'TEST2': price_data_2
    }
    
    exit_signals = module.batch_check_trailing_stop(
        positions=test_positions,
        current_date=dates[-1],
        price_data_dict=price_data_dict,
        trailing_stop_pct=0.15,
        take_profit_pct=0.50
    )
    print(f"   ✅ Batch check complete: {len(exit_signals)} exits triggered")
    for signal in exit_signals:
        print(f"      - {signal.ticker}: {signal.trigger_type} at {signal.return_pct*100:.1f}%")
    
    print("\n" + "="*70)
    print("✅ TRAILING STOP MODULE TEST COMPLETE")
    print("="*70)
    
    return True


if __name__ == "__main__":
    import sys
    success = test_trailing_stop_module()
    sys.exit(0 if success else 1)

