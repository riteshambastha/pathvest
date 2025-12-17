"""
PathVest Base Strategy for LEAN Engine
Provides foundation for all PathVest trading strategies
"""
from AlgorithmImports import *


class PathVestBaseStrategy(QCAlgorithm):
    """
    Base class for PathVest strategies in LEAN
    
    Implements:
    - Fractional share support
    - Transaction costs (commission + slippage)
    - Daily resolution
    - Event-driven architecture
    
    Subclasses should override:
    - Initialize() - Add strategy-specific setup
    - OnData() - Implement trading logic
    """
    
    def Initialize(self):
        """
        Initialize the algorithm
        Override this in subclasses but call super().Initialize() first
        """
        # Default dates (will be overridden by config)
        self.SetStartDate(2013, 1, 1)
        self.SetEndDate(2023, 12, 31)
        
        # Default cash
        self.SetCash(100000)
        
        # Enable fractional shares (PathVest requirement FR-3.1.D.4)
        self.Settings.FreePortfolioValuePercentage = 0.05
        self.Settings.MinimumOrderMarginPortfolioPercentage = 0
        
        # Data resolution
        self.UniverseSettings.Resolution = Resolution.Daily
        
        # Set brokerage model for realistic fills
        self.SetBrokerageModel(BrokerageName.InteractiveBrokersBrokerage, AccountType.Margin)
        
        # Initialize securities with custom models
        self.SetSecurityInitializer(self.security_initializer)
        
        # Portfolio tracking
        self.positions = {}
        self.signals = {}
        self.entry_prices = {}
        
        # Risk management
        self.max_positions = 20  # FR-3.1.C.4
        self.position_size_pct = 0.05  # 5% per position
        self.min_positions = 5  # FR-3.1.C.10.3
        
        self.Debug("PathVest Base Strategy Initialized")
    
    def security_initializer(self, security):
        """
        Configure slippage and transaction costs
        Per SRS FR-3.1.C.7
        """
        # Slippage: 25 bps (0.0025 or 0.25%)
        security.SetSlippageModel(ConstantSlippageModel(0.0025))
        
        # Commission: $0.005 per share
        security.SetFeeModel(ConstantFeeModel(0.005))
        
        # Set data normalization
        security.SetDataNormalizationMode(DataNormalizationMode.Adjusted)
    
    def OnData(self, data):
        """
        Event handler for new market data
        Override this in strategy implementations
        """
        pass
    
    def enter_position(self, symbol, signal_type, conviction_score=50):
        """
        Enter a new position
        
        Args:
            symbol: Stock symbol
            signal_type: Type of entry signal (e.g., 'doubling_down', 'insider_buying')
            conviction_score: Conviction score 0-100
        """
        # Check if already in position
        if self.Portfolio[symbol].Invested:
            self.Debug(f"Already invested in {symbol}")
            return
        
        # Check position limits
        if len(self.positions) >= self.max_positions:
            self.Debug(f"Maximum positions ({self.max_positions}) reached")
            return
        
        # Calculate position size (5% of portfolio)
        quantity = self.CalculateOrderQuantity(symbol, self.position_size_pct)
        
        if quantity == 0:
            self.Debug(f"Calculated quantity is 0 for {symbol}")
            return
        
        # Place market order
        ticket = self.MarketOrder(symbol, quantity)
        
        if ticket.Status == OrderStatus.Filled:
            self.positions[symbol] = {
                'entry_date': self.Time,
                'entry_price': ticket.AverageFillPrice,
                'quantity': quantity,
                'signal_type': signal_type,
                'conviction_score': conviction_score
            }
            
            self.Debug(f"ENTRY: {symbol} | {quantity} shares @ ${ticket.AverageFillPrice:.2f} | Signal: {signal_type}")
    
    def exit_position(self, symbol, exit_reason='unknown'):
        """
        Exit an existing position
        
        Args:
            symbol: Stock symbol
            exit_reason: Reason for exit (e.g., 'thesis_drift', 'stop_loss')
        """
        if not self.Portfolio[symbol].Invested:
            self.Debug(f"Not invested in {symbol}")
            return
        
        # Get current holding
        holding = self.Portfolio[symbol]
        
        # Close entire position
        ticket = self.Liquidate(symbol)
        
        if ticket.Status == OrderStatus.Filled:
            position_info = self.positions.get(symbol, {})
            entry_price = position_info.get('entry_price', 0)
            pnl_pct = ((ticket.AverageFillPrice - entry_price) / entry_price * 100) if entry_price > 0 else 0
            
            self.Debug(f"EXIT: {symbol} | {holding.Quantity} shares @ ${ticket.AverageFillPrice:.2f} | P&L: {pnl_pct:.2f}% | Reason: {exit_reason}")
            
            # Remove from positions tracking
            if symbol in self.positions:
                del self.positions[symbol]
    
    def get_portfolio_value(self):
        """Get current portfolio value"""
        return self.Portfolio.TotalPortfolioValue
    
    def get_cash(self):
        """Get current cash balance"""
        return self.Portfolio.Cash
    
    def get_holdings_value(self):
        """Get total value of holdings"""
        return self.Portfolio.TotalHoldingsValue
    
    def get_invested_count(self):
        """Get number of current positions"""
        return len([s for s in self.Securities.Values if s.Invested])
    
    def should_enter_new_position(self):
        """
        Check if we should enter new positions
        Implements FR-3.1.C.10.3: Cash Drag Management
        """
        current_positions = self.get_invested_count()
        
        # Must have at least min_positions to trade
        if current_positions < self.min_positions:
            return True
        
        # Can add up to max_positions
        if current_positions < self.max_positions:
            return True
        
        return False
    
    def OnOrderEvent(self, orderEvent):
        """
        Event handler for order status changes
        """
        if orderEvent.Status == OrderStatus.Filled:
            order = self.Transactions.GetOrderById(orderEvent.OrderId)
            self.Debug(f"Order Filled: {order.Symbol} | {order.Quantity} @ ${orderEvent.FillPrice:.2f}")
    
    def OnEndOfDay(self, symbol):
        """
        Event handler for end of day
        Good place for daily checks (stops, take profits, etc.)
        """
        pass
    
    def OnEndOfAlgorithm(self):
        """
        Event handler when backtest completes
        """
        self.Debug(f"Backtest Complete")
        self.Debug(f"Final Portfolio Value: ${self.Portfolio.TotalPortfolioValue:,.2f}")
        self.Debug(f"Total Return: {((self.Portfolio.TotalPortfolioValue / self.StartingCash) - 1) * 100:.2f}%")

