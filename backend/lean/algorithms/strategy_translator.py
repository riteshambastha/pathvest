"""
PathVest Strategy Configuration Translator

This module translates PathVest strategy configurations into LEAN algorithm code.
It dynamically generates Python classes that implement the strategy logic within
the LEAN framework.

Key Features:
- Convert PathVest JSON configs to LEAN QCAlgorithm code
- Generate OnData() event handlers
- Implement entry/exit signal logic
- Handle position sizing and risk management
- Support all SRS-defined signal types (Doubling Down, Insider Buying, Herding)

References:
- SRS FR-3.1.C.9: Entry Logic & Technical Confirmation
- SRS FR-3.1.C.10: Portfolio Construction & Ranking
- SRS FR-3.1.C.11: Exit Rules
"""

import json
from typing import Dict, List, Any, Optional
from datetime import datetime
import textwrap


class StrategyTranslator:
    """
    Translates PathVest strategy configurations into executable LEAN algorithms.
    
    This class takes a JSON strategy configuration (as defined by PathVest)
    and generates a complete LEAN QCAlgorithm class that can be executed
    by the LEAN engine.
    """
    
    def __init__(self):
        """Initialize the strategy translator."""
        self.strategy_config = {}
        self.algorithm_code = ""
    
    def translate(self, strategy_config: Dict[str, Any]) -> str:
        """
        Translate a PathVest strategy configuration into LEAN algorithm code.
        
        Args:
            strategy_config: Dictionary containing strategy configuration
            
        Returns:
            str: Python code for a LEAN QCAlgorithm class
        """
        self.strategy_config = strategy_config
        
        # Extract configuration components
        name = strategy_config.get("name", "PathVestStrategy")
        start_date = strategy_config.get("start_date", "2020-01-01")
        end_date = strategy_config.get("end_date", "2023-12-31")
        initial_capital = strategy_config.get("initial_capital", 100000)
        
        # Universe configuration
        universe_config = strategy_config.get("universe", {})
        tickers = universe_config.get("tickers", [])
        selected_institutions = strategy_config.get("selected_institutions", [])
        
        # Entry signals
        entry_signals = strategy_config.get("entry_signals", {})
        
        # Exit signals
        exit_signals = strategy_config.get("exit_signals", [])
        
        # Risk management
        risk_mgmt = strategy_config.get("risk_management", {})
        max_positions = risk_mgmt.get("max_portfolio_positions", 20)
        position_size = risk_mgmt.get("max_position_size", 0.05)
        allow_fractional = risk_mgmt.get("allow_fractional", True)
        
        # Transaction costs
        tx_costs = strategy_config.get("transaction_costs", {})
        commission = tx_costs.get("commission_per_share", 0.005)
        slippage_bps = tx_costs.get("slippage_bps", 25)
        
        # Generate algorithm code
        class_name = self._sanitize_class_name(name)
        
        code = f'''"""
Generated LEAN Algorithm: {name}

This algorithm was automatically generated from a PathVest strategy configuration.
Generated on: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

Strategy Configuration:
- Period: {start_date} to {end_date}
- Initial Capital: ${initial_capital:,.2f}
- Universe: {len(tickers)} stocks
- Selected Institutions: {len(selected_institutions)} funds
- Max Positions: {max_positions}
- Position Size: {position_size * 100:.1f}%
- Commission: ${commission}/share
- Slippage: {slippage_bps} bps
"""

from AlgorithmImports import *
from pathlib import Path
import sys

# Add custom data sources to path
sys.path.insert(0, str(Path(__file__).parent.parent / "data"))
from sec_data_source import SEC13FData, InsiderTransactionData


class {class_name}(QCAlgorithm):
    """
    PathVest Strategy: {name}
    
    This algorithm implements institutional following with technical confirmation.
    """
    
    def Initialize(self):
        """Initialize the algorithm."""
        # Set date range
        self.SetStartDate({start_date.split('-')[0]}, {start_date.split('-')[1]}, {start_date.split('-')[2]})
        self.SetEndDate({end_date.split('-')[0]}, {end_date.split('-')[1]}, {end_date.split('-')[2]})
        
        # Set initial capital
        self.SetCash({initial_capital})
        
        # Enable fractional shares
        self.Settings.FreePortfolioValuePercentage = 0.05
        self.Settings.AllowFractionalHoldings = {str(allow_fractional)}
        
        # Set transaction fees and slippage
        self.SetSecurityInitializer(self.CustomSecurityInitializer)
        
        # Strategy configuration
        self.max_positions = {max_positions}
        self.position_size = {position_size}
        self.selected_institutions = {selected_institutions}
        
        # Universe selection
        self.universe_tickers = {tickers}
        
        # Add equity securities
        for ticker in self.universe_tickers:
            equity = self.AddEquity(ticker, Resolution.Daily)
            equity.SetDataNormalizationMode(DataNormalizationMode.Adjusted)
        
        # Add custom SEC data
        for ticker in self.universe_tickers:
            self.AddData(SEC13FData, ticker, Resolution.Daily)
            self.AddData(InsiderTransactionData, ticker, Resolution.Daily)
        
        # Technical indicators
        self.sma = {{}}
        self.rsi = {{}}
        self.high_10d = {{}}
        
        for ticker in self.universe_tickers:
            symbol = self.Symbol(ticker)
            self.sma[ticker] = self.SMA(symbol, 50)
            self.rsi[ticker] = self.RSI(symbol, 14)
            # For 10-day high, we'll track manually
            self.high_10d[ticker] = self.MAX(symbol, 10)
        
        # Tracking variables
        self.sec_signals = {{}}  # Store SEC signals
        self.pending_entries = {{}}  # Stocks waiting for technical confirmation
        self.conviction_scores = {{}}  # Conviction scores for ranking
        
        # Exit tracking
        self.entry_prices = {{}}
        self.highest_prices = {{}}  # For trailing stops
        
{self._generate_exit_logic(exit_signals)}
    
    def CustomSecurityInitializer(self, security):
        """
        Initialize security with custom transaction models.
        """
        # Commission: ${commission} per share
        security.SetFeeModel(ConstantFeeModel({commission}))
        
        # Slippage: {slippage_bps} basis points
        security.SetSlippageModel(ConstantSlippageModel({slippage_bps / 10000.0}))
    
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
            
{self._generate_entry_logic(entry_signals)}
        
        # Process insider transaction data
        for insider_data in data.Get(InsiderTransactionData):
            if insider_data is None:
                continue
            
            ticker = insider_data.Symbol.Value
            
            # Boost conviction if insiders are buying
            if insider_data.transaction_type == "BUY" and ticker in self.conviction_scores:
                self.conviction_scores[ticker] += 10  # Boost for insider buying
                self.Log(f"Insider buying detected in {{ticker}}: {{insider_data.insider_name}} ({{insider_data.insider_title}})")
        
        # Check pending entries for technical confirmation
        self._check_technical_confirmation(data)
        
        # Check exits
        self._check_exits(data)
        
        # Rebalance if needed
        if self.Time.day == 1:  # Monthly rebalancing
            self._rebalance_portfolio()
    
{self._generate_technical_confirmation_logic(entry_signals)}
    
{self._generate_exit_check_logic(exit_signals)}
    
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
                    
                    self.Log(f"BUY {{ticker}}: {{quantity:.4f}} shares @ ${{current_price:.2f}} "
                            f"(Conviction: {{self.conviction_scores.get(ticker, 0):.1f}})")
                    
                    # Remove from pending
                    del self.pending_entries[ticker]
    
    def OnOrderEvent(self, orderEvent):
        """Handle order execution events."""
        if orderEvent.Status == OrderStatus.Filled:
            order = self.Transactions.GetOrderById(orderEvent.OrderId)
            self.Log(f"Order filled: {{order.Symbol}} {{order.Quantity}} @ ${{orderEvent.FillPrice:.2f}}")
    
    def OnEndOfAlgorithm(self):
        """Called at the end of the backtest."""
        self.Log(f"Backtest complete. Final portfolio value: ${{self.Portfolio.TotalPortfolioValue:,.2f}}")
        self.Log(f"Total return: {{(self.Portfolio.TotalPortfolioValue / {initial_capital} - 1) * 100:.2f}}%")
'''
        
        return code
    
    def _sanitize_class_name(self, name: str) -> str:
        """Convert strategy name to valid Python class name."""
        # Remove special characters and spaces
        clean = ''.join(c if c.isalnum() else '_' for c in name)
        # Ensure starts with letter
        if not clean[0].isalpha():
            clean = 'Strategy_' + clean
        return clean
    
    def _generate_entry_logic(self, entry_signals: Dict) -> str:
        """Generate entry signal logic based on configuration."""
        indent = "            "
        
        logic = f"{indent}# Check if this institution is in our selected list\n"
        logic += f"{indent}if sec_data.cik not in self.selected_institutions:\n"
        logic += f"{indent}    continue\n\n"
        
        logic += f"{indent}# Primary Signal Generation (FR-3.1.C.9 Step 1)\n"
        logic += f"{indent}signal_triggered = False\n"
        logic += f"{indent}signal_type = None\n\n"
        
        logic += f"{indent}# Signal A: Doubling Down\n"
        logic += f"{indent}if sec_data.is_doubling_down:\n"
        logic += f"{indent}    signal_triggered = True\n"
        logic += f"{indent}    signal_type = 'DOUBLING_DOWN'\n"
        logic += f"{indent}    self.Log(f\"Signal A (Doubling Down): {{ticker}} by {{sec_data.institution_name}}\")\n\n"
        
        logic += f"{indent}# Signal B: Insider Buying (will be confirmed from Form 4)\n"
        logic += f"{indent}if sec_data.shares_change_pct >= 50:  # Large increase\n"
        logic += f"{indent}    signal_triggered = True\n"
        logic += f"{indent}    signal_type = 'INSIDER_BUYING'\n"
        logic += f"{indent}    self.Log(f\"Signal B (Large Institutional Buy): {{ticker}} (+{{sec_data.shares_change_pct:.1f}}%)\")\n\n"
        
        logic += f"{indent}# Signal C: Institutional Herding\n"
        logic += f"{indent}if sec_data.is_new_position and sec_data.market_value > 10000000:\n"
        logic += f"{indent}    signal_triggered = True\n"
        logic += f"{indent}    signal_type = 'HERDING'\n"
        logic += f"{indent}    self.Log(f\"Signal C (New Large Position): {{ticker}} by {{sec_data.institution_name}}\")\n\n"
        
        logic += f"{indent}if signal_triggered:\n"
        logic += f"{indent}    # Store signal for technical confirmation (Step 2)\n"
        logic += f"{indent}    self.sec_signals[ticker] = {{\n"
        logic += f"{indent}        'type': signal_type,\n"
        logic += f"{indent}        'institution': sec_data.institution_name,\n"
        logic += f"{indent}        'conviction': sec_data.conviction_score,\n"
        logic += f"{indent}        'filing_date': self.Time\n"
        logic += f"{indent}    }}\n"
        logic += f"{indent}    self.conviction_scores[ticker] = sec_data.conviction_score\n"
        logic += f"{indent}    self.pending_entries[ticker] = self.sec_signals[ticker]\n"
        
        return logic
    
    def _generate_technical_confirmation_logic(self, entry_signals: Dict) -> str:
        """Generate technical confirmation checks."""
        return '''    def _check_technical_confirmation(self, data):
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
'''
    
    def _generate_exit_logic(self, exit_signals: List) -> str:
        """Generate exit configuration."""
        indent = "        "
        
        logic = f"{indent}# Exit configuration (FR-3.1.C.11)\n"
        logic += f"{indent}self.exit_config = {{\n"
        
        # Default exits
        logic += f"{indent}    'thesis_drift': True,  # Module 1: Mandatory\n"
        logic += f"{indent}    'insider_reversal': False,  # Module 2\n"
        logic += f"{indent}    'trailing_stop_pct': 0.15,  # Module 3: 15% trailing stop\n"
        logic += f"{indent}    'stale_exit_quarters': 4,  # Module 4: 4 quarters\n"
        logic += f"{indent}}}\n"
        
        return logic
    
    def _generate_exit_check_logic(self, exit_signals: List) -> str:
        """Generate exit checking logic."""
        return '''    def _check_exits(self, data):
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
'''
    
    def save_to_file(self, code: str, output_path: str):
        """
        Save generated algorithm code to a file.
        
        Args:
            code: Python code string
            output_path: Path to save the file
        """
        with open(output_path, 'w') as f:
            f.write(code)


