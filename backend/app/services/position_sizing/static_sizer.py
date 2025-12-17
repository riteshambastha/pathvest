"""
Static Position Sizing Module
Per SRS FR-3.1.C.10: Position Sizing & Portfolio Constraints

Implements:
- 5% static position size
- Rank buffer (B=5) for churn prevention
- Min/Max position constraints (5-20 stocks)
- Cash drag management (<5 candidates → 100% cash)
- Rebalancing logic (monthly/quarterly)
"""

from typing import Dict, List, Optional, Tuple
from datetime import date, datetime
from dataclasses import dataclass
import pandas as pd


@dataclass
class PositionAllocation:
    """Represents a position allocation"""
    ticker: str
    weight: float  # 0-1 (percentage of portfolio)
    shares: Optional[float] = None  # Calculated based on portfolio value
    conviction_score: Optional[float] = None
    rank: Optional[int] = None


@dataclass
class PortfolioAllocation:
    """Represents complete portfolio allocation"""
    positions: List[PositionAllocation]
    cash_weight: float  # 0-1 (percentage in cash)
    total_invested: float  # 0-1 (percentage invested)
    rebalance_date: date
    num_positions: int
    allocation_reason: str


class StaticPositionSizer:
    """
    Static Position Sizing Implementation
    
    Per SRS FR-3.1.C.10:
    - Static 5% position size per stock
    - Portfolio constraint: 5-20 stocks
    - Rank buffer: B=5 positions
    - Cash drag: <5 candidates → 100% cash
    
    Logic:
    1. Sort candidates by conviction score
    2. Apply rank buffer to prevent churn
    3. Select top N candidates (max 20)
    4. Allocate 5% to each position
    5. Remaining to cash
    """
    
    DEFAULT_POSITION_SIZE = 0.05  # 5%
    MIN_POSITIONS = 5
    MAX_POSITIONS = 20
    RANK_BUFFER = 5
    
    def __init__(
        self,
        position_size: float = DEFAULT_POSITION_SIZE,
        min_positions: int = MIN_POSITIONS,
        max_positions: int = MAX_POSITIONS,
        rank_buffer: int = RANK_BUFFER
    ):
        """
        Initialize Static Position Sizer
        
        Args:
            position_size: Target position size (default 5%)
            min_positions: Minimum positions (default 5)
            max_positions: Maximum positions (default 20)
            rank_buffer: Rank buffer for churn prevention (default 5)
        """
        self.position_size = position_size
        self.min_positions = min_positions
        self.max_positions = max_positions
        self.rank_buffer = rank_buffer
    
    def calculate_allocation(
        self,
        candidates: List[Dict],
        current_holdings: Optional[List[Dict]] = None,
        rebalance_date: Optional[date] = None
    ) -> PortfolioAllocation:
        """
        Calculate portfolio allocation with rank buffer
        
        Args:
            candidates: List of candidate stocks with 'ticker' and 'conviction_score'
            current_holdings: Current portfolio holdings (for rank buffer)
            rebalance_date: Date of rebalancing
            
        Returns:
            PortfolioAllocation object
        """
        
        if rebalance_date is None:
            rebalance_date = date.today()
        
        # Sort candidates by conviction score (descending)
        sorted_candidates = sorted(
            candidates,
            key=lambda x: x.get('conviction_score', 0),
            reverse=True
        )
        
        # Apply rank buffer if we have current holdings
        if current_holdings:
            selected_tickers = self._apply_rank_buffer(
                sorted_candidates,
                current_holdings
            )
        else:
            # No current holdings, just take top N
            selected_tickers = [c['ticker'] for c in sorted_candidates[:self.max_positions]]
        
        # Check minimum position constraint
        if len(selected_tickers) < self.min_positions:
            # Cash drag: Not enough candidates
            return PortfolioAllocation(
                positions=[],
                cash_weight=1.0,
                total_invested=0.0,
                rebalance_date=rebalance_date,
                num_positions=0,
                allocation_reason=f"Cash drag: Only {len(selected_tickers)} candidates (min {self.min_positions} required)"
            )
        
        # Create position allocations
        positions = []
        for i, ticker in enumerate(selected_tickers):
            # Find candidate info
            candidate_info = next((c for c in sorted_candidates if c['ticker'] == ticker), {})
            
            positions.append(PositionAllocation(
                ticker=ticker,
                weight=self.position_size,
                conviction_score=candidate_info.get('conviction_score'),
                rank=i + 1
            ))
        
        # Calculate total invested and cash
        total_invested = len(positions) * self.position_size
        cash_weight = max(0, 1.0 - total_invested)
        
        return PortfolioAllocation(
            positions=positions,
            cash_weight=cash_weight,
            total_invested=total_invested,
            rebalance_date=rebalance_date,
            num_positions=len(positions),
            allocation_reason=f"Allocated {len(positions)} positions at {self.position_size*100:.1f}% each"
        )
    
    def _apply_rank_buffer(
        self,
        sorted_candidates: List[Dict],
        current_holdings: List[Dict]
    ) -> List[str]:
        """
        Apply rank buffer to prevent excessive churn
        
        Per SRS: Rank buffer B=5
        - Current holdings within top (N + B) ranks are retained
        - Example: If holding 20 stocks, keep all in top 25
        
        Args:
            sorted_candidates: Sorted list of candidates (by conviction)
            current_holdings: Current portfolio holdings
            
        Returns:
            List of selected ticker symbols
        """
        
        # Get current holding tickers
        current_tickers = {h['ticker'] for h in current_holdings}
        
        # Create rank map for candidates
        candidate_ranks = {
            c['ticker']: i + 1
            for i, c in enumerate(sorted_candidates)
        }
        
        # Apply buffer: Keep current holdings within top (N + B)
        buffer_threshold = self.max_positions + self.rank_buffer
        
        retained_tickers = []
        for ticker in current_tickers:
            rank = candidate_ranks.get(ticker, float('inf'))
            if rank <= buffer_threshold:
                retained_tickers.append(ticker)
        
        # Add new candidates to fill up to max_positions
        selected_tickers = retained_tickers.copy()
        
        for candidate in sorted_candidates:
            ticker = candidate['ticker']
            if ticker not in selected_tickers:
                if len(selected_tickers) < self.max_positions:
                    selected_tickers.append(ticker)
                else:
                    break
        
        return selected_tickers
    
    def calculate_share_quantities(
        self,
        allocation: PortfolioAllocation,
        portfolio_value: float,
        current_prices: Dict[str, float]
    ) -> PortfolioAllocation:
        """
        Calculate share quantities for each position
        
        Args:
            allocation: Portfolio allocation
            portfolio_value: Total portfolio value
            current_prices: Dict of ticker -> current price
            
        Returns:
            Updated PortfolioAllocation with share quantities
        """
        
        for position in allocation.positions:
            ticker = position.ticker
            target_value = portfolio_value * position.weight
            
            price = current_prices.get(ticker)
            if price and price > 0:
                position.shares = target_value / price
        
        return allocation
    
    def should_rebalance(
        self,
        last_rebalance_date: date,
        current_date: date,
        frequency: str = 'monthly'
    ) -> bool:
        """
        Determine if rebalancing should occur
        
        Args:
            last_rebalance_date: Date of last rebalance
            current_date: Current date
            frequency: 'monthly' or 'quarterly'
            
        Returns:
            True if rebalancing should occur
        """
        
        if frequency == 'monthly':
            # Rebalance if month changed
            return (current_date.year, current_date.month) != (last_rebalance_date.year, last_rebalance_date.month)
        elif frequency == 'quarterly':
            # Rebalance if quarter changed
            current_quarter = (current_date.month - 1) // 3
            last_quarter = (last_rebalance_date.month - 1) // 3
            return (current_date.year, current_quarter) != (last_rebalance_date.year, last_quarter)
        else:
            raise ValueError(f"Invalid frequency: {frequency}")
    
    def calculate_rebalance_trades(
        self,
        current_allocation: PortfolioAllocation,
        target_allocation: PortfolioAllocation,
        portfolio_value: float,
        current_prices: Dict[str, float]
    ) -> List[Dict]:
        """
        Calculate trades needed to rebalance from current to target
        
        Args:
            current_allocation: Current portfolio allocation
            target_allocation: Target portfolio allocation
            portfolio_value: Total portfolio value
            current_prices: Current stock prices
            
        Returns:
            List of trade instructions
        """
        
        trades = []
        
        # Create position maps
        current_positions = {p.ticker: p for p in current_allocation.positions}
        target_positions = {p.ticker: p for p in target_allocation.positions}
        
        # Calculate sells (positions to exit or reduce)
        for ticker, current_pos in current_positions.items():
            if ticker not in target_positions:
                # Exit position
                trades.append({
                    'ticker': ticker,
                    'action': 'sell',
                    'shares': current_pos.shares,
                    'reason': 'Exit position (not in target allocation)'
                })
            else:
                # Check if size needs adjustment
                target_pos = target_positions[ticker]
                if target_pos.shares and current_pos.shares:
                    share_diff = target_pos.shares - current_pos.shares
                    if abs(share_diff) > 0.01:  # Small threshold to avoid tiny trades
                        trades.append({
                            'ticker': ticker,
                            'action': 'sell' if share_diff < 0 else 'buy',
                            'shares': abs(share_diff),
                            'reason': 'Rebalance position'
                        })
        
        # Calculate buys (new positions)
        for ticker, target_pos in target_positions.items():
            if ticker not in current_positions:
                trades.append({
                    'ticker': ticker,
                    'action': 'buy',
                    'shares': target_pos.shares,
                    'reason': 'New position'
                })
        
        return trades


