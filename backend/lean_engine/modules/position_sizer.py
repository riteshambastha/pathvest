"""
Position Sizer Module - FR-3.1.C.4
Handles position sizing and portfolio constraints
"""

from AlgorithmImports import *
from typing import Dict, List, Optional


class PositionSizer:
    """
    Position sizing manager for institutional following strategy
    
    Constraints (FR-3.1.C.4):
    - Static position size: 5% of total portfolio value
    - Min 5 stocks to be active (Cash Drag Management - FR-3.1.C.10.3)
    - Max 20 stocks
    - Rank Buffer: B=5 spots (FR-3.1.C.10.2)
    """
    
    DEFAULT_POSITION_SIZE_PCT = 0.05  # 5%
    MIN_POSITIONS = 5
    MAX_POSITIONS = 20
    RANK_BUFFER = 5
    
    def __init__(
        self,
        algorithm,
        position_size_pct: float = DEFAULT_POSITION_SIZE_PCT,
        min_positions: int = MIN_POSITIONS,
        max_positions: int = MAX_POSITIONS,
        rank_buffer: int = RANK_BUFFER
    ):
        """
        Initialize position sizer
        
        Args:
            algorithm: LEAN algorithm instance
            position_size_pct: Target position size as % of portfolio
            min_positions: Minimum number of positions
            max_positions: Maximum number of positions
            rank_buffer: Rank buffer for churn prevention
        """
        self.algorithm = algorithm
        self.position_size_pct = position_size_pct
        self.min_positions = min_positions
        self.max_positions = max_positions
        self.rank_buffer = rank_buffer
    
    def calculate_target_quantity(
        self,
        symbol: Symbol,
        current_price: float
    ) -> float:
        """
        Calculate target quantity for a position
        
        Args:
            symbol: Stock symbol
            current_price: Current stock price
        
        Returns:
            Target quantity (fractional shares allowed)
        """
        if current_price <= 0:
            return 0
        
        # Get current portfolio value
        portfolio_value = self.algorithm.Portfolio.TotalPortfolioValue
        
        # Calculate target dollar amount for this position
        target_value = portfolio_value * self.position_size_pct
        
        # Calculate shares needed
        target_quantity = target_value / current_price
        
        return target_quantity
    
    def get_rebalance_orders(
        self,
        ranked_candidates: List[Dict],
        current_holdings: Dict[Symbol, Holding]
    ) -> Dict[str, List]:
        """
        Determine which positions to enter, exit, or rebalance
        
        Implements Rank Buffer logic (FR-3.1.C.10.2):
        - New candidate enters only if Rank < (Worst_Holding_Rank - Buffer)
        
        Args:
            ranked_candidates: List of candidates with conviction scores and ranks
            current_holdings: Current portfolio holdings
        
        Returns:
            Dict with 'entries', 'exits', 'holds', 'rebalances'
        """
        orders = {
            'entries': [],
            'exits': [],
            'holds': [],
            'rebalances': []
        }
        
        # Cash Drag Management (FR-3.1.C.10.3)
        if len(ranked_candidates) < self.min_positions:
            # Insufficient candidates - go to 100% cash
            self.algorithm.Debug(
                f"Cash Drag: Only {len(ranked_candidates)} candidates (need {self.min_positions}). "
                "Moving to 100% cash."
            )
            
            # Exit all positions
            for symbol in current_holdings.keys():
                orders['exits'].append({
                    'symbol': symbol,
                    'reason': 'cash_drag_insufficient_candidates'
                })
            
            return orders
        
        # Get current position count
        current_position_count = len([h for h in current_holdings.values() if h.Quantity > 0])
        
        # Select top candidates (up to max_positions)
        top_candidates = ranked_candidates[:self.max_positions]
        
        # Create lookup for current holdings by ticker
        holdings_by_ticker = {
            holding.Symbol.Value: holding
            for holding in current_holdings.values()
            if holding.Quantity > 0
        }
        
        # Identify candidates already held
        for candidate in top_candidates:
            ticker = candidate.get('ticker')
            symbol_str = ticker
            
            if ticker in holdings_by_ticker:
                # Already holding this stock
                orders['holds'].append({
                    'ticker': ticker,
                    'rank': candidate.get('rank'),
                    'conviction_score': candidate.get('conviction_score')
                })
            else:
                # New candidate - check rank buffer
                if current_position_count < self.max_positions:
                    # Have room for new position
                    orders['entries'].append(candidate)
                else:
                    # At capacity - need to check rank buffer
                    # Find worst current holding
                    worst_rank = float('inf')
                    worst_ticker = None
                    
                    for hold in orders['holds']:
                        if hold.get('rank', 0) > worst_rank:
                            worst_rank = hold['rank']
                            worst_ticker = hold['ticker']
                    
                    candidate_rank = candidate.get('rank', 0)
                    
                    # Apply rank buffer
                    if candidate_rank < (worst_rank - self.rank_buffer):
                        # Qualifies for entry
                        orders['entries'].append(candidate)
                        
                        # Mark worst holding for exit
                        if worst_ticker:
                            orders['exits'].append({
                                'ticker': worst_ticker,
                                'reason': f'rank_buffer_replacement (rank {worst_rank} -> {candidate_rank})'
                            })
                            
                            # Remove from holds
                            orders['holds'] = [
                                h for h in orders['holds']
                                if h['ticker'] != worst_ticker
                            ]
        
        # Check for positions to exit (no longer in top candidates)
        top_tickers = set(c.get('ticker') for c in top_candidates)
        
        for ticker, holding in holdings_by_ticker.items():
            if ticker not in top_tickers:
                # Position no longer qualified
                orders['exits'].append({
                    'ticker': ticker,
                    'reason': 'no_longer_qualified'
                })
        
        return orders
    
    def execute_rebalance_orders(self, orders: Dict[str, List]):
        """
        Execute the rebalance orders
        
        Args:
            orders: Dict with entries, exits, holds, rebalances
        """
        # Execute exits first
        for exit_order in orders['exits']:
            ticker = exit_order.get('ticker')
            reason = exit_order.get('reason', 'rebalance')
            
            try:
                symbol = Symbol.Create(ticker, SecurityType.Equity, Market.USA)
                
                if self.algorithm.Portfolio[symbol].Invested:
                    self.algorithm.Liquidate(symbol, f"Exit: {reason}")
                    self.algorithm.Debug(f"Exited {ticker}: {reason}")
            
            except Exception as e:
                self.algorithm.Debug(f"Error exiting {ticker}: {e}")
        
        # Execute entries
        for candidate in orders['entries']:
            ticker = candidate.get('ticker')
            
            try:
                symbol = Symbol.Create(ticker, SecurityType.Equity, Market.USA)
                
                # Get current price
                if symbol in self.algorithm.Securities:
                    current_price = self.algorithm.Securities[symbol].Price
                else:
                    # Add security if not already added
                    self.algorithm.AddEquity(ticker, Resolution.Daily)
                    current_price = self.algorithm.Securities[symbol].Price
                
                if current_price > 0:
                    # Calculate target quantity
                    target_quantity = self.calculate_target_quantity(symbol, current_price)
                    
                    if target_quantity > 0:
                        # Place order
                        self.algorithm.SetHoldings(symbol, self.position_size_pct)
                        
                        self.algorithm.Debug(
                            f"Entered {ticker}: Rank {candidate.get('rank')}, "
                            f"Conviction {candidate.get('conviction_score', 0):.1f}"
                        )
            
            except Exception as e:
                self.algorithm.Debug(f"Error entering {ticker}: {e}")
    
    def get_position_size_for_symbol(self, symbol: Symbol) -> float:
        """
        Get target position size for a symbol
        
        Args:
            symbol: Stock symbol
        
        Returns:
            Position size as decimal (e.g., 0.05 for 5%)
        """
        return self.position_size_pct
    
    def should_go_to_cash(self, num_candidates: int) -> bool:
        """
        Check if should move to 100% cash due to insufficient candidates
        
        Args:
            num_candidates: Number of qualified candidates
        
        Returns:
            True if should go to cash
        """
        return num_candidates < self.min_positions

