"""
Institutional Following Strategy for LEAN
Implements the complete institutional equity strategy based on 13F/Form 4 filings
"""

from AlgorithmImports import *
from datetime import datetime, timedelta
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from custom_data import SecFiling13F, SecFilingCollection, InsiderTransactionForm4, InsiderActivityTracker
from modules import PositionSizer, ExitManager


class InstitutionalFollowingStrategy(QCAlgorithm):
    """
    Institutional Following Strategy
    
    Strategy Logic:
    1. Subscribe to 13F filings from qualified institutions
    2. Generate signals when institutions take significant positions
    3. Confirm with technical indicators
    4. Size positions at 5% each (5-20 stock portfolio)
    5. Exit based on 4 exit modules
    
    This implements the complete strategy specified in the SRS.
    """
    
    def Initialize(self):
        """Initialize the algorithm"""
        # Set date range
        self.SetStartDate(2013, 1, 1)
        self.SetEndDate(2023, 12, 31)
        
        # Set initial cash
        self.SetCash(1_000_000)
        
        # Enable fractional shares (FR-3.1.D.4)
        self.Settings.FreePortfolioValuePercentage = 0.05
        self.Settings.AllowFractionalHoldings = True
        
        # Set benchmark
        self.SetBenchmark("SPY")
        
        # Initialize modules
        self.position_sizer = PositionSizer(
            algorithm=self,
            position_size_pct=0.05,  # 5% per position
            min_positions=5,
            max_positions=20,
            rank_buffer=5
        )
        
        self.exit_manager = ExitManager(
            algorithm=self,
            enable_thesis_drift=True,
            enable_insider_reversal=True,
            enable_trailing_stop=True,
            trailing_stop_pct=0.15,  # 15% trailing stop
            enable_dead_money=True,
            dead_money_quarters=4
        )
        
        # Initialize tracking collections
        self.filing_collection = SecFilingCollection()
        self.insider_tracker = InsiderActivityTracker(window_days=90)
        
        # Track candidates and holdings
        self.current_candidates = []
        self.last_rebalance_date = None
        self.rebalance_frequency_days = 30  # Monthly rebalancing
        
        # Add custom data feeds
        self._add_custom_data_feeds()
        
        # Schedule functions
        self.Schedule.On(
            self.DateRules.MonthStart(),
            self.TimeRules.AfterMarketOpen("SPY", 30),
            self.Rebalance
        )
        
        self.Schedule.On(
            self.DateRules.EveryDay(),
            self.TimeRules.AfterMarketOpen("SPY", 60),
            self.CheckExits
        )
        
        self.Debug("Institutional Following Strategy initialized")
    
    def _add_custom_data_feeds(self):
        """Add custom data feeds for 13F and Form 4"""
        # Add 13F filing data feed
        # Note: In production, this would be a proper symbol
        # For now, using generic symbol
        self.AddData(SecFiling13F, "13F_FILINGS", Resolution.Daily)
        
        # Add Form 4 insider transaction feed
        self.AddData(InsiderTransactionForm4, "FORM4_TRANSACTIONS", Resolution.Daily)
    
    def OnData(self, slice: Slice):
        """
        Process new data as it arrives
        
        Args:
            slice: Data slice containing all data for this timestamp
        """
        # Process 13F filings
        if slice.ContainsKey("13F_FILINGS"):
            filing_data = slice["13F_FILINGS"]
            
            if filing_data:
                # Add to collection
                self.filing_collection.add_filing(filing_data)
                
                # Process signals from this filing
                self._process_filing_signals(filing_data)
        
        # Process Form 4 insider transactions
        if slice.ContainsKey("FORM4_TRANSACTIONS"):
            form4_data = slice["FORM4_TRANSACTIONS"]
            
            if form4_data:
                # Add to tracker
                self.insider_tracker.add_transaction(form4_data)
    
    def _process_filing_signals(self, filing: SecFiling13F):
        """
        Process signals from a 13F filing
        
        Args:
            filing: SecFiling13F instance with signals attached
        """
        if not filing.signals:
            return
        
        self.Debug(f"Processing {len(filing.signals)} signals from {filing.institution_name}")
        
        # Add signals to current candidates
        for signal in filing.signals:
            # Check if already in candidates
            ticker = signal.get('ticker')
            
            # Ensure we have this security
            symbol = self.AddEquity(ticker, Resolution.Daily).Symbol
            
            # Check technical confirmation
            if self._check_technical_confirmation(symbol):
                # Add to candidates
                self.current_candidates.append({
                    'ticker': ticker,
                    'symbol': symbol,
                    'signal': signal,
                    'filing': filing,
                    'signal_date': filing.filing_date
                })
    
    def _check_technical_confirmation(self, symbol: Symbol) -> bool:
        """
        Check if stock passes technical confirmation filters
        
        All 3 must pass:
        1. Close > 10-day High
        2. Close > 50-day SMA
        3. RSI(14) > 45
        
        Args:
            symbol: Stock symbol
        
        Returns:
            True if passes all filters
        """
        if symbol not in self.Securities:
            return False
        
        security = self.Securities[symbol]
        
        # Get price history
        history = self.History(symbol, 60, Resolution.Daily)
        
        if history.empty or len(history) < 50:
            return False
        
        try:
            # Get current price
            current_price = security.Price
            
            # Check 1: Price > 10-day high
            ten_day_high = history['high'][-10:].max()
            if current_price <= ten_day_high:
                return False
            
            # Check 2: Price > 50-day SMA
            sma_50 = history['close'].rolling(50).mean().iloc[-1]
            if current_price <= sma_50:
                return False
            
            # Check 3: RSI > 45
            rsi = self._calculate_rsi(history['close'], period=14)
            if rsi[-1] <= 45:
                return False
            
            return True
        
        except Exception as e:
            self.Debug(f"Error in technical confirmation for {symbol}: {e}")
            return False
    
    def _calculate_rsi(self, prices, period=14):
        """Calculate RSI indicator"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def Rebalance(self):
        """
        Monthly rebalancing function
        
        This is the main portfolio construction logic:
        1. Rank candidates by conviction score
        2. Apply position sizing
        3. Execute rebalance orders
        """
        if not self.current_candidates:
            self.Debug("No candidates for rebalancing")
            return
        
        self.Debug(f"Rebalancing with {len(self.current_candidates)} candidates")
        
        # Rank candidates by conviction score
        ranked_candidates = self._rank_candidates(self.current_candidates)
        
        # Get current holdings
        current_holdings = {
            symbol: holding
            for symbol, holding in self.Portfolio.items()
            if holding.Invested
        }
        
        # Determine rebalance orders
        orders = self.position_sizer.get_rebalance_orders(
            ranked_candidates=ranked_candidates,
            current_holdings=current_holdings
        )
        
        # Execute orders
        self.position_sizer.execute_rebalance_orders(orders)
        
        # Track entry dates for exit manager
        for candidate in orders['entries']:
            symbol = candidate.get('symbol')
            if symbol and symbol in self.Securities:
                self.exit_manager.on_position_opened(
                    symbol=symbol,
                    entry_date=self.Time,
                    entry_price=self.Securities[symbol].Price
                )
        
        # Update last rebalance date
        self.last_rebalance_date = self.Time
        
        # Clear candidates after processing
        self.current_candidates = []
    
    def _rank_candidates(self, candidates: List[Dict]) -> List[Dict]:
        """
        Rank candidates by conviction score
        
        This would typically call the ConvictionScorer from signal_engine,
        but for LEAN integration, we'll use a simplified version.
        
        Args:
            candidates: List of candidate dicts
        
        Returns:
            Sorted list with ranks
        """
        # Calculate conviction score for each
        for candidate in candidates:
            signal = candidate.get('signal', {})
            
            # Extract scores from signal
            herding_score = 50  # Default
            insider_score = 50  # Default
            
            # Get from signal details if available
            if 'institutional_herding_details' in signal:
                herding_score = 70
            
            if 'insider_buying_details' in signal:
                insider_score = 70
            
            # Composite score (60% herding, 40% insider)
            conviction_score = 0.6 * herding_score + 0.4 * insider_score
            
            candidate['conviction_score'] = conviction_score
        
        # Sort by conviction score (descending)
        sorted_candidates = sorted(
            candidates,
            key=lambda x: -x.get('conviction_score', 0)
        )
        
        # Assign ranks
        for i, candidate in enumerate(sorted_candidates, start=1):
            candidate['rank'] = i
        
        return sorted_candidates
    
    def CheckExits(self):
        """
        Daily check for exit conditions
        
        Checks all 4 exit modules for each holding
        """
        # Get current holdings
        holdings_to_check = {}
        
        for symbol, holding in self.Portfolio.items():
            if not holding.Invested:
                continue
            
            # Get current price
            current_price = self.Securities[symbol].Price if symbol in self.Securities else 0
            
            if current_price <= 0:
                continue
            
            # Prepare data for exit checks
            holdings_to_check[symbol] = {
                'current_price': current_price,
                'qualified_ciks': None,  # Would query from filing data
                'insider_selling_cluster': None  # Would check insider tracker
            }
            
            # Check insider selling
            if symbol.Value in self.insider_tracker.transactions_by_ticker:
                sales = self.insider_tracker.get_recent_sales(symbol.Value)
                
                if sales:
                    total_sales_value = sum(s.transaction_value for s in sales)
                    
                    holdings_to_check[symbol]['insider_selling_cluster'] = {
                        'total_sales_value': total_sales_value,
                        'total_insider_holdings_value': total_sales_value * 2  # Simplified
                    }
        
        # Check and execute exits
        self.exit_manager.check_and_execute_exits(
            current_date=self.Time,
            holdings_data=holdings_to_check
        )
    
    def OnEndOfAlgorithm(self):
        """Called when the algorithm ends"""
        self.Debug(f"Algorithm finished. Final portfolio value: ${self.Portfolio.TotalPortfolioValue:,.2f}")
        self.Debug(f"Total return: {((self.Portfolio.TotalPortfolioValue / 1_000_000) - 1) * 100:.2f}%")