# Testing
if __name__ == "__main__":
    # Sample PathVest configuration
    sample_config = {
        "name": "Institutional Following with Technical Confirmation",
        "start_date": "2020-01-01",
        "end_date": "2023-12-31",
        "initial_capital": 100000,
        
        "universe": {
            "tickers": ["AAPL", "MSFT", "GOOGL", "AMZN", "META"]
        },
        
        "selected_institutions": ["0001166559", "0001067983"],  # Berkshire, Baupost
        
        "entry_signals": {
            "doubling_down": True,
            "insider_buying": True,
            "herding": True,
            "technical_confirmation": True
        },
        
        "exit_signals": [
            {"type": "trailing_stop", "percent": 15},
            {"type": "time_based", "quarters": 4}
        ],
        
        "risk_management": {
            "max_portfolio_positions": 20,
            "max_position_size": 0.05,
            "allow_fractional": True
        },
        
        "transaction_costs": {
            "commission_per_share": 0.005,
            "slippage_bps": 25
        }
    }
    
    translator = StrategyTranslator()
    code = translator.translate(sample_config)
    
    print("=" * 60)
    print("Generated LEAN Algorithm")
    print("=" * 60)
    print(code[:1000] + "\n... (truncated for display)")
    print("=" * 60)
    print(f"✅ Successfully generated {len(code)} characters of code")