# Test function
def test_static_position_sizer():
    """Test the Static Position Sizer"""
    print("\n" + "="*70)
    print("🧪 TESTING POSITION SIZING MODULE")
    print("="*70)
    
    # Create sizer
    sizer = StaticPositionSizer(
        position_size=0.05,  # 5%
        min_positions=5,
        max_positions=20,
        rank_buffer=5
    )
    print("✅ StaticPositionSizer created")
    print(f"   Position size: {sizer.position_size*100:.1f}%")
    print(f"   Min/Max positions: {sizer.min_positions}-{sizer.max_positions}")
    print(f"   Rank buffer: {sizer.rank_buffer}")
    
    # Test 1: Basic allocation with sufficient candidates
    print("\n" + "="*70)
    print("TEST 1: Basic Allocation (15 candidates)")
    print("="*70)
    
    candidates = [
        {'ticker': f'STOCK{i}', 'conviction_score': 100 - i*2}
        for i in range(15)
    ]
    
    allocation = sizer.calculate_allocation(
        candidates=candidates,
        rebalance_date=date(2024, 1, 1)
    )
    
    print(f"✅ Allocation calculated:")
    print(f"   Positions: {allocation.num_positions}")
    print(f"   Total invested: {allocation.total_invested*100:.1f}%")
    print(f"   Cash: {allocation.cash_weight*100:.1f}%")
    print(f"   Reason: {allocation.allocation_reason}")
    print(f"\n   Top 5 positions:")
    for pos in allocation.positions[:5]:
        print(f"      {pos.ticker}: {pos.weight*100:.1f}% (conviction: {pos.conviction_score:.1f})")
    
    # Test 2: Cash drag (insufficient candidates)
    print("\n" + "="*70)
    print("TEST 2: Cash Drag (only 3 candidates)")
    print("="*70)
    
    few_candidates = [
        {'ticker': f'STOCK{i}', 'conviction_score': 90 - i*5}
        for i in range(3)
    ]
    
    allocation_cash = sizer.calculate_allocation(
        candidates=few_candidates,
        rebalance_date=date(2024, 1, 1)
    )
    
    print(f"✅ Allocation calculated:")
    print(f"   Positions: {allocation_cash.num_positions}")
    print(f"   Total invested: {allocation_cash.total_invested*100:.1f}%")
    print(f"   Cash: {allocation_cash.cash_weight*100:.1f}%")
    print(f"   Reason: {allocation_cash.allocation_reason}")
    
    # Test 3: Rank buffer (with current holdings)
    print("\n" + "="*70)
    print("TEST 3: Rank Buffer (existing portfolio)")
    print("="*70)
    
    # Simulate current holdings
    current_holdings = [
        {'ticker': f'STOCK{i}'} for i in range(10)
    ]
    
    # New candidates where some old stocks dropped in rank
    new_candidates = [
        {'ticker': 'NEWSTOCK1', 'conviction_score': 100},
        {'ticker': 'NEWSTOCK2', 'conviction_score': 98},
        {'ticker': 'STOCK0', 'conviction_score': 96},
        {'ticker': 'STOCK1', 'conviction_score': 94},
        {'ticker': 'STOCK2', 'conviction_score': 92},
        {'ticker': 'STOCK3', 'conviction_score': 90},
        {'ticker': 'STOCK4', 'conviction_score': 88},
        {'ticker': 'STOCK5', 'conviction_score': 86},
        {'ticker': 'STOCK6', 'conviction_score': 84},
        {'ticker': 'STOCK7', 'conviction_score': 82},
        {'ticker': 'STOCK8', 'conviction_score': 80},  # Still in top 25
        {'ticker': 'STOCK9', 'conviction_score': 78},  # Still in top 25
        {'ticker': 'NEWSTOCK3', 'conviction_score': 76},
    ]
    
    allocation_buffer = sizer.calculate_allocation(
        candidates=new_candidates,
        current_holdings=current_holdings,
        rebalance_date=date(2024, 2, 1)
    )
    
    print(f"✅ Allocation with rank buffer:")
    print(f"   Positions: {allocation_buffer.num_positions}")
    old_tickers = set(h['ticker'] for h in current_holdings)
    retained = [p.ticker for p in allocation_buffer.positions if p.ticker in old_tickers]
    new_added = [p.ticker for p in allocation_buffer.positions if p.ticker not in old_tickers]
    print(f"   Retained from old: {len(retained)} positions")
    print(f"   New additions: {len(new_added)} positions")
    print(f"   Retained tickers: {', '.join(retained[:5])}...")
    print(f"   New tickers: {', '.join(new_added)}")
    
    # Test 4: Share quantity calculation
    print("\n" + "="*70)
    print("TEST 4: Share Quantity Calculation")
    print("="*70)
    
    portfolio_value = 100_000  # $100K
    current_prices = {
        pos.ticker: 50.0 + (i * 5)  # Varying prices
        for i, pos in enumerate(allocation.positions)
    }
    
    allocation_with_shares = sizer.calculate_share_quantities(
        allocation=allocation,
        portfolio_value=portfolio_value,
        current_prices=current_prices
    )
    
    print(f"✅ Share quantities calculated:")
    print(f"   Portfolio value: ${portfolio_value:,.0f}")
    print(f"\n   First 5 positions:")
    for pos in allocation_with_shares.positions[:5]:
        price = current_prices[pos.ticker]
        value = pos.shares * price if pos.shares else 0
        print(f"      {pos.ticker}: {pos.shares:.2f} shares @ ${price:.2f} = ${value:,.0f}")
    
    # Test 5: Rebalancing check
    print("\n" + "="*70)
    print("TEST 5: Rebalancing Logic")
    print("="*70)
    
    last_rebalance = date(2024, 1, 15)
    
    # Same month
    should_rebalance_same = sizer.should_rebalance(last_rebalance, date(2024, 1, 25), 'monthly')
    print(f"   Same month (Jan 15 → Jan 25): {should_rebalance_same} (should be False)")
    
    # Next month
    should_rebalance_next = sizer.should_rebalance(last_rebalance, date(2024, 2, 5), 'monthly')
    print(f"   Next month (Jan 15 → Feb 5): {should_rebalance_next} (should be True)")
    
    # Quarterly
    should_rebalance_q = sizer.should_rebalance(last_rebalance, date(2024, 4, 1), 'quarterly')
    print(f"   Next quarter (Jan 15 → Apr 1): {should_rebalance_q} (should be True)")
    
    # Test 6: Rebalance trade calculation
    print("\n" + "="*70)
    print("TEST 6: Rebalance Trade Calculation")
    print("="*70)
    
    # Simulate scenario where we need to rebalance
    current_simple = PortfolioAllocation(
        positions=[
            PositionAllocation('STOCK0', 0.05, 100.0, 95, 1),
            PositionAllocation('STOCK1', 0.05, 100.0, 93, 2),
            PositionAllocation('STOCK2', 0.05, 100.0, 91, 3),
        ],
        cash_weight=0.85,
        total_invested=0.15,
        rebalance_date=date(2024, 1, 1),
        num_positions=3,
        allocation_reason="Test"
    )
    
    target_simple = PortfolioAllocation(
        positions=[
            PositionAllocation('STOCK1', 0.05, 100.0, 93, 1),  # Keep
            PositionAllocation('STOCK3', 0.05, 100.0, 89, 2),  # New
            PositionAllocation('STOCK4', 0.05, 100.0, 87, 3),  # New
        ],
        cash_weight=0.85,
        total_invested=0.15,
        rebalance_date=date(2024, 2, 1),
        num_positions=3,
        allocation_reason="Test"
    )
    
    trades = sizer.calculate_rebalance_trades(
        current_allocation=current_simple,
        target_allocation=target_simple,
        portfolio_value=portfolio_value,
        current_prices={'STOCK0': 50, 'STOCK1': 50, 'STOCK2': 50, 'STOCK3': 50, 'STOCK4': 50}
    )
    
    print(f"✅ Rebalance trades calculated: {len(trades)} trades")
    for trade in trades:
        print(f"   {trade['action'].upper()} {trade['shares']:.2f} shares of {trade['ticker']}")
        print(f"      Reason: {trade['reason']}")
    
    print("\n" + "="*70)
    print("✅ ALL POSITION SIZING TESTS COMPLETE")
    print("="*70)
    
    return True


if __name__ == "__main__":
    import sys
    success = test_static_position_sizer()
    sys.exit(0 if success else 1)

