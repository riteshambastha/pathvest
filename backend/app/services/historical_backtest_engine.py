"""
Real Historical Backtesting Engine
Uses actual historical price data and SEC filing dates to simulate portfolio performance
"""

import httpx
import os
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Tuple
import asyncio

BASE_URL = "https://www.alphavantage.co/query"


class HistoricalBacktestEngine:
    """
    Real backtesting engine that simulates portfolio performance using:
    - Historical stock prices
    - SEC filing dates as signals
    - Realistic transaction costs
    - Proper position sizing
    - Exit signals (stop-loss, take-profit, trailing stop)
    - Rebalancing rules (never, weekly, monthly, quarterly, threshold-based)
    """
    
    # Default exit parameters
    DEFAULT_STOP_LOSS_PCT = 0.10      # 10% stop loss
    DEFAULT_TAKE_PROFIT_PCT = 0.30    # 30% take profit
    DEFAULT_TRAILING_STOP_PCT = 0.15  # 15% trailing stop from peak
    
    # Default rebalancing parameters
    DEFAULT_REBALANCE_FREQUENCY = 'monthly'  # never, weekly, monthly, quarterly, threshold
    DEFAULT_DRIFT_THRESHOLD = 0.05  # 5% drift triggers threshold-based rebalancing
    DEFAULT_TARGET_WEIGHT = 0.05    # 5% per position (static sizing per SRS)
    DEFAULT_MIN_POSITIONS = 5       # Minimum positions before 100% cash
    DEFAULT_MAX_POSITIONS = 20      # Maximum positions
    
    def __init__(self, initial_capital: float = 100000, exit_config: Dict = None, rebalance_config: Dict = None):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions = {}  # {ticker: shares}
        self.position_details = {}  # {ticker: {entry_date, entry_price, peak_price, shares}}
        self.portfolio_history = []
        self.trades = []
        # Load API key dynamically (not at module level)
        self.api_key = os.getenv("ALPHAVANTAGE_API_KEY", "")
        
        # Exit configuration
        self.exit_config = exit_config or {}
        self.stop_loss_pct = self.exit_config.get('stop_loss_pct', self.DEFAULT_STOP_LOSS_PCT)
        self.take_profit_pct = self.exit_config.get('take_profit_pct', self.DEFAULT_TAKE_PROFIT_PCT)
        self.trailing_stop_pct = self.exit_config.get('trailing_stop_pct', self.DEFAULT_TRAILING_STOP_PCT)
        self.enable_stop_loss = self.exit_config.get('enable_stop_loss', True)
        self.enable_take_profit = self.exit_config.get('enable_take_profit', True)
        self.enable_trailing_stop = self.exit_config.get('enable_trailing_stop', True)
        
        # Rebalancing configuration
        self.rebalance_config = rebalance_config or {}
        self.rebalance_frequency = self.rebalance_config.get('frequency', self.DEFAULT_REBALANCE_FREQUENCY)
        self.drift_threshold = self.rebalance_config.get('drift_threshold', self.DEFAULT_DRIFT_THRESHOLD)
        self.target_weight = self.rebalance_config.get('target_weight', self.DEFAULT_TARGET_WEIGHT)
        self.min_positions = self.rebalance_config.get('min_positions', self.DEFAULT_MIN_POSITIONS)
        self.max_positions = self.rebalance_config.get('max_positions', self.DEFAULT_MAX_POSITIONS)
        self.last_rebalance_date = None
        self.rebalance_count = 0
        
    async def fetch_historical_prices(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Fetch historical daily prices from AlphaVantage
        Returns DataFrame with Date, Open, High, Low, Close, Volume
        """
        print(f"📈 Fetching historical prices for {symbol}...")
        
        # Use TIME_SERIES_DAILY for historical data
        # Note: 'compact' returns last 100 data points (free tier)
        # 'full' requires premium subscription
        params = {
            'function': 'TIME_SERIES_DAILY',
            'symbol': symbol,
            'outputsize': 'compact',  # Free tier: last 100 data points
            'apikey': self.api_key
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(BASE_URL, params=params)
                data = response.json()

                # Debug: Log the response keys and status
                print(f"🔍 API Response for {symbol}: Status {response.status_code}, Keys: {list(data.keys())[:3]}...")
                
                if 'Time Series (Daily)' not in data:
                    error_msg = data.get('Note', data.get('Error Message', 'Unknown error'))
                    print(f"⚠️  No data for {symbol}: {error_msg}")
                    # Debug: Show full response for troubleshooting
                    if len(str(data)) < 500:
                        print(f"🔍 Full API response: {data}")
                    return pd.DataFrame()
                
                # Convert to DataFrame
                time_series = data['Time Series (Daily)']
                df = pd.DataFrame.from_dict(time_series, orient='index')
                df.index = pd.to_datetime(df.index)
                df = df.sort_index()
                
                # Rename columns
                df.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
                df = df.astype(float)
                
                total_days = len(df)
                print(f"🔍 {symbol}: Raw data has {total_days} days ({df.index.min()} to {df.index.max()})")
                
                # Try to filter by date range
                filtered_df = df[(df.index >= start_date) & (df.index <= end_date)]
                
                if len(filtered_df) > 0:
                    print(f"✅ Got {len(filtered_df)} days of historical data for {symbol} (filtered)")
                    return filtered_df
                else:
                    # If no data in range, use all available data (better than nothing)
                    # This happens when backtest period doesn't overlap with available data
                    print(f"⚠️ {symbol}: No data in range {start_date} to {end_date}, using all {total_days} days")
                    return df
                
        except Exception as e:
            print(f"❌ Error fetching {symbol}: {e}")
            return pd.DataFrame()
    
    def calculate_position_size(self, ticker: str, signal_strength: float = 1.0) -> int:
        """
        Calculate number of shares to buy based on available cash and position sizing rules
        - Max 20% of portfolio per position (concentrated)
        - Adjusted by signal strength (0-1)
        """
        max_position_value = self.initial_capital * 0.20 * signal_strength
        available_cash = min(self.cash, max_position_value)
        
        return int(available_cash)  # We'll divide by price when buying
    
    def execute_trade(self, date: datetime, ticker: str, shares: int, price: float, action: str):
        """
        Execute a buy or sell order
        """
        commission = 0  # Zero commission (modern brokers)
        slippage = 0.001  # 0.1% slippage
        
        if action == 'BUY':
            # Apply slippage (pay slightly more)
            execution_price = price * (1 + slippage)
            cost = shares * execution_price + commission
            
            if cost <= self.cash:
                self.cash -= cost
                self.positions[ticker] = self.positions.get(ticker, 0) + shares
                
                # Track position details for exit signals
                if ticker not in self.position_details:
                    self.position_details[ticker] = {
                        'entry_date': date,
                        'entry_price': execution_price,
                        'peak_price': execution_price,
                        'shares': shares
                    }
                else:
                    # Average up/down - update average entry price
                    old_shares = self.position_details[ticker]['shares']
                    old_cost = old_shares * self.position_details[ticker]['entry_price']
                    new_total_shares = old_shares + shares
                    new_avg_price = (old_cost + cost) / new_total_shares
                    self.position_details[ticker]['entry_price'] = new_avg_price
                    self.position_details[ticker]['shares'] = new_total_shares
                
                self.trades.append({
                    'date': date,
                    'ticker': ticker,
                    'action': 'BUY',
                    'shares': shares,
                    'price': execution_price,
                    'cost': cost,
                    'cash_after': self.cash,
                    'entry_price': execution_price
                })
                print(f"  📈 BUY  {shares:,} {ticker} @ ${execution_price:.2f} = ${cost:,.2f}")
                return True
            else:
                print(f"  ⚠️  Insufficient cash to buy {ticker}")
                return False
                
        elif action == 'SELL':
            if ticker in self.positions and self.positions[ticker] >= shares:
                # Apply slippage (receive slightly less)
                execution_price = price * (1 - slippage)
                proceeds = shares * execution_price - commission
                
                self.cash += proceeds
                self.positions[ticker] -= shares
                
                if self.positions[ticker] == 0:
                    del self.positions[ticker]
                
                self.trades.append({
                    'date': date,
                    'ticker': ticker,
                    'action': 'SELL',
                    'shares': shares,
                    'price': execution_price,
                    'proceeds': proceeds,
                    'cash_after': self.cash
                })
                print(f"  📉 SELL {shares:,} {ticker} @ ${execution_price:.2f} = ${proceeds:,.2f}")
                return True
            else:
                print(f"  ⚠️  No position in {ticker} to sell")
                return False
    
    def calculate_portfolio_value(self, date: datetime, prices: Dict[str, float]) -> float:
        """
        Calculate total portfolio value (cash + positions)
        """
        positions_value = sum(
            self.positions.get(ticker, 0) * prices.get(ticker, 0)
            for ticker in self.positions.keys()
        )
        return self.cash + positions_value
    
    def check_exit_signals(self, date: datetime, current_prices: Dict[str, float]) -> List[Dict]:
        """
        Check all open positions for exit signals (stop-loss, take-profit, trailing stop)
        
        Returns:
            List of exit signal dicts with keys: ticker, reason, exit_type
        """
        exit_signals = []
        
        for ticker, details in list(self.position_details.items()):
            if ticker not in current_prices:
                continue
                
            current_price = current_prices[ticker]
            entry_price = details['entry_price']
            peak_price = details.get('peak_price', entry_price)
            
            # Update peak price
            if current_price > peak_price:
                self.position_details[ticker]['peak_price'] = current_price
                peak_price = current_price
            
            # Calculate returns
            return_from_entry = (current_price - entry_price) / entry_price
            drawdown_from_peak = (peak_price - current_price) / peak_price if peak_price > 0 else 0
            
            exit_signal = None
            
            # Check STOP-LOSS (fixed % from entry)
            if self.enable_stop_loss and return_from_entry <= -self.stop_loss_pct:
                exit_signal = {
                    'ticker': ticker,
                    'reason': f'Stop-loss triggered: {return_from_entry*100:.1f}% loss',
                    'exit_type': 'stop_loss',
                    'return_pct': return_from_entry,
                    'confidence': 90.0
                }
            
            # Check TAKE-PROFIT (fixed % from entry)
            elif self.enable_take_profit and return_from_entry >= self.take_profit_pct:
                exit_signal = {
                    'ticker': ticker,
                    'reason': f'Take-profit triggered: +{return_from_entry*100:.1f}% gain',
                    'exit_type': 'take_profit',
                    'return_pct': return_from_entry,
                    'confidence': 95.0
                }
            
            # Check TRAILING STOP (% from peak)
            elif self.enable_trailing_stop and drawdown_from_peak >= self.trailing_stop_pct:
                exit_signal = {
                    'ticker': ticker,
                    'reason': f'Trailing stop: {drawdown_from_peak*100:.1f}% from peak ${peak_price:.2f}',
                    'exit_type': 'trailing_stop',
                    'return_pct': return_from_entry,
                    'confidence': 85.0
                }
            
            if exit_signal:
                exit_signals.append(exit_signal)
        
        return exit_signals
    
    def execute_exit(self, date: datetime, ticker: str, price: float, reason: str, exit_type: str) -> bool:
        """
        Execute an exit trade (sell entire position)
        """
        if ticker not in self.positions or self.positions[ticker] <= 0:
            return False
        
        shares = self.positions[ticker]
        details = self.position_details.get(ticker, {})
        entry_price = details.get('entry_price', price)
        
        # Apply slippage
        slippage = 0.001
        execution_price = price * (1 - slippage)
        proceeds = shares * execution_price
        
        # Update cash
        self.cash += proceeds
        
        # Calculate P&L
        cost_basis = shares * entry_price
        pnl = proceeds - cost_basis
        return_pct = (execution_price - entry_price) / entry_price if entry_price > 0 else 0
        
        # Record trade
        self.trades.append({
            'date': date,
            'ticker': ticker,
            'action': 'SELL',
            'shares': shares,
            'price': execution_price,
            'proceeds': proceeds,
            'cash_after': self.cash,
            'exit_reason': reason,
            'exit_type': exit_type,
            'entry_price': entry_price,
            'pnl': pnl,
            'return_pct': return_pct
        })
        
        # Log the exit
        emoji = '🎯' if exit_type == 'take_profit' else '🛑' if exit_type == 'stop_loss' else '📉'
        print(f"  {emoji} EXIT {shares:,} {ticker} @ ${execution_price:.2f} | {reason} | P&L: ${pnl:+,.2f} ({return_pct*100:+.1f}%)")
        
        # Remove position
        del self.positions[ticker]
        del self.position_details[ticker]
        
        return True
    
    # ==================== REBALANCING METHODS ====================
    
    def should_rebalance(self, current_date: datetime, current_prices: Dict[str, float]) -> bool:
        """
        Determine if rebalancing should occur based on configured frequency.
        
        Supported frequencies:
        - 'never': No rebalancing (buy and hold)
        - 'weekly': Rebalance every Monday
        - 'monthly': Rebalance on first trading day of each month
        - 'quarterly': Rebalance on first trading day of each quarter
        - 'threshold': Rebalance when any position drifts > threshold from target
        
        Returns:
            True if rebalancing should occur
        """
        if self.rebalance_frequency == 'never':
            return False
        
        # For first day, set last_rebalance_date
        if self.last_rebalance_date is None:
            self.last_rebalance_date = current_date
            return False
        
        if self.rebalance_frequency == 'weekly':
            # Rebalance every Monday (weekday 0)
            return current_date.weekday() == 0 and (current_date - self.last_rebalance_date).days >= 5
        
        elif self.rebalance_frequency == 'monthly':
            # Rebalance on first trading day of new month
            return current_date.month != self.last_rebalance_date.month or current_date.year != self.last_rebalance_date.year
        
        elif self.rebalance_frequency == 'quarterly':
            # Rebalance on first trading day of new quarter
            current_quarter = (current_date.month - 1) // 3
            last_quarter = (self.last_rebalance_date.month - 1) // 3
            return (current_quarter != last_quarter) or (current_date.year != self.last_rebalance_date.year)
        
        elif self.rebalance_frequency == 'threshold':
            # Check if any position has drifted beyond threshold
            return self.check_drift_threshold(current_prices)
        
        return False
    
    def check_drift_threshold(self, current_prices: Dict[str, float]) -> bool:
        """
        Check if any position has drifted beyond the configured threshold.
        
        Returns:
            True if any position weight differs from target by > drift_threshold
        """
        if not self.positions:
            return False
        
        # Calculate total portfolio value
        portfolio_value = self.calculate_portfolio_value(datetime.now(), current_prices)
        if portfolio_value <= 0:
            return False
        
        # Check each position's weight
        for ticker, shares in self.positions.items():
            if ticker in current_prices and current_prices[ticker] > 0:
                position_value = shares * current_prices[ticker]
                current_weight = position_value / portfolio_value
                drift = abs(current_weight - self.target_weight)
                
                if drift > self.drift_threshold:
                    print(f"⚖️ Drift detected: {ticker} at {current_weight*100:.1f}% (target: {self.target_weight*100:.0f}%, drift: {drift*100:.1f}%)")
                    return True
        
        return False
    
    def calculate_target_allocation(self, current_prices: Dict[str, float]) -> Dict[str, float]:
        """
        Calculate the target allocation (equal weight for all positions).
        
        Returns:
            Dict of ticker -> target_shares
        """
        if not self.positions:
            return {}
        
        # Calculate total portfolio value
        portfolio_value = self.calculate_portfolio_value(datetime.now(), current_prices)
        
        # Equal weight to all current positions
        num_positions = len(self.positions)
        if num_positions == 0:
            return {}
        
        # Cap positions at max, ensure min
        if num_positions < self.min_positions:
            print(f"⚠️ Only {num_positions} positions (min: {self.min_positions}) - staying fully invested")
        
        # Target weight is either equal-weight or fixed 5%
        target_weight_per_position = min(self.target_weight, 1.0 / num_positions)
        target_value_per_position = portfolio_value * target_weight_per_position
        
        target_allocation = {}
        for ticker in self.positions.keys():
            if ticker in current_prices and current_prices[ticker] > 0:
                target_shares = target_value_per_position / current_prices[ticker]
                target_allocation[ticker] = target_shares
        
        return target_allocation
    
    def execute_rebalancing(self, date: datetime, current_prices: Dict[str, float]) -> List[Dict]:
        """
        Execute rebalancing trades to restore target allocation.
        
        Returns:
            List of rebalancing trades executed
        """
        rebalance_trades = []
        
        if not self.positions:
            print("⚖️ No positions to rebalance")
            return rebalance_trades
        
        # Calculate target allocation
        target_allocation = self.calculate_target_allocation(current_prices)
        
        if not target_allocation:
            return rebalance_trades
        
        print(f"\n⚖️ REBALANCING on {date.strftime('%Y-%m-%d')}")
        print(f"   Portfolio positions: {len(self.positions)}")
        
        # Calculate trades needed
        for ticker, target_shares in target_allocation.items():
            current_shares = self.positions.get(ticker, 0)
            share_diff = target_shares - current_shares
            
            # Apply minimum trade threshold (avoid tiny trades)
            min_trade_value = 100  # $100 minimum trade
            if ticker in current_prices:
                trade_value = abs(share_diff * current_prices[ticker])
                if trade_value < min_trade_value:
                    continue
            
            if share_diff > 0:
                # Need to BUY more
                price = current_prices.get(ticker, 0)
                if price > 0:
                    additional_shares = int(share_diff)
                    if additional_shares > 0:
                        cost = additional_shares * price
                        if cost <= self.cash:
                            self.execute_trade(date, ticker, additional_shares, price, 'BUY')
                            rebalance_trades.append({
                                'ticker': ticker,
                                'action': 'BUY',
                                'shares': additional_shares,
                                'price': price,
                                'reason': 'Rebalance - increase position'
                            })
            
            elif share_diff < 0:
                # Need to SELL some
                price = current_prices.get(ticker, 0)
                if price > 0:
                    sell_shares = int(abs(share_diff))
                    if sell_shares > 0 and sell_shares <= current_shares:
                        self.execute_trade(date, ticker, sell_shares, price, 'SELL')
                        rebalance_trades.append({
                            'ticker': ticker,
                            'action': 'SELL',
                            'shares': sell_shares,
                            'price': price,
                            'reason': 'Rebalance - reduce position'
                        })
        
        # Update last rebalance date
        self.last_rebalance_date = date
        self.rebalance_count += 1
        
        if rebalance_trades:
            print(f"   Executed {len(rebalance_trades)} rebalancing trades")
        else:
            print(f"   No rebalancing needed (positions within tolerance)")
        
        return rebalance_trades
    
    # ==================== END REBALANCING METHODS ====================
    
    def run_backtest(
        self,
        signals: List[Dict],  # [{date, ticker, action, signal_strength}, ...]
        historical_prices: Dict[str, pd.DataFrame],  # {ticker: DataFrame}
        start_date: str,
        end_date: str,
        exit_config: Dict = None
    ) -> Dict:
        """
        Run the backtest simulation with exit signals
        
        Args:
            signals: List of trading signals with dates
            historical_prices: Dict of ticker -> price DataFrames
            start_date: Backtest start date
            end_date: Backtest end date
            exit_config: Optional exit configuration override
            
        Returns:
            Dict with performance metrics
        """
        # Update exit config if provided
        if exit_config:
            self.stop_loss_pct = exit_config.get('stop_loss_pct', self.stop_loss_pct)
            self.take_profit_pct = exit_config.get('take_profit_pct', self.take_profit_pct)
            self.trailing_stop_pct = exit_config.get('trailing_stop_pct', self.trailing_stop_pct)
            self.enable_stop_loss = exit_config.get('enable_stop_loss', self.enable_stop_loss)
            self.enable_take_profit = exit_config.get('enable_take_profit', self.enable_take_profit)
            self.enable_trailing_stop = exit_config.get('enable_trailing_stop', self.enable_trailing_stop)
        
        print(f"\n🎯 Running backtest: {start_date} to {end_date}")
        print(f"💰 Initial capital: ${self.initial_capital:,.2f}")
        print(f"📊 Entry signals: {len(signals)}")
        print(f"🛑 Exit Rules: Stop-Loss={self.stop_loss_pct*100:.0f}% | Take-Profit={self.take_profit_pct*100:.0f}% | Trailing-Stop={self.trailing_stop_pct*100:.0f}%")
        print(f"⚖️ Rebalancing: {self.rebalance_frequency.upper()} | Target Weight: {self.target_weight*100:.0f}% | Drift Threshold: {self.drift_threshold*100:.0f}%")
        print()
        
        # Convert dates
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date)
        
        # Sort signals by date
        signals = sorted(signals, key=lambda x: x['date'])
        
        # Create a date range for daily portfolio tracking
        date_range = pd.date_range(start=start_dt, end=end_dt, freq='D')
        
        signal_idx = 0
        
        # Process each day
        for date in date_range:
            # Check if it's a weekday (markets open)
            if date.weekday() >= 5:  # Saturday or Sunday
                continue
            
            # Execute any signals for this date
            while signal_idx < len(signals) and pd.to_datetime(signals[signal_idx]['date']) <= date:
                signal = signals[signal_idx]
                ticker = signal['ticker']
                action = signal.get('action', 'BUY')
                signal_strength = signal.get('signal_strength', 1.0)
                
                # Get price for this date
                if ticker in historical_prices:
                    prices_df = historical_prices[ticker]
                    if date in prices_df.index:
                        price = prices_df.loc[date, 'Close']
                        
                        if action == 'BUY':
                            # Calculate shares to buy
                            position_value = self.calculate_position_size(ticker, signal_strength)
                            if price > 0:
                                shares = int(position_value / price)
                                
                                if shares > 0:
                                    self.execute_trade(date, ticker, shares, price, 'BUY')
                            else:
                                print(f"⚠️ Skipping {ticker}: Price is {price}")
                        
                        elif action == 'SELL':
                            # Sell entire position
                            if ticker in self.positions:
                                shares = self.positions[ticker]
                                self.execute_trade(date, ticker, shares, price, 'SELL')
                
                signal_idx += 1
            
            # Calculate current prices for all positions
            current_prices = {}
            for ticker in list(self.positions.keys()):
                if ticker in historical_prices:
                    prices_df = historical_prices[ticker]
                    # Find closest date
                    available_dates = prices_df.index[prices_df.index <= date]
                    if len(available_dates) > 0:
                        closest_date = available_dates[-1]
                        current_prices[ticker] = prices_df.loc[closest_date, 'Close']
            
            # Check exit signals (stop-loss, take-profit, trailing stop)
            exit_signals = self.check_exit_signals(date, current_prices)
            
            for exit_signal in exit_signals:
                ticker = exit_signal['ticker']
                if ticker in current_prices:
                    self.execute_exit(
                        date=date,
                        ticker=ticker,
                        price=current_prices[ticker],
                        reason=exit_signal['reason'],
                        exit_type=exit_signal['exit_type']
                    )
            
            # Check if rebalancing should occur
            if self.positions and self.should_rebalance(date, current_prices):
                self.execute_rebalancing(date, current_prices)
            
            # Recalculate current prices after exits and rebalancing
            current_prices_after = {}
            for ticker in list(self.positions.keys()):
                if ticker in historical_prices:
                    prices_df = historical_prices[ticker]
                    available_dates = prices_df.index[prices_df.index <= date]
                    if len(available_dates) > 0:
                        closest_date = available_dates[-1]
                        current_prices_after[ticker] = prices_df.loc[closest_date, 'Close']
            
            portfolio_value = self.calculate_portfolio_value(date, current_prices_after)
            
            self.portfolio_history.append({
                'date': date,
                'portfolio_value': portfolio_value,
                'cash': self.cash,
                'positions_value': portfolio_value - self.cash,
                'num_positions': len(self.positions)
            })
        
        # Check if we have any portfolio history
        if len(self.portfolio_history) == 0:
            print("⚠️ No portfolio history - no trades were executed")
            print("   This usually means signal dates don't overlap with price data")
            return {
                'initial_capital': self.initial_capital,
                'final_value': self.initial_capital,
                'total_return': 0,
                'cagr': 0,
                'volatility': 0,
                'sharpe_ratio': 0,
                'sortino_ratio': 0,
                'max_drawdown': 0,
                'romad': 0,
                'alpha': 0,
                'beta': 0,
                'information_ratio': 0,
                'var_95': 0,
                'cvar_95': 0,
                'win_rate_daily': 0,
                'win_rate_monthly': 0,
                'profit_factor': 0,
                'trades': self.trades,
                'equity_curve': [],
                'benchmark_total_return': 0,
                'benchmark_cagr': 0,
                'warning': 'No trades executed - signal dates may not overlap with available price data'
            }
        
        # Calculate performance metrics
        return self.calculate_metrics()
    
    def calculate_metrics(self) -> Dict:
        """
        Calculate comprehensive performance metrics from portfolio history
        Includes all fields required by BacktestSummary schema
        """
        if not self.portfolio_history:
            return {}
        
        df = pd.DataFrame(self.portfolio_history)
        df.set_index('date', inplace=True)
        
        # Basic metrics
        final_value = df['portfolio_value'].iloc[-1]
        total_return = (final_value - self.initial_capital) / self.initial_capital
        
        # Daily returns
        df['daily_return'] = df['portfolio_value'].pct_change()
        
        # Volatility (annualized)
        volatility = df['daily_return'].std() * np.sqrt(252)
        
        # Sharpe Ratio (assuming 0% risk-free rate)
        sharpe_ratio = (total_return * 252 / len(df)) / volatility if volatility > 0 and len(df) > 0 else 0
        
        # Maximum Drawdown
        df['cummax'] = df['portfolio_value'].cummax()
        # Avoid division by zero
        df['drawdown'] = df.apply(
            lambda row: (row['portfolio_value'] - row['cummax']) / row['cummax'] if row['cummax'] > 0 else 0, 
            axis=1
        )
        max_drawdown = df['drawdown'].min() if len(df) > 0 else 0
        
        # Sortino Ratio (downside deviation)
        downside_returns = df['daily_return'][df['daily_return'] < 0]
        downside_deviation = downside_returns.std() * np.sqrt(252) if len(downside_returns) > 0 else 0
        sortino_ratio = (total_return * 252 / len(df)) / downside_deviation if downside_deviation > 0 and len(df) > 0 else 0
        
        # CAGR
        years = len(df) / 252
        cagr = (final_value / self.initial_capital) ** (1 / years) - 1 if years > 0 else 0
        
        # Win rates (daily, monthly, yearly)
        winning_days = len(df[df['daily_return'] > 0])
        total_days = len(df[df['daily_return'].notna()])
        win_rate_daily = winning_days / total_days if total_days > 0 else 0
        
        # Monthly win rate
        df_monthly = df.resample('M')['portfolio_value'].last().pct_change()
        monthly_count = len(df_monthly.dropna())
        win_rate_monthly = len(df_monthly[df_monthly > 0]) / monthly_count if monthly_count > 0 else 0
        
        # Yearly win rate (use 'A' for year-end frequency - compatible with all pandas versions)
        try:
            df_yearly = df.resample('A')['portfolio_value'].last().pct_change()
            yearly_count = len(df_yearly.dropna())
            win_rate_yearly = len(df_yearly[df_yearly > 0]) / yearly_count if yearly_count > 0 else 0
        except Exception:
            win_rate_yearly = 0
        
        # Best and worst days
        best_day = df['daily_return'].max() if len(df) > 0 else 0
        worst_day = df['daily_return'].min() if len(df) > 0 else 0
        
        # RoMAD (Return over Maximum Drawdown)
        romad = abs(total_return / max_drawdown) if max_drawdown != 0 else 0
        
        # Alpha and Beta (vs SPY benchmark - simplified calculation)
        # For now, use simplified estimates. Proper calculation requires benchmark data.
        beta = 1.0  # Neutral beta assumption
        benchmark_return = 0.10 * years  # Assume 10% annual benchmark return
        alpha = total_return - (beta * benchmark_return)
        
        # Information Ratio (simplified)
        information_ratio = alpha / volatility if volatility > 0 else 0
        
        # VaR and CVaR (95% confidence)
        var_95 = df['daily_return'].quantile(0.05) if len(df) > 0 else 0
        cvar_95 = df['daily_return'][df['daily_return'] <= var_95].mean() if len(df) > 0 else 0
        
        # Benchmark metrics (simplified - assume SPY-like returns)
        benchmark_total_return = 0.10 * years
        benchmark_cagr = 0.10
        
        print(f"\n📊 Backtest Results:")
        print(f"   Initial: ${self.initial_capital:,.2f}")
        print(f"   Final:   ${final_value:,.2f}")
        print(f"   Return:  {total_return*100:.2f}%")
        print(f"   CAGR:    {cagr*100:.2f}%")
        print(f"   Sharpe:  {sharpe_ratio:.2f}")
        print(f"   Max DD:  {max_drawdown*100:.2f}%")
        print(f"   Trades:  {len(self.trades)}")
        print(f"   Rebalances: {self.rebalance_count} ({self.rebalance_frequency})")
        print()
        
        return {
            'initial_capital': self.initial_capital,
            'final_value': final_value,
            'total_return': total_return,
            'cagr': cagr,
            'volatility': volatility,
            'sharpe_ratio': sharpe_ratio,
            'sortino_ratio': sortino_ratio,
            'max_drawdown': max_drawdown,
            'romad': romad,
            'alpha': alpha,
            'beta': beta,
            'information_ratio': information_ratio,
            'var_95': var_95,
            'cvar_95': cvar_95,
            'win_rate': win_rate_daily,  # Keep for backward compatibility
            'win_rate_daily': win_rate_daily,
            'win_rate_monthly': win_rate_monthly,
            'win_rate_yearly': win_rate_yearly,
            'best_day': best_day,
            'worst_day': worst_day,
            'benchmark_total_return': benchmark_total_return,
            'benchmark_cagr': benchmark_cagr,
            'total_trades': len(self.trades),
            'portfolio_history': df['portfolio_value'].tolist(),
            'dates': [d.strftime('%Y-%m-%d') for d in df.index],
            'trades': self.trades,
            # Rebalancing statistics
            'rebalance_count': self.rebalance_count,
            'rebalance_frequency': self.rebalance_frequency,
            'rebalance_config': {
                'frequency': self.rebalance_frequency,
                'drift_threshold': self.drift_threshold,
                'target_weight': self.target_weight,
                'min_positions': self.min_positions,
                'max_positions': self.max_positions
            }
        }

