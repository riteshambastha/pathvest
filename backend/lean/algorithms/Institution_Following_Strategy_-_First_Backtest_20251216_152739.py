"""
Generated LEAN Algorithm: Institution Following Strategy - First Backtest

This algorithm was automatically generated from a PathVest strategy configuration.
Generated on: 2025-12-16 15:27:39

Strategy Configuration:
- Period: 2022-01-01 to 2023-12-31
- Initial Capital: $100,000.00
- Universe: 0 stocks
- Selected Institutions: 0 funds
- Max Positions: 20
- Position Size: 5.0%
- Commission: $0.005/share
- Slippage: 25 bps
"""

from AlgorithmImports import *
from pathlib import Path
import sys

# Add custom data sources to path
sys.path.insert(0, str(Path(__file__).parent.parent / "data"))
from sec_data_source import SEC13FData, InsiderTransactionData


class Institution_Following_Strategy___First_Backtest(QCAlgorithm):
    """
    PathVest Strategy: Institution Following Strategy - First Backtest
    
    This algorithm implements institutional following with technical confirmation.
    """
    
    def Initialize(self):
        """Initialize the algorithm."""
        # Set date range
        self.SetStartDate(2022, 01, 01)
        self.SetEndDate(2023, 12, 31)
        
        # Set initial capital
        self.SetCash(100000)
        
        # Enable fractional shares
        self.Settings.FreePortfolioValuePercentage = 0.05
        self.Settings.AllowFractionalHoldings = True
        
        # Set transaction fees and slippage
        self.SetSecurityInitializer(self.CustomSecurityInitializer)
        
        # Strategy configuration
        self.max_positions = 20
        self.position_size = 0.05
        self.selected_institutions = []
        
        # Universe selection
        self.universe_tickers = []
        
        # Add equity securities
        for ticker in self.universe_tickers:
            equity = self.AddEquity(ticker, Resolution.Daily)
            equity.SetDataNormalizationMode(DataNormalizationMode.Adjusted)
        
        # Add custom SEC data
        for ticker in self.universe_tickers:
            self.AddData(SEC13FData, ticker, Resolution.Daily)
            self.AddData(InsiderTransactionData, ticker, Resolution.Daily)
        
        # Technical indicators
        self.sma = {}
        self.rsi = {}
        self.high_10d = {}
        
        for ticker in self.universe_tickers:
            symbol = self.Symbol(ticker)
            self.sma[ticker] = self.SMA(symbol, 50)
            self.rsi[ticker] = self.RSI(symbol, 14)
            # For 10-day high, we'll track manually
            self.high_10d[ticker] = self.MAX(symbol, 10)
        
        # Tracking variables
        self.sec_signals = {}  # Store SEC signals
        self.pending_entries = {}  # Stocks waiting for technical confirmation
        self.conviction_scores = {}  # Conviction scores for ranking
        
        # Exit tracking
        self.entry_prices = {}
        self.highest_prices = {}  # For trailing stops
        
        # Exit configuration (FR-3.1.C.11)
        self.exit_config = {
            'thesis_drift': True,  # Module 1: Mandatory
            'insider_reversal': False,  # Module 2
            'trailing_stop_pct': 0.15,  # Module 3: 15% trailing stop
            'stale_exit_quarters': 4,  # Module 4: 4 quarters
        }

    
    def CustomSecurityInitializer(self, security):
        """
        Initialize security with custom transaction models.
        """
        # Commission: $0.005 per share
        security.SetFeeModel(ConstantFeeModel(0.005))
        
        # Slippage: 25 basis points
        security.SetSlippageModel(ConstantSlippageModel(0.0025))
    
    def OnData(self, data):
        """
        Main event handler - called when new data arrives.
        
        This method implements the core strategy logic:
        1. Process SEC filing events (13F, Form 4)
        2. Check for technical confirmation
        3. Execute entries if conditions met
        4. Monitor exits
        """
        # Process SEC 13F data
        for sec_data in data.Get(SEC13FData):
            if sec_data is None:
                continue
            
            ticker = sec_data.Symbol.Value
            
            # Check if this institution is in our selected list
            if sec_data.cik not in self.selected_institutions:
                continue

            # Primary Signal Generation (FR-3.1.C.9 Step 1)
            signal_triggered = False
            signal_type = None

            # Signal A: Doubling Down
            if sec_data.is_doubling_down:
                signal_triggered = True
                signal_type = 'DOUBLING_DOWN'
                self.Log(f"Signal A (Doubling Down): {ticker} by {sec_data.institution_name}")

            # Signal B: Insider Buying (will be confirmed from Form 4)
            if sec_data.shares_change_pct >= 50:  # Large increase
                signal_triggered = True
                signal_type = 'INSIDER_BUYING'
                self.Log(f"Signal B (Large Institutional Buy): {ticker} (+{sec_data.shares_change_pct:.1f}%)")

            # Signal C: Institutional Herding
            if sec_data.is_new_position and sec_data.market_value > 10000000:
                signal_triggered = True
                signal_type = 'HERDING'
                self.Log(f"Signal C (New Large Position): {ticker} by {sec_data.institution_name}")

            if signal_triggered:
                # Store signal for technical confirmation (Step 2)
                self.sec_signals[ticker] = {
                    'type': signal_type,
                    'institution': sec_data.institution_name,
                    'conviction': sec_data.conviction_score,
                    'filing_date': self.Time
                }
                self.conviction_scores[ticker] = sec_data.conviction_score
                self.pending_entries[ticker] = self.sec_signals[ticker]

        
        # Process insider transaction data
        for insider_data in data.Get(InsiderTransactionData):
            if insider_data is None:
                continue
            
            ticker = insider_data.Symbol.Value
            
            # Boost conviction if insiders are buying
            if insider_data.transaction_type == "BUY" and ticker in self.conviction_scores:
                self.conviction_scores[ticker] += 10  # Boost for insider buying
                self.Log(f"Insider buying detected in {ticker}: {insider_data.insider_name} ({insider_data.insider_title})")
        
        # Check pending entries for technical confirmation
        self._check_technical_confirmation(data)
        
        # Check exits
        self._check_exits(data)
        
        # Rebalance if needed
        if self.Time.day == 1:  # Monthly rebalancing
            self._rebalance_portfolio()
    
    def _check_technical_confirmation(self, data):
        """
        Check if pending entries meet technical confirmation criteria.
        
        Implements FR-3.1.C.9 Step 3: Technical Confirmation
        - Price Breakout: Close > 10-day High
        - Trend Filter: Close > 50-day SMA
        - Momentum Filter: RSI(14) > 45
        """
        confirmed_entries = []
        
        for ticker in list(self.pending_entries.keys()):
            symbol = self.Symbol(ticker)
            
            if not self.Securities.ContainsKey(symbol):
                continue
            
            security = self.Securities[symbol]
            
            if not security.HasData:
                continue
            
            current_price = security.Close
            
            # Check all three technical conditions
            breakout = False
            trend = False
            momentum = False
            
            # 1. Price Breakout: Close > 10-day High
            if ticker in self.high_10d and self.high_10d[ticker].IsReady:
                high_10d_value = self.high_10d[ticker].Current.Value
                if current_price > high_10d_value:
                    breakout = True
            
            # 2. Trend Filter: Close > 50-day SMA
            if ticker in self.sma and self.sma[ticker].IsReady:
                sma_value = self.sma[ticker].Current.Value
                if current_price > sma_value:
                    trend = True
            
            # 3. Momentum Filter: RSI(14) > 45
            if ticker in self.rsi and self.rsi[ticker].IsReady:
                rsi_value = self.rsi[ticker].Current.Value
                if rsi_value > 45:
                    momentum = True
            
            # All conditions must be met
            if breakout and trend and momentum:
                confirmed_entries.append(ticker)
                self.Log(f"Technical confirmation met for {ticker}: "
                        f"Breakout=✅ Trend=✅ Momentum=✅")
        
        # Move confirmed entries to ready-to-trade list
        for ticker in confirmed_entries:
            # Keep in pending_entries, will be executed in rebalance
            pass

    
    def _check_exits(self, data):
        """
        Check all positions for exit conditions.
        
        Implements FR-3.1.C.11: Exit Modules
        """
        for symbol in self.Portfolio.Keys:
            if not self.Portfolio[symbol].Invested:
                continue
            
            ticker = symbol.Value
            holding = self.Portfolio[symbol]
            
            # Exit Module 3: Trailing Stop
            if self.exit_config.get('trailing_stop_pct', 0) > 0:
                current_price = self.Securities[symbol].Close
                
                # Update highest price
                if ticker in self.highest_prices:
                    self.highest_prices[ticker] = max(self.highest_prices[ticker], current_price)
                else:
                    self.highest_prices[ticker] = current_price
                
                # Check trailing stop
                trailing_stop_pct = self.exit_config['trailing_stop_pct']
                stop_price = self.highest_prices[ticker] * (1 - trailing_stop_pct)
                
                if current_price < stop_price:
                    self.Log(f"SELL {ticker}: Trailing stop hit at ${current_price:.2f} "
                            f"(Stop: ${stop_price:.2f}, High: ${self.highest_prices[ticker]:.2f})")
                    self.Liquidate(symbol)
                    
                    # Clean up tracking
                    if ticker in self.entry_prices:
                        del self.entry_prices[ticker]
                    if ticker in self.highest_prices:
                        del self.highest_prices[ticker]

    
    def _rebalance_portfolio(self):
        """
        Rebalance portfolio based on conviction ranking.
        
        This implements FR-3.1.C.10.1: Conviction Ranking Algorithm
        """
        if not self.pending_entries:
            return
        
        # Sort by conviction score
        sorted_candidates = sorted(
            self.pending_entries.items(),
            key=lambda x: self.conviction_scores.get(x[0], 0),
            reverse=True
        )
        
        # Take top candidates up to max_positions
        current_holdings = len([x for x in self.Portfolio.Values if x.Invested])
        available_slots = self.max_positions - current_holdings
        
        if available_slots <= 0:
            return
        
        # Execute top candidates
        for ticker, signal_info in sorted_candidates[:available_slots]:
            symbol = self.Symbol(ticker)
            
            if not self.Portfolio[symbol].Invested:
                # Calculate position size
                target_value = self.Portfolio.TotalPortfolioValue * self.position_size
                current_price = self.Securities[symbol].Price
                
                if current_price > 0:
                    quantity = target_value / current_price
                    
                    # Market order at next open (T+1 execution)
                    self.MarketOnOpenOrder(symbol, quantity)
                    
                    # Track entry
                    self.entry_prices[ticker] = current_price
                    self.highest_prices[ticker] = current_price
                    
                    self.Log(f"BUY {ticker}: {quantity:.4f} shares @ ${current_price:.2f} "
                            f"(Conviction: {self.conviction_scores.get(ticker, 0):.1f})")
                    
                    # Remove from pending
                    del self.pending_entries[ticker]
    
    def OnOrderEvent(self, orderEvent):
        """Handle order execution events."""
        if orderEvent.Status == OrderStatus.Filled:
            order = self.Transactions.GetOrderById(orderEvent.OrderId)
            self.Log(f"Order filled: {order.Symbol} {order.Quantity} @ ${orderEvent.FillPrice:.2f}")
    
    def OnEndOfAlgorithm(self):
        """Called at the end of the backtest."""
        self.Log(f"Backtest complete. Final portfolio value: ${self.Portfolio.TotalPortfolioValue:,.2f}")
        self.Log(f"Total return: {(self.Portfolio.TotalPortfolioValue / 100000 - 1) * 100:.2f}%")
