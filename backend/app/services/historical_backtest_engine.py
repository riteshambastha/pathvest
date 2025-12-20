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
    """
    
    def __init__(self, initial_capital: float = 100000):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions = {}  # {ticker: shares}
        self.portfolio_history = []
        self.trades = []
        # Load API key dynamically (not at module level)
        self.api_key = os.getenv("ALPHAVANTAGE_API_KEY", "")
        
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
                
                self.trades.append({
                    'date': date,
                    'ticker': ticker,
                    'action': 'BUY',
                    'shares': shares,
                    'price': execution_price,
                    'cost': cost,
                    'cash_after': self.cash
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
    
    def run_backtest(
        self,
        signals: List[Dict],  # [{date, ticker, action, signal_strength}, ...]
        historical_prices: Dict[str, pd.DataFrame],  # {ticker: DataFrame}
        start_date: str,
        end_date: str
    ) -> Dict:
        """
        Run the backtest simulation
        
        Args:
            signals: List of trading signals with dates
            historical_prices: Dict of ticker -> price DataFrames
            start_date: Backtest start date
            end_date: Backtest end date
            
        Returns:
            Dict with performance metrics
        """
        print(f"\n🎯 Running backtest: {start_date} to {end_date}")
        print(f"💰 Initial capital: ${self.initial_capital:,.2f}")
        print(f"📊 Signals: {len(signals)}")
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
            
            # Calculate portfolio value for this date
            current_prices = {}
            for ticker in self.positions.keys():
                if ticker in historical_prices:
                    prices_df = historical_prices[ticker]
                    # Find closest date
                    available_dates = prices_df.index[prices_df.index <= date]
                    if len(available_dates) > 0:
                        closest_date = available_dates[-1]
                        current_prices[ticker] = prices_df.loc[closest_date, 'Close']
            
            portfolio_value = self.calculate_portfolio_value(date, current_prices)
            
            self.portfolio_history.append({
                'date': date,
                'portfolio_value': portfolio_value,
                'cash': self.cash,
                'positions_value': portfolio_value - self.cash
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
            'trades': self.trades
        }

