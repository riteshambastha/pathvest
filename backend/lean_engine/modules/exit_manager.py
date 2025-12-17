"""
Exit Manager Module - FR-3.1.C.11
Implements 4 exit modules for the strategy
"""

from AlgorithmImports import *
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple


class ExitManager:
    """
    Exit manager implementing 4 exit modules (FR-3.1.C.11):
    
    1. Mandatory Thesis Drift Exit (Smart Money Follow-through)
    2. Insider Reversal Exit (Form 4 Selling Spikes)
    3. Stop-Loss and Take-Profit (Trailing Stop)
    4. Time-Based Stale Exit (Dead Money Rule)
    """
    
    def __init__(
        self,
        algorithm,
        enable_thesis_drift: bool = True,
        enable_insider_reversal: bool = True,
        enable_trailing_stop: bool = True,
        trailing_stop_pct: float = 0.15,
        enable_dead_money: bool = True,
        dead_money_quarters: int = 4
    ):
        """
        Initialize exit manager
        
        Args:
            algorithm: LEAN algorithm instance
            enable_thesis_drift: Enable Module 1 (13F invalidation)
            enable_insider_reversal: Enable Module 2 (Form 4 selling cluster)
            enable_trailing_stop: Enable Module 3 (Trailing stop)
            trailing_stop_pct: Trailing stop percentage (default: 15%)
            enable_dead_money: Enable Module 4 (Time-based exit)
            dead_money_quarters: Quarters before dead money exit (default: 4)
        """
        self.algorithm = algorithm
        
        # Exit module enables
        self.enable_thesis_drift = enable_thesis_drift
        self.enable_insider_reversal = enable_insider_reversal
        self.enable_trailing_stop = enable_trailing_stop
        self.enable_dead_money = enable_dead_money
        
        # Exit parameters
        self.trailing_stop_pct = trailing_stop_pct
        self.dead_money_quarters = dead_money_quarters
        
        # Tracking data
        self.entry_dates = {}  # Symbol -> datetime
        self.high_water_marks = {}  # Symbol -> float (highest price since entry)
        self.qualified_institutions = {}  # Symbol -> Set[CIK] (institutions holding this stock)
    
    def on_position_opened(self, symbol: Symbol, entry_date: datetime, entry_price: float):
        """
        Track when a position is opened
        
        Args:
            symbol: Stock symbol
            entry_date: Date position was opened
            entry_price: Entry price
        """
        self.entry_dates[symbol] = entry_date
        self.high_water_marks[symbol] = entry_price
    
    def update_high_water_mark(self, symbol: Symbol, current_price: float):
        """
        Update high water mark for trailing stop
        
        Args:
            symbol: Stock symbol
            current_price: Current price
        """
        if symbol not in self.high_water_marks:
            self.high_water_marks[symbol] = current_price
        else:
            self.high_water_marks[symbol] = max(
                self.high_water_marks[symbol],
                current_price
            )
    
    def check_all_exit_conditions(
        self,
        symbol: Symbol,
        current_date: datetime,
        current_price: float,
        qualified_ciks: Optional[List[str]] = None,
        insider_selling_cluster: Optional[Dict] = None
    ) -> Tuple[bool, str]:
        """
        Check all exit conditions for a position
        
        Args:
            symbol: Stock symbol
            current_date: Current date
            current_price: Current price
            qualified_ciks: List of qualified institution CIKs still holding
            insider_selling_cluster: Dict with insider selling info
        
        Returns:
            (should_exit, reason)
        """
        # Module 1: Thesis Drift Exit
        if self.enable_thesis_drift:
            should_exit, reason = self.check_thesis_drift(symbol, qualified_ciks)
            if should_exit:
                return True, f"Module 1: {reason}"
        
        # Module 2: Insider Reversal Exit
        if self.enable_insider_reversal:
            should_exit, reason = self.check_insider_reversal(symbol, insider_selling_cluster)
            if should_exit:
                return True, f"Module 2: {reason}"
        
        # Module 3: Trailing Stop
        if self.enable_trailing_stop:
            should_exit, reason = self.check_trailing_stop(symbol, current_price)
            if should_exit:
                return True, f"Module 3: {reason}"
        
        # Module 4: Dead Money Exit
        if self.enable_dead_money:
            should_exit, reason = self.check_dead_money(symbol, current_date, current_price)
            if should_exit:
                return True, f"Module 4: {reason}"
        
        return False, ""
    
    # ==================== Module 1: Thesis Drift Exit ====================
    
    def check_thesis_drift(
        self,
        symbol: Symbol,
        qualified_ciks: Optional[List[str]]
    ) -> Tuple[bool, str]:
        """
        Exit Module 1: Mandatory Thesis Drift Exit (FR-3.1.C.11)
        
        Trigger if ANY of:
        - Stock no longer held by qualified funds
        - Net institutional ownership drops > 20% QoQ
        - Stock fails fundamental filters (e.g., market cap < $3B)
        
        Args:
            symbol: Stock symbol
            qualified_ciks: List of CIKs of qualified institutions still holding
        
        Returns:
            (should_exit, reason)
        """
        if qualified_ciks is None:
            # Can't determine - don't exit
            return False, ""
        
        # Check if still held by qualified institutions
        if len(qualified_ciks) == 0:
            return True, "No qualified institutions holding (thesis invalidated)"
        
        # Check if institutional ownership dropped significantly
        previous_cik_count = len(self.qualified_institutions.get(symbol, set()))
        current_cik_count = len(qualified_ciks)
        
        if previous_cik_count > 0:
            ownership_change_pct = (current_cik_count - previous_cik_count) / previous_cik_count
            
            if ownership_change_pct < -0.20:  # 20% drop
                return True, f"Institutional ownership dropped {abs(ownership_change_pct)*100:.1f}%"
        
        # Update tracked institutions
        self.qualified_institutions[symbol] = set(qualified_ciks)
        
        # Check fundamental filters (market cap)
        # In LEAN, we'd query fundamental data
        # For now, placeholder - would check if market cap < $3B
        
        return False, ""
    
    # ==================== Module 2: Insider Reversal Exit ====================
    
    def check_insider_reversal(
        self,
        symbol: Symbol,
        insider_selling_cluster: Optional[Dict]
    ) -> Tuple[bool, str]:
        """
        Exit Module 2: Insider Reversal Exit (FR-3.1.C.11)
        
        Trigger if:
        - Aggregate insider sales (30d) > $5M AND > 50% of insider holdings
        
        Args:
            symbol: Stock symbol
            insider_selling_cluster: Dict with:
                - total_sales_value: float
                - total_insider_holdings_value: float
        
        Returns:
            (should_exit, reason)
        """
        if not insider_selling_cluster:
            return False, ""
        
        total_sales = insider_selling_cluster.get('total_sales_value', 0)
        total_holdings = insider_selling_cluster.get('total_insider_holdings_value', 1)
        
        # Check conditions
        if total_sales > 5_000_000:  # $5M threshold
            sales_pct = total_sales / total_holdings if total_holdings > 0 else 0
            
            if sales_pct > 0.50:  # 50% threshold
                return True, f"Massive insider selling: ${total_sales/1e6:.1f}M ({sales_pct*100:.1f}% of holdings)"
        
        return False, ""
    
    # ==================== Module 3: Trailing Stop ====================
    
    def check_trailing_stop(
        self,
        symbol: Symbol,
        current_price: float
    ) -> Tuple[bool, str]:
        """
        Exit Module 3: Trailing Stop (FR-3.1.C.11)
        
        Logic: P_exit = Max(Price_history) × (1 - Trailing_Stop_Pct)
        
        Args:
            symbol: Stock symbol
            current_price: Current price
        
        Returns:
            (should_exit, reason)
        """
        # Update high water mark
        self.update_high_water_mark(symbol, current_price)
        
        high_water_mark = self.high_water_marks.get(symbol, current_price)
        
        # Calculate exit price
        exit_price = high_water_mark * (1 - self.trailing_stop_pct)
        
        if current_price < exit_price:
            drawdown_pct = ((high_water_mark - current_price) / high_water_mark) * 100
            return True, f"Trailing stop triggered: {drawdown_pct:.1f}% from high ${high_water_mark:.2f}"
        
        return False, ""
    
    # ==================== Module 4: Dead Money Exit ====================
    
    def check_dead_money(
        self,
        symbol: Symbol,
        current_date: datetime,
        current_price: float
    ) -> Tuple[bool, str]:
        """
        Exit Module 4: Dead Money Exit (FR-3.1.C.11)
        
        Trigger if:
        - Position held > 4 quarters (default) AND
        - Total return < 0%
        
        Args:
            symbol: Stock symbol
            current_date: Current date
            current_price: Current price
        
        Returns:
            (should_exit, reason)
        """
        entry_date = self.entry_dates.get(symbol)
        
        if not entry_date:
            return False, ""
        
        # Calculate holding period
        holding_days = (current_date - entry_date).days
        quarters_held = holding_days / 91  # ~91 days per quarter
        
        if quarters_held < self.dead_money_quarters:
            return False, ""
        
        # Check if unprofitable
        if symbol in self.algorithm.Portfolio:
            holding = self.algorithm.Portfolio[symbol]
            
            if holding.UnrealizedProfitPercent < 0:
                return True, (
                    f"Dead money: Held {quarters_held:.1f} quarters, "
                    f"Return: {holding.UnrealizedProfitPercent*100:.1f}%"
                )
        
        return False, ""
    
    # ==================== Execution ====================
    
    def execute_exit(self, symbol: Symbol, reason: str):
        """
        Execute exit order
        
        Args:
            symbol: Stock symbol to exit
            reason: Exit reason for logging
        """
        try:
            if self.algorithm.Portfolio[symbol].Invested:
                # Liquidate position
                self.algorithm.Liquidate(symbol, f"Exit: {reason}")
                
                # Log exit
                self.algorithm.Debug(f"EXITED {symbol.Value}: {reason}")
                
                # Clean up tracking
                if symbol in self.entry_dates:
                    del self.entry_dates[symbol]
                if symbol in self.high_water_marks:
                    del self.high_water_marks[symbol]
                if symbol in self.qualified_institutions:
                    del self.qualified_institutions[symbol]
        
        except Exception as e:
            self.algorithm.Debug(f"Error executing exit for {symbol.Value}: {e}")
    
    def check_and_execute_exits(
        self,
        current_date: datetime,
        holdings_data: Dict[Symbol, Dict]
    ):
        """
        Check all holdings for exit conditions and execute
        
        Args:
            current_date: Current date
            holdings_data: Dict mapping Symbol to data dict with:
                - current_price: float
                - qualified_ciks: List[str]
                - insider_selling_cluster: Optional[Dict]
        """
        for symbol, data in holdings_data.items():
            current_price = data.get('current_price', 0)
            qualified_ciks = data.get('qualified_ciks')
            insider_selling_cluster = data.get('insider_selling_cluster')
            
            should_exit, reason = self.check_all_exit_conditions(
                symbol=symbol,
                current_date=current_date,
                current_price=current_price,
                qualified_ciks=qualified_ciks,
                insider_selling_cluster=insider_selling_cluster
            )
            
            if should_exit:
                self.execute_exit(symbol, reason)

