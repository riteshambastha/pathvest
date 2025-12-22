"""
Backtrader Integration for PathVest
====================================
A production-grade backtesting engine using Backtrader framework.
Replaces the custom HistoricalBacktestEngine with industry-standard tooling.
"""

import backtrader as bt
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging
import yfinance as yf

logger = logging.getLogger(__name__)


class PathVestStrategy(bt.Strategy):
    """
    Custom Backtrader strategy implementing PathVest's institutional signal-based trading.
    
    Features:
    - T+1 execution (signals received on day T execute on day T+1)
    - Position sizing (5% per position, max 20 positions)
    - Exit signals (stop-loss, take-profit, trailing stop, thesis drift)
    - Rebalancing rules
    """
    
    params = (
        # Position sizing
        ('position_pct', 0.05),       # 5% per position
        ('max_positions', 20),
        ('min_positions', 5),
        
        # Exit rules
        ('stop_loss_pct', 0.20),      # 20% stop loss
        ('take_profit_pct', 0.75),    # 75% take profit
        ('trailing_stop_pct', 0.25),  # 25% trailing stop
        ('enable_stop_loss', True),
        ('enable_take_profit', False),
        ('enable_trailing_stop', False),
        
        # Signals
        ('signals', None),            # List of {date, ticker, action, strength}
        
        # Rebalancing
        ('rebalance_frequency', 'monthly'),
        ('drift_threshold', 0.05),
    )
    
    def __init__(self):
        self.order_refs = {}
        self.entry_prices = {}
        self.peak_prices = {}
        self.signal_queue = []
        self.trade_log = []
        self.daily_values = []
        self.last_rebalance_date = None
        
        # Parse signals into queue
        if self.params.signals:
            for sig in self.params.signals:
                sig_date = pd.to_datetime(sig['date']).date()
                self.signal_queue.append({
                    'signal_date': sig_date,
                    'execute_date': sig_date + timedelta(days=1),  # T+1
                    'ticker': sig['ticker'],
                    'action': sig.get('action', 'BUY'),
                    'strength': sig.get('signal_strength', 1.0),
                    'conviction': sig.get('conviction_score', 0.5),
                })
        
        logger.info(f"📊 Strategy initialized with {len(self.signal_queue)} signals")
    
    def notify_order(self, order):
        """Handle order notifications"""
        if order.status in [order.Completed]:
            ticker = order.data._name
            if order.isbuy():
                self.entry_prices[ticker] = order.executed.price
                self.peak_prices[ticker] = order.executed.price
                logger.info(f"  ✅ BUY {ticker} @ ${order.executed.price:.2f} x {order.executed.size}")
                
                self.trade_log.append({
                    'date': self.datetime.date(),
                    'ticker': ticker,
                    'action': 'BUY',
                    'price': order.executed.price,
                    'shares': order.executed.size,
                    'value': order.executed.value,
                })
            else:
                entry_price = self.entry_prices.get(ticker, order.executed.price)
                pnl = (order.executed.price - entry_price) * order.executed.size
                return_pct = (order.executed.price / entry_price - 1) if entry_price > 0 else 0
                
                logger.info(f"  ✅ SELL {ticker} @ ${order.executed.price:.2f} | P&L: ${pnl:,.2f} ({return_pct:.1%})")
                
                self.trade_log.append({
                    'date': self.datetime.date(),
                    'ticker': ticker,
                    'action': 'SELL',
                    'price': order.executed.price,
                    'shares': order.executed.size,
                    'value': order.executed.value,
                    'pnl': pnl,
                    'return_pct': return_pct,
                })
                
                # Clean up tracking
                if ticker in self.entry_prices:
                    del self.entry_prices[ticker]
                if ticker in self.peak_prices:
                    del self.peak_prices[ticker]
    
    def next(self):
        """Called on each bar (day)"""
        current_date = self.datetime.date()
        
        # Record daily portfolio value
        self.daily_values.append({
            'date': current_date,
            'value': self.broker.getvalue(),
            'cash': self.broker.getcash(),
        })
        
        # Process signals for T+1 execution
        signals_to_execute = [s for s in self.signal_queue if s['execute_date'] == current_date]
        
        for signal in signals_to_execute:
            ticker = signal['ticker']
            action = signal['action']
            
            # Find the data feed for this ticker
            data = None
            for d in self.datas:
                if d._name == ticker:
                    data = d
                    break
            
            if data is None:
                continue
            
            if action == 'BUY':
                # Check if we can add more positions
                current_positions = len([d for d in self.datas if self.getposition(d).size > 0])
                
                if current_positions >= self.params.max_positions:
                    logger.info(f"  ⚠️ Max positions ({self.params.max_positions}) reached, skipping {ticker}")
                    continue
                
                # Calculate position size
                portfolio_value = self.broker.getvalue()
                position_value = portfolio_value * self.params.position_pct
                price = data.close[0]
                
                if price > 0:
                    shares = int(position_value / price)
                    if shares > 0 and self.broker.getcash() >= shares * price:
                        self.buy(data=data, size=shares)
                        logger.info(f"📈 Signal: BUY {shares} {ticker} @ ~${price:.2f}")
            
            elif action == 'SELL':
                position = self.getposition(data)
                if position.size > 0:
                    self.sell(data=data, size=position.size)
                    logger.info(f"📉 Signal: SELL {position.size} {ticker}")
        
        # Remove executed signals
        self.signal_queue = [s for s in self.signal_queue if s['execute_date'] != current_date]
        
        # Check exit conditions for all positions
        self._check_exit_signals()
        
        # Check rebalancing
        self._check_rebalancing(current_date)
    
    def _check_exit_signals(self):
        """Check and execute exit signals (stop-loss, take-profit, trailing stop)"""
        for data in self.datas:
            position = self.getposition(data)
            if position.size <= 0:
                continue
            
            ticker = data._name
            current_price = data.close[0]
            entry_price = self.entry_prices.get(ticker, current_price)
            peak_price = self.peak_prices.get(ticker, entry_price)
            
            # Update peak price for trailing stop
            if current_price > peak_price:
                self.peak_prices[ticker] = current_price
                peak_price = current_price
            
            return_pct = (current_price / entry_price - 1) if entry_price > 0 else 0
            drawdown_from_peak = (peak_price - current_price) / peak_price if peak_price > 0 else 0
            
            exit_reason = None
            
            # Stop loss check
            if self.params.enable_stop_loss and return_pct <= -self.params.stop_loss_pct:
                exit_reason = 'STOP_LOSS'
            
            # Take profit check
            elif self.params.enable_take_profit and return_pct >= self.params.take_profit_pct:
                exit_reason = 'TAKE_PROFIT'
            
            # Trailing stop check
            elif self.params.enable_trailing_stop and drawdown_from_peak >= self.params.trailing_stop_pct:
                exit_reason = 'TRAILING_STOP'
            
            if exit_reason:
                logger.info(f"🚨 {exit_reason}: Selling {ticker} | Return: {return_pct:.1%}")
                self.sell(data=data, size=position.size)
    
    def _check_rebalancing(self, current_date):
        """Check if rebalancing is needed"""
        if self.last_rebalance_date is None:
            self.last_rebalance_date = current_date
            return
        
        should_rebalance = False
        
        if self.params.rebalance_frequency == 'weekly':
            should_rebalance = (current_date - self.last_rebalance_date).days >= 7
        elif self.params.rebalance_frequency == 'monthly':
            should_rebalance = (current_date - self.last_rebalance_date).days >= 30
        elif self.params.rebalance_frequency == 'quarterly':
            should_rebalance = (current_date - self.last_rebalance_date).days >= 90
        
        if should_rebalance:
            self._execute_rebalancing()
            self.last_rebalance_date = current_date
    
    def _execute_rebalancing(self):
        """Rebalance positions to target weights"""
        portfolio_value = self.broker.getvalue()
        target_value_per_position = portfolio_value * self.params.position_pct
        
        for data in self.datas:
            position = self.getposition(data)
            if position.size <= 0:
                continue
            
            current_value = position.size * data.close[0]
            drift = abs(current_value - target_value_per_position) / target_value_per_position
            
            if drift > self.params.drift_threshold:
                ticker = data._name
                target_shares = int(target_value_per_position / data.close[0])
                diff = target_shares - position.size
                
                if diff > 0:
                    self.buy(data=data, size=diff)
                    logger.info(f"⚖️ Rebalance: BUY {diff} {ticker}")
                elif diff < 0:
                    self.sell(data=data, size=abs(diff))
                    logger.info(f"⚖️ Rebalance: SELL {abs(diff)} {ticker}")


