"""
PathVest Strategy - Generated Algorithm for LEAN
Generated: 2025-12-16T19:47:44.570931
"""

from AlgorithmImports import *
import json

class PathVestStrategy(QCAlgorithm):
    """
    PathVest institutional following strategy
    Trades based on SEC 13F filing signals
    """
    
    def Initialize(self):
        """Initialize algorithm"""
        # Set dates and capital
        self.SetStartDate(2024, 01, 01)
        self.SetEndDate(2024, 12, 31)
        self.SetCash(100000)
        
        # Enable fractional shares
        self.Settings.FreePortfolioValuePercentage = 0.05
        
        # Set transaction models
        self.SetBrokerageModel(BrokerageName.InteractiveBrokersBrokerage, AccountType.Margin)
        
        # Add securities
        self.tickers = ['AAPL', 'MSFT']
        self.symbols = {}
        for ticker in self.tickers:
            symbol = self.AddEquity(ticker, Resolution.Daily)
            symbol.FeeModel = ConstantFeeModel(0)  # Zero commission
            symbol.SlippageModel = ConstantSlippageModel(0.001)  # 0.1% slippage
            self.symbols[ticker] = symbol.Symbol
        
        # Load signals from JSON
        self.signals = [
        {
                "date": "2024-01-15",
                "ticker": "AAPL",
                "action": "BUY",
                "signal_strength": 1.0
        },
        {
                "date": "2024-03-10",
                "ticker": "MSFT",
                "action": "BUY",
                "signal_strength": 0.8
        },
        {
                "date": "2024-06-15",
                "ticker": "AAPL",
                "action": "SELL",
                "signal_strength": 1.0
        }
]
        
        # Convert signal dates to datetime
        self.signals_by_date = {}
        for signal in self.signals:
            date_str = signal['date']
            if date_str not in self.signals_by_date:
                self.signals_by_date[date_str] = []
            self.signals_by_date[date_str].append(signal)
        
        self.Debug(f"Loaded {len(self.signals)} signals for {len(self.tickers)} tickers")
    
    def OnData(self, data):
        """Main event handler called on each bar"""
        current_date = self.Time.strftime('%Y-%m-%d')
        
        # Check for signals on this date
        if current_date not in self.signals_by_date:
            return
        
        signals_today = self.signals_by_date[current_date]
        self.Debug(f"Processing {len(signals_today)} signals on {current_date}")
        
        for signal in signals_today:
            ticker = signal['ticker']
            action = signal['action']
            signal_strength = signal.get('signal_strength', 1.0)
            
            if ticker not in self.symbols:
                continue
            
            symbol = self.symbols[ticker]
            
            # Skip if no data for this symbol
            if not data.ContainsKey(symbol):
                self.Debug(f"No data for {ticker} on {current_date}")
                continue
            
            if action == 'BUY':
                # Calculate position size (max 20% of portfolio)
                max_position_value = self.Portfolio.TotalPortfolioValue * 0.20 * signal_strength
                current_price = data[symbol].Close
                
                if current_price > 0:
                    shares_to_buy = int(max_position_value / current_price)
                    
                    if shares_to_buy > 0 and self.Portfolio.Cash > shares_to_buy * current_price:
                        self.MarketOrder(symbol, shares_to_buy)
                        self.Debug(f"BUY {shares_to_buy} {ticker} @ ${current_price:.2f}")
            
            elif action == 'SELL':
                # Sell entire position
                if self.Portfolio[symbol].Invested:
                    shares_to_sell = self.Portfolio[symbol].Quantity
                    self.MarketOrder(symbol, -shares_to_sell)
                    current_price = data[symbol].Close
                    self.Debug(f"SELL {shares_to_sell} {ticker} @ ${current_price:.2f}")
    
    def OnEndOfAlgorithm(self):
        """Called at end of backtest"""
        self.Debug(f"Final Portfolio Value: ${self.Portfolio.TotalPortfolioValue:.2f}")
        self.Debug(f"Total Return: {(self.Portfolio.TotalPortfolioValue / 100000 - 1) * 100:.2f}%")