class BacktraderEngine:
    """
    Main Backtrader engine wrapper for PathVest.
    Handles data loading, strategy execution, and result processing.
    """
    
    def __init__(
        self,
        initial_capital: float = 1_000_000,
        commission: float = 0.001,  # 0.1% commission
        slippage: float = 0.0025,   # 0.25% slippage
    ):
        self.initial_capital = initial_capital
        self.commission = commission
        self.slippage = slippage
        self.cerebro = None
        self.results = None
        
    async def run_backtest(
        self,
        signals: List[Dict],
        start_date: str,
        end_date: str,
        strategy_config: Dict,
        price_data: Optional[Dict[str, pd.DataFrame]] = None,
    ) -> Dict:
        """
        Run a backtest using Backtrader.
        
        Args:
            signals: List of trading signals [{date, ticker, action, signal_strength}, ...]
            start_date: Backtest start date
            end_date: Backtest end date
            strategy_config: Strategy configuration
            price_data: Optional pre-fetched price data
        
        Returns:
            Dict with backtest results
        """
        logger.info(f"🚀 Starting Backtrader backtest: {start_date} to {end_date}")
        logger.info(f"   Initial Capital: ${self.initial_capital:,.0f}")
        logger.info(f"   Signals: {len(signals)}")
        
        # Initialize Cerebro
        self.cerebro = bt.Cerebro()
        self.cerebro.broker.setcash(self.initial_capital)
        self.cerebro.broker.setcommission(commission=self.commission)
        
        # Extract unique tickers from signals
        tickers = list(set([s['ticker'] for s in signals if s.get('ticker')]))
        logger.info(f"   Unique tickers: {len(tickers)}")
        
        if not tickers:
            return self._empty_results("No tickers in signals")
        
        # Load price data for each ticker
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date)
        
        loaded_tickers = []
        for ticker in tickers[:50]:  # Limit to 50 tickers for performance
            try:
                if price_data and ticker in price_data:
                    df = price_data[ticker]
                else:
                    df = await self._fetch_price_data(ticker, start_date, end_date)
                
                if df is not None and len(df) > 0:
                    # Convert to Backtrader data feed
                    data = bt.feeds.PandasData(
                        dataname=df,
                        fromdate=start_dt,
                        todate=end_dt,
                        name=ticker,
                    )
                    self.cerebro.adddata(data)
                    loaded_tickers.append(ticker)
                    
            except Exception as e:
                logger.warning(f"  ⚠️ Failed to load {ticker}: {e}")
                continue
        
        if not loaded_tickers:
            return self._empty_results("Failed to load price data for any ticker")
        
        logger.info(f"   Loaded data for {len(loaded_tickers)} tickers")
        
        # Filter signals to only include loaded tickers
        valid_signals = [s for s in signals if s.get('ticker') in loaded_tickers]
        
        # Extract strategy parameters
        exit_rules = strategy_config.get('exit_rules', {})
        position_sizing = strategy_config.get('position_sizing', {})
        heartbeat = strategy_config.get('heartbeat', {})
        
        # Add strategy with parameters
        self.cerebro.addstrategy(
            PathVestStrategy,
            signals=valid_signals,
            position_pct=position_sizing.get('percent_per_position', 0.05),
            max_positions=position_sizing.get('max_positions', 20),
            min_positions=position_sizing.get('min_positions', 5),
            stop_loss_pct=exit_rules.get('stop_loss_pct', 0.20),
            take_profit_pct=exit_rules.get('take_profit_pct', 0.75),
            trailing_stop_pct=exit_rules.get('trailing_stop_pct', 0.25),
            enable_stop_loss=exit_rules.get('enable_stop_loss', True),
            enable_take_profit=exit_rules.get('enable_take_profit', False),
            enable_trailing_stop=exit_rules.get('enable_trailing_stop', False),
            rebalance_frequency=heartbeat.get('rebalance_frequency', 'monthly'),
            drift_threshold=heartbeat.get('rebalance_threshold', 0.05),
        )
        
        # Add analyzers
        self.cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe', riskfreerate=0.04)
        self.cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
        self.cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
        self.cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
        self.cerebro.addanalyzer(bt.analyzers.SQN, _name='sqn')
        
        # Run backtest
        logger.info("   Running backtest...")
        results = self.cerebro.run()
        strat = results[0]
        
        # Extract results
        final_value = self.cerebro.broker.getvalue()
        total_return = (final_value / self.initial_capital) - 1
        
        # Get analyzer results
        sharpe = strat.analyzers.sharpe.get_analysis()
        drawdown = strat.analyzers.drawdown.get_analysis()
        trades = strat.analyzers.trades.get_analysis()
        returns = strat.analyzers.returns.get_analysis()
        sqn = strat.analyzers.sqn.get_analysis()
        
        # Build portfolio history from daily values
        portfolio_history = []
        for dv in strat.daily_values:
            portfolio_history.append({
                'date': dv['date'].isoformat(),
                'portfolio_value': dv['value'],
                'cash': dv['cash'],
            })
        
        # Calculate metrics
        sharpe_ratio = sharpe.get('sharperatio', 0) or 0
        max_drawdown = drawdown.get('max', {}).get('drawdown', 0) / 100 if drawdown.get('max') else 0
        
        total_trades = trades.get('total', {}).get('total', 0) if trades.get('total') else 0
        won_trades = trades.get('won', {}).get('total', 0) if trades.get('won') else 0
        win_rate = won_trades / total_trades if total_trades > 0 else 0
        
        result = {
            'success': True,
            'engine': 'backtrader',
            'total_return': total_return,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': -abs(max_drawdown),
            'final_value': final_value,
            'initial_capital': self.initial_capital,
            'total_trades': total_trades,
            'winning_trades': won_trades,
            'losing_trades': total_trades - won_trades,
            'win_rate': win_rate,
            'sqn': sqn.get('sqn', 0) or 0,
            'cagr': self._calculate_cagr(self.initial_capital, final_value, start_date, end_date),
            'trade_log': strat.trade_log,
            'portfolio_history': portfolio_history,
            'stocks_analyzed': loaded_tickers,
            'signals_processed': len(valid_signals),
        }
        
        logger.info(f"\n{'='*60}")
        logger.info(f"📊 BACKTEST COMPLETE")
        logger.info(f"   Total Return: {total_return:.2%}")
        logger.info(f"   Sharpe Ratio: {sharpe_ratio:.2f}")
        logger.info(f"   Max Drawdown: {max_drawdown:.2%}")
        logger.info(f"   Total Trades: {total_trades}")
        logger.info(f"   Win Rate: {win_rate:.1%}")
        logger.info(f"{'='*60}")
        
        return result
    
    async def _fetch_price_data(
        self,
        ticker: str,
        start_date: str,
        end_date: str,
    ) -> Optional[pd.DataFrame]:
        """Fetch price data using yfinance"""
        try:
            df = yf.download(
                ticker,
                start=start_date,
                end=end_date,
                progress=False,
                auto_adjust=True,
            )
            
            if df.empty:
                return None
            
            # Ensure proper column names for Backtrader
            df.columns = [c.lower() for c in df.columns]
            if 'adj close' in df.columns:
                df = df.drop('adj close', axis=1)
            
            return df
            
        except Exception as e:
            logger.warning(f"Error fetching {ticker}: {e}")
            return None
    
    def _calculate_cagr(
        self,
        initial: float,
        final: float,
        start_date: str,
        end_date: str,
    ) -> float:
        """Calculate Compound Annual Growth Rate"""
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date)
        years = (end_dt - start_dt).days / 365.25
        
        if years <= 0 or initial <= 0:
            return 0
        
        return (final / initial) ** (1 / years) - 1
    
    def _empty_results(self, reason: str) -> Dict:
        """Return empty results with error"""
        return {
            'success': False,
            'error': reason,
            'engine': 'backtrader',
            'total_return': 0,
            'sharpe_ratio': 0,
            'max_drawdown': 0,
            'final_value': self.initial_capital,
            'initial_capital': self.initial_capital,
            'total_trades': 0,
            'trade_log': [],
            'portfolio_history': [],
        }


# Factory function
def get_backtrader_engine(
    initial_capital: float = 1_000_000,
    **kwargs
) -> BacktraderEngine:
    """Get a configured Backtrader engine instance"""
    return BacktraderEngine(initial_capital=initial_capital, **kwargs)

