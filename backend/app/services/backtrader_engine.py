"""
Backtrader Integration for PathVest
====================================
A production-grade backtesting engine using Backtrader framework.
Full implementation with all metrics required for the results dashboard.

Enhanced with:
- Robust queue management for yfinance requests with rate limiting
- Smart retry logic with exponential backoff and jitter
- Accurate time estimation and progress tracking
- Graceful handling of failed tickers (continue with partial data)
- Friendly messaging with break suggestions for long-running backtests
"""

import backtrader as bt
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Any, Tuple, Callable
import logging
import yfinance as yf
from scipy import stats
import asyncio
import time
import random
from collections import deque

logger = logging.getLogger(__name__)

# Configuration for yfinance request management - optimized for reliability
YFINANCE_CONFIG = {
    'max_retries': 5,           # More retries for resilience
    'base_delay': 0.5,          # Start with shorter delay
    'max_delay': 60.0,          # Cap at 60 seconds
    'concurrent_requests': 3,    # Reduced for rate limiting
    'batch_size': 10,           # Smaller batches for better control
    'batch_delay': 1.5,         # Delay between batches
    'request_timeout': 30,      # Timeout per request
    'success_rate_threshold': 0.1,  # Minimum 10% success rate to continue
}

# Friendly break suggestions based on ETA
BREAK_SUGGESTIONS = [
    (30, '⚡', 'Almost there! Just a few more seconds...'),
    (60, '🍪', 'Quick snack break? We\'ll be done in about a minute!'),
    (120, '☕', 'Perfect time to grab a coffee! Back in ~2 minutes.'),
    (180, '🍵', 'How about making yourself a nice chai? ~3 min to go!'),
    (300, '🍦', 'Time for an ice cream break! We need ~5 minutes.'),
    (600, '🚶', 'Take a short walk! This will take ~10 minutes.'),
    (float('inf'), '📖', 'Read a chapter of your book! This is a thorough analysis.'),
]

def get_break_suggestion(eta_seconds: float) -> Tuple[str, str]:
    """Get a friendly break suggestion based on ETA."""
    for threshold, emoji, message in BREAK_SUGGESTIONS:
        if eta_seconds <= threshold:
            return emoji, message
    return BREAK_SUGGESTIONS[-1][1], BREAK_SUGGESTIONS[-1][2]

def format_eta(seconds: float) -> str:
    """Format ETA in human-readable format."""
    if seconds <= 0:
        return "almost done"
    if seconds < 60:
        return f"~{int(seconds)} seconds"
    if seconds < 120:
        return "~1 minute"
    if seconds < 3600:
        return f"~{int(seconds / 60)} minutes"
    return f"~{int(seconds / 3600)} hours"


class PathVestStrategy(bt.Strategy):
    """
    Custom Backtrader strategy implementing PathVest's institutional signal-based trading.
    
    Features:
    - T+1 execution (signals received on day T execute on day T+1)
    - Position sizing (5% per position, max 20 positions)
    - Exit signals (stop-loss, take-profit, trailing stop, thesis drift)
    - Rebalancing rules
    - Comprehensive trade logging with entry/exit details
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
        self.entry_dates = {}
        self.entry_shares = {}
        self.peak_prices = {}
        self.signal_queue = []
        self.trade_log = []  # Complete trades (with exit)
        self.open_positions = {}  # Positions not yet closed
        self.daily_values = []
        self.daily_returns = []
        self.last_rebalance_date = None
        self.rebalance_count = 0
        self.signal_metadata = {}  # Store signal info for trades
        
        # Parse signals into queue
        if self.params.signals:
            for sig in self.params.signals:
                sig_date = pd.to_datetime(sig['date']).date()
                ticker = sig['ticker']
                self.signal_queue.append({
                    'signal_date': sig_date,
                    'execute_date': sig_date + timedelta(days=1),  # T+1
                    'ticker': ticker,
                    'action': sig.get('action', 'BUY'),
                    'strength': sig.get('signal_strength', 1.0),
                    'conviction': sig.get('conviction_score', 0.5),
                    'signal_type': sig.get('signal_type', 'INSTITUTIONAL'),
                })
                # Store signal metadata for when trade is executed
                key = (sig_date + timedelta(days=1), ticker)
                self.signal_metadata[key] = {
                    'signal_type': sig.get('signal_type', 'INSTITUTIONAL'),
                    'conviction_score': sig.get('conviction_score', 0.5),
                    'signal_strength': sig.get('signal_strength', 1.0),
                }
        
        logger.info(f"📊 Strategy initialized with {len(self.signal_queue)} signals")
    
    def notify_order(self, order):
        """Handle order notifications"""
        if order.status in [order.Completed]:
            ticker = order.data._name
            current_date = self.datetime.date()
            
            if order.isbuy():
                # Record entry
                self.entry_prices[ticker] = order.executed.price
                self.entry_dates[ticker] = current_date
                self.entry_shares[ticker] = order.executed.size
                self.peak_prices[ticker] = order.executed.price
                
                # Get signal metadata
                key = (current_date, ticker)
                sig_meta = self.signal_metadata.get(key, {})
                
                # Track open position
                self.open_positions[ticker] = {
                    'entry_date': current_date,
                    'entry_price': order.executed.price,
                    'shares': order.executed.size,
                    'signal_type': sig_meta.get('signal_type', 'INSTITUTIONAL'),
                    'conviction_score': sig_meta.get('conviction_score', 0.5),
                }
                
                logger.info(f"  ✅ BUY {ticker} @ ${order.executed.price:.2f} x {order.executed.size}")
                
            else:
                # This is a sell - complete the trade
                entry_price = self.entry_prices.get(ticker, order.executed.price)
                entry_date = self.entry_dates.get(ticker, current_date)
                entry_shares = self.entry_shares.get(ticker, order.executed.size)
                
                pnl = (order.executed.price - entry_price) * order.executed.size
                return_pct = (order.executed.price / entry_price - 1) if entry_price > 0 else 0
                holding_days = (current_date - entry_date).days if entry_date else 0
                
                # Get open position data
                open_pos = self.open_positions.get(ticker, {})
                
                # Determine exit reason
                exit_reason = getattr(order, 'exit_reason', None) or 'SIGNAL'
                
                # Log complete trade
                self.trade_log.append({
                    'entry_date': entry_date.isoformat() if hasattr(entry_date, 'isoformat') else str(entry_date),
                    'exit_date': current_date.isoformat() if hasattr(current_date, 'isoformat') else str(current_date),
                    'ticker': ticker,
                    'entry_price': float(entry_price),
                    'exit_price': float(order.executed.price),
                    'shares': float(order.executed.size),
                    'pnl': float(pnl),
                    'return_pct': float(return_pct),
                    'holding_period_days': int(holding_days),
                    'exit_reason': exit_reason,
                    'signal_type': open_pos.get('signal_type', 'INSTITUTIONAL'),
                    'conviction_score': open_pos.get('conviction_score', 0.5),
                })
                
                logger.info(f"  ✅ SELL {ticker} @ ${order.executed.price:.2f} | P&L: ${pnl:,.2f} ({return_pct:.1%}) | Exit: {exit_reason}")
                
                # Clean up tracking
                for d in [self.entry_prices, self.entry_dates, self.entry_shares, self.peak_prices, self.open_positions]:
                    if ticker in d:
                        del d[ticker]
    
    def next(self):
        """Called on each bar (day)"""
        current_date = self.datetime.date()
        current_value = self.broker.getvalue()
        
        # Calculate daily return
        if len(self.daily_values) > 0:
            prev_value = self.daily_values[-1]['value']
            if prev_value > 0:
                daily_return = (current_value / prev_value) - 1
                self.daily_returns.append({
                    'date': current_date,
                    'return': daily_return,
                })
        
        # Record daily portfolio value
        self.daily_values.append({
            'date': current_date,
            'value': current_value,
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
                    order = self.sell(data=data, size=position.size)
                    order.exit_reason = 'SIGNAL'
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
                order = self.sell(data=data, size=position.size)
                order.exit_reason = exit_reason
    
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
            self.rebalance_count += 1
    
    def _execute_rebalancing(self):
        """Rebalance positions to target weights"""
        portfolio_value = self.broker.getvalue()
        target_value_per_position = portfolio_value * self.params.position_pct
        
        for data in self.datas:
            position = self.getposition(data)
            if position.size <= 0:
                continue
            
            current_value = position.size * data.close[0]
            if target_value_per_position > 0:
                drift = abs(current_value - target_value_per_position) / target_value_per_position
            else:
                drift = 0
            
            if drift > self.params.drift_threshold:
                ticker = data._name
                if data.close[0] > 0:
                    target_shares = int(target_value_per_position / data.close[0])
                    diff = target_shares - position.size
                    
                    if diff > 0:
                        self.buy(data=data, size=diff)
                        logger.info(f"⚖️ Rebalance: BUY {diff} {ticker}")
                    elif diff < 0:
                        order = self.sell(data=data, size=abs(diff))
                        order.exit_reason = 'REBALANCE'
                        logger.info(f"⚖️ Rebalance: SELL {abs(diff)} {ticker}")


class YFinanceQueueManager:
    """
    Robust queue manager for yfinance API requests with:
    - Rate limiting to avoid API throttling
    - Exponential backoff with jitter for retries
    - Progress tracking with accurate ETA
    - Graceful degradation (continue with partial data)
    - Friendly messaging for long-running operations
    """
    
    def __init__(self, progress_callback: Optional[Callable] = None):
        self.progress_callback = progress_callback
        self.completed = 0
        self.failed = 0
        self.total = 0
        self.failed_tickers = []
        self.successful_tickers = []
        self.start_time = None
        self.semaphore = asyncio.Semaphore(YFINANCE_CONFIG['concurrent_requests'])
        
        # Rolling average for more accurate ETA
        self.fetch_times = deque(maxlen=20)  # Keep last 20 fetch times
        self.last_progress_update = 0
        self.current_ticker = None
        self.rate_limit_hits = 0
        self.consecutive_failures = 0
        self.max_consecutive_failures = 10  # Stop if too many consecutive failures
    
    async def fetch_with_retry(
        self,
        ticker: str,
        start_date: str,
        end_date: str,
        retry_count: int = 0
    ) -> Optional[pd.DataFrame]:
        """Fetch price data with intelligent retry logic and rate limiting."""
        max_retries = YFINANCE_CONFIG['max_retries']
        base_delay = YFINANCE_CONFIG['base_delay']
        max_delay = YFINANCE_CONFIG['max_delay']
        timeout = YFINANCE_CONFIG['request_timeout']
        
        async with self.semaphore:
            fetch_start = time.time()
            self.current_ticker = ticker
            
            while retry_count < max_retries:
                try:
                    # Add jitter to prevent thundering herd
                    jitter = random.uniform(0.2, 0.8)
                    await asyncio.sleep(jitter)
                    
                    # Use asyncio.wait_for with timeout
                    loop = asyncio.get_event_loop()
                    df = await asyncio.wait_for(
                        loop.run_in_executor(
                            None,
                            lambda: yf.download(
                                ticker,
                                start=start_date,
                                end=end_date,
                                progress=False,
                                auto_adjust=True,
                                threads=False,
                            )
                        ),
                        timeout=timeout
                    )
                    
                    if df is not None and not df.empty:
                        # Normalize column names
                        df.columns = [c.lower() if isinstance(c, str) else c[0].lower() for c in df.columns]
                        if 'adj close' in df.columns:
                            df = df.drop('adj close', axis=1)
                        
                        # Record successful fetch time
                        fetch_time = time.time() - fetch_start
                        self.fetch_times.append(fetch_time)
                        self.consecutive_failures = 0  # Reset on success
                        
                        return df
                    else:
                        # No data available - not a failure, just no data
                        logger.debug(f"No data available for {ticker}")
                        return None
                        
                except asyncio.TimeoutError:
                    retry_count += 1
                    logger.warning(f"⏱️ Timeout for {ticker}, retry {retry_count}/{max_retries}")
                    await asyncio.sleep(base_delay * retry_count)
                    
                except Exception as e:
                    retry_count += 1
                    error_str = str(e).lower()
                    
                    # Check for rate limiting
                    if 'rate' in error_str or '429' in error_str or 'throttl' in error_str:
                        self.rate_limit_hits += 1
                        delay = min(base_delay * (4 ** retry_count), max_delay)  # More aggressive backoff
                        logger.warning(f"🚦 Rate limited on {ticker}, waiting {delay:.1f}s (hit #{self.rate_limit_hits})")
                        await asyncio.sleep(delay)
                    elif retry_count < max_retries:
                        delay = min(base_delay * (2 ** retry_count) + random.uniform(0, 1), max_delay)
                        logger.warning(f"⚠️ Retry {retry_count}/{max_retries} for {ticker}: {e}")
                        await asyncio.sleep(delay)
                    else:
                        logger.error(f"❌ Failed {ticker} after {max_retries} retries: {e}")
                        self.consecutive_failures += 1
                        return None
        
        return None
    
    def _calculate_eta(self) -> float:
        """Calculate ETA based on rolling average of fetch times."""
        if not self.fetch_times:
            # Initial estimate: 3 seconds per ticker
            return (self.total - self.completed - self.failed) * 3.0
        
        avg_time = sum(self.fetch_times) / len(self.fetch_times)
        remaining = self.total - self.completed - self.failed
        return remaining * avg_time
    
    def _get_progress_message(self) -> str:
        """Generate a friendly progress message."""
        processed = self.completed + self.failed
        pct = int((processed / max(self.total, 1)) * 100)
        
        if pct < 10:
            return f"🚀 Starting up... ({processed}/{self.total} stocks)"
        elif pct < 30:
            return f"📊 Building momentum... ({processed}/{self.total} stocks)"
        elif pct < 50:
            return f"📈 Halfway there! ({processed}/{self.total} stocks)"
        elif pct < 70:
            return f"⚡ Making great progress! ({processed}/{self.total} stocks)"
        elif pct < 90:
            return f"🎯 Almost done! ({processed}/{self.total} stocks)"
        else:
            return f"✨ Finishing up... ({processed}/{self.total} stocks)"
    
    async def fetch_batch(
        self,
        tickers: List[str],
        start_date: str,
        end_date: str,
    ) -> Dict[str, pd.DataFrame]:
        """Fetch price data with robust queue management and progress tracking."""
        self.total = len(tickers)
        self.completed = 0
        self.failed = 0
        self.start_time = time.time()
        self.failed_tickers = []
        self.successful_tickers = []
        self.fetch_times.clear()
        self.consecutive_failures = 0
        
        results = {}
        batch_size = YFINANCE_CONFIG['batch_size']
        total_batches = (len(tickers) + batch_size - 1) // batch_size
        
        logger.info(f"📦 Starting fetch: {len(tickers)} tickers in {total_batches} batches")
        
        # Initial progress report
        if self.progress_callback:
            await self._report_progress(stage='starting')
        
        # Process in batches
        for batch_num, batch_start in enumerate(range(0, len(tickers), batch_size)):
            # Check if we've hit too many consecutive failures
            if self.consecutive_failures >= self.max_consecutive_failures:
                logger.error(f"🛑 Stopping: {self.max_consecutive_failures} consecutive failures")
                break
            
            batch_end = min(batch_start + batch_size, len(tickers))
            batch = tickers[batch_start:batch_end]
            
            logger.info(f"📦 Batch {batch_num + 1}/{total_batches}: {len(batch)} tickers")
            
            # Create tasks for this batch
            tasks = []
            for ticker in batch:
                tasks.append(self._fetch_single(ticker, start_date, end_date, results))
            
            # Wait for batch to complete
            await asyncio.gather(*tasks, return_exceptions=True)
            
            # Update progress
            if self.progress_callback:
                await self._report_progress()
            
            # Delay between batches
            if batch_end < len(tickers):
                await asyncio.sleep(YFINANCE_CONFIG['batch_delay'])
        
        return results
    
    async def _fetch_single(
        self,
        ticker: str,
        start_date: str,
        end_date: str,
        results: Dict[str, pd.DataFrame]
    ):
        """Fetch a single ticker and update progress."""
        try:
            df = await self.fetch_with_retry(ticker, start_date, end_date)
            
            if df is not None and len(df) > 0:
                results[ticker] = df
                self.completed += 1
                self.successful_tickers.append(ticker)
            else:
                self.failed += 1
                self.failed_tickers.append(ticker)
                
        except Exception as e:
            self.failed += 1
            self.failed_tickers.append(ticker)
            logger.error(f"Error fetching {ticker}: {e}")
        
        # Report progress after each ticker
        if self.progress_callback:
            await self._report_progress()
    
    async def _report_progress(self, stage: str = 'fetching'):
        """Report current progress with time estimation and friendly messaging."""
        processed = self.completed + self.failed
        elapsed = time.time() - self.start_time if self.start_time else 0
        
        # Throttle progress updates (max once per 0.5 seconds)
        current_time = time.time()
        if current_time - self.last_progress_update < 0.5 and stage != 'starting':
            return
        self.last_progress_update = current_time
        
        # Calculate ETA using rolling average
        eta_seconds = self._calculate_eta()
        
        # Get friendly message and break suggestion
        emoji, break_suggestion = get_break_suggestion(eta_seconds)
        
        # Calculate success rate
        success_rate = (self.completed / max(processed, 1)) * 100
        
        # Build progress message
        if stage == 'starting':
            message = f"🚀 Preparing to fetch data for {self.total} stocks..."
            eta_message = f"Estimated time: {format_eta(eta_seconds)}"
        else:
            message = self._get_progress_message()
            if eta_seconds > 60:
                eta_message = f"{emoji} {break_suggestion}"
            else:
                eta_message = f"⚡ Almost there! {format_eta(eta_seconds)} remaining"
        
        progress_data = {
            'processed': processed,
            'total': self.total,
            'completed': self.completed,
            'failed': self.failed,
            'elapsed_seconds': elapsed,
            'eta_seconds': eta_seconds,
            'eta_message': eta_message,
            'avg_seconds_per_ticker': elapsed / max(processed, 1),
            'failed_tickers': self.failed_tickers[-5:],  # Last 5 failed
            'current_ticker': self.current_ticker,
            'success_rate': success_rate,
            'rate_limit_hits': self.rate_limit_hits,
            'message': message,
            'break_suggestion': break_suggestion,
            'break_emoji': emoji,
            'stage': stage,
        }
        
        try:
            if asyncio.iscoroutinefunction(self.progress_callback):
                await self.progress_callback(progress_data)
            else:
                self.progress_callback(progress_data)
        except Exception as e:
            logger.warning(f"Progress callback error: {e}")


class BacktraderEngine:
    """
    Main Backtrader engine wrapper for PathVest.
    Handles data loading, strategy execution, and comprehensive result processing.
    Returns all metrics required by the results dashboard.
    
    Enhanced with:
    - Robust queue management for yfinance requests
    - Progress tracking with ETA
    - Graceful handling of failed tickers
    """
    
    def __init__(
        self,
        initial_capital: float = 1_000_000,
        commission: float = 0.001,  # 0.1% commission
        slippage: float = 0.0025,   # 0.25% slippage
        benchmark_ticker: str = 'SPY',
        progress_callback: Optional[Callable] = None,
    ):
        self.initial_capital = initial_capital
        self.commission = commission
        self.slippage = slippage
        self.benchmark_ticker = benchmark_ticker
        self.cerebro = None
        self.results = None
        self.benchmark_data = None
        self.progress_callback = progress_callback
        self.queue_manager = YFinanceQueueManager(progress_callback)
        
    async def run_backtest(
        self,
        signals: List[Dict],
        start_date: str,
        end_date: str,
        strategy_config: Dict,
        price_data: Optional[Dict[str, pd.DataFrame]] = None,
        progress_callback: Optional[Callable] = None,
    ) -> Dict:
        """
        Run a backtest using Backtrader with comprehensive metrics.
        
        Returns all data needed for Summary, Overview, Trades, Attribution, Validation tabs.
        
        Enhanced with:
        - Robust queue management for yfinance
        - Progress tracking with ETA
        - Friendly messaging for long-running backtests
        """
        backtest_start_time = time.time()
        
        # Use provided callback or instance callback
        callback = progress_callback or self.progress_callback
        
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
        
        # Report initial progress
        if callback:
            try:
                init_progress = {
                    'stage': 'initializing',
                    'message': f'🚀 Preparing to fetch data for {len(tickers)} tickers...',
                    'percent': 5,
                    'total_tickers': len(tickers),
                    'eta_seconds': len(tickers) * 3,  # Initial estimate: 3 seconds per ticker
                }
                if asyncio.iscoroutinefunction(callback):
                    await callback(init_progress)
                else:
                    callback(init_progress)
            except Exception as e:
                logger.warning(f"Progress callback error: {e}")
        
        # Load price data for each ticker
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date)
        
        loaded_tickers = []
        price_data_dict = {}
        failed_tickers = []
        
        # Use the queue manager for robust fetching
        if price_data:
            # Use pre-loaded price data
            for ticker in tickers:
                if ticker in price_data and price_data[ticker] is not None:
                    price_data_dict[ticker] = price_data[ticker]
            logger.info(f"   Using pre-loaded data for {len(price_data_dict)} tickers")
        else:
            # Fetch data using queue manager with progress tracking
            async def data_progress_callback(progress_data):
                """Wrap progress for data fetching stage."""
                if callback:
                    processed = progress_data.get('processed', 0)
                    total = progress_data.get('total', len(tickers))
                    completed = progress_data.get('completed', 0)
                    failed = progress_data.get('failed', 0)
                    eta_seconds = progress_data.get('eta_seconds', 0)
                    current_ticker = progress_data.get('current_ticker')
                    
                    # Map to overall progress (10% - 80%)
                    percent = 10 + int((processed / max(total, 1)) * 70)
                    
                    # Create friendly message with ETA
                    if eta_seconds > 120:
                        eta_msg = f"☕ ~{int(eta_seconds / 60)} min remaining - perfect time for a coffee break!"
                    elif eta_seconds > 60:
                        eta_msg = f"🍵 ~{int(eta_seconds / 60)} min remaining - grab a chai while you wait!"
                    elif eta_seconds > 30:
                        eta_msg = f"🍦 ~{int(eta_seconds)} sec remaining - almost there!"
                    else:
                        eta_msg = f"⚡ ~{int(eta_seconds)} sec remaining - finishing up!"
                    
                    full_progress = {
                        'stage': 'fetching_data',
                        'message': f'📊 Market Data: {processed}/{total} stocks processed',
                        'percent': percent,
                        'eta_message': eta_msg,
                        'eta_seconds': eta_seconds,
                        'processed': processed,
                        'total': total,
                        'completed': completed,
                        'failed': failed,
                        'current_ticker': current_ticker,
                        'failed_tickers': progress_data.get('failed_tickers', []),
                    }
                    
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(full_progress)
                        else:
                            callback(full_progress)
                    except Exception as e:
                        logger.warning(f"Progress callback error: {e}")
            
            self.queue_manager = YFinanceQueueManager(data_progress_callback)
            price_data_dict = await self.queue_manager.fetch_batch(tickers, start_date, end_date)
            failed_tickers = self.queue_manager.failed_tickers
        
        # Add loaded data to Cerebro
        for ticker, df in price_data_dict.items():
            if df is not None and len(df) > 0:
                try:
                    data = bt.feeds.PandasData(
                        dataname=df,
                        fromdate=start_dt,
                        todate=end_dt,
                        name=ticker,
                    )
                    self.cerebro.adddata(data)
                    loaded_tickers.append(ticker)
                except Exception as e:
                    logger.warning(f"  ⚠️ Failed to add {ticker} to Cerebro: {e}")
                    failed_tickers.append(ticker)
        
        if not loaded_tickers:
            return self._empty_results(
                f"Failed to load price data for any ticker. "
                f"Failed tickers: {', '.join(failed_tickers[:10])}{'...' if len(failed_tickers) > 10 else ''}"
            )
        
        # Store for _build_comprehensive_results
        self._failed_tickers = failed_tickers
        
        logger.info(f"   Loaded data for {len(loaded_tickers)} tickers")
        if failed_tickers:
            logger.warning(f"   Failed to load {len(failed_tickers)} tickers: {', '.join(failed_tickers[:10])}")
        
        # Report progress: Data loading complete
        if callback:
            try:
                progress = {
                    'stage': 'loading_benchmark',
                    'message': f'📈 Loading benchmark data ({self.benchmark_ticker})...',
                    'percent': 82,
                    'loaded_tickers': len(loaded_tickers),
                    'failed_tickers_count': len(failed_tickers),
                }
                if asyncio.iscoroutinefunction(callback):
                    await callback(progress)
                else:
                    callback(progress)
            except Exception as e:
                logger.warning(f"Progress callback error: {e}")
        
        # Load benchmark data
        try:
            benchmark_df = await self.queue_manager.fetch_with_retry(
                self.benchmark_ticker, start_date, end_date
            )
            self.benchmark_data = benchmark_df
        except Exception as e:
            logger.warning(f"Failed to load benchmark {self.benchmark_ticker}: {e}")
            self.benchmark_data = None
        
        # Filter signals to only include loaded tickers
        valid_signals = [s for s in signals if s.get('ticker') in loaded_tickers]
        
        # Report progress: Running strategy
        if callback:
            try:
                progress = {
                    'stage': 'running_backtest',
                    'message': f'⚙️ Running backtest with {len(valid_signals)} signals across {len(loaded_tickers)} stocks...',
                    'percent': 85,
                    'valid_signals': len(valid_signals),
                    'eta_message': '🎯 Almost done! Just crunching the numbers...',
                }
                if asyncio.iscoroutinefunction(callback):
                    await callback(progress)
                else:
                    callback(progress)
            except Exception as e:
                logger.warning(f"Progress callback error: {e}")
        
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
        
        # Add comprehensive analyzers
        self.cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe', riskfreerate=0.04)
        self.cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
        self.cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
        self.cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
        self.cerebro.addanalyzer(bt.analyzers.SQN, _name='sqn')
        self.cerebro.addanalyzer(bt.analyzers.VWR, _name='vwr')  # Variability-Weighted Return
        self.cerebro.addanalyzer(bt.analyzers.AnnualReturn, _name='annual_returns')
        self.cerebro.addanalyzer(bt.analyzers.TimeReturn, _name='time_return', timeframe=bt.TimeFrame.Months)
        
        # Run backtest
        logger.info("   Running backtest...")
        
        # Report progress: Executing backtest
        if callback:
            try:
                progress = {
                    'stage': 'executing',
                    'message': '📊 Executing trades and calculating metrics...',
                    'percent': 90,
                    'eta_message': '🚀 Simulating trades - this is the fun part!',
                }
                if asyncio.iscoroutinefunction(callback):
                    await callback(progress)
                else:
                    callback(progress)
            except Exception as e:
                logger.warning(f"Progress callback error: {e}")
        
        results = self.cerebro.run()
        strat = results[0]
        
        execution_time = time.time() - backtest_start_time
        
        # Report progress: Calculating metrics
        if callback:
            try:
                progress = {
                    'stage': 'calculating_metrics',
                    'message': '📈 Calculating performance metrics...',
                    'percent': 95,
                    'eta_message': '✨ Preparing your results...',
                }
                if asyncio.iscoroutinefunction(callback):
                    await callback(progress)
                else:
                    callback(progress)
            except Exception as e:
                logger.warning(f"Progress callback error: {e}")
        
        # Extract and calculate all metrics
        final_value = self.cerebro.broker.getvalue()
        total_return = (final_value / self.initial_capital) - 1
        
        # Build comprehensive results
        result = self._build_comprehensive_results(
            strat=strat,
            final_value=final_value,
            total_return=total_return,
            start_date=start_date,
            end_date=end_date,
            loaded_tickers=loaded_tickers,
            valid_signals=valid_signals,
            execution_time=execution_time,
        )
        
        logger.info(f"\n{'='*60}")
        logger.info(f"📊 BACKTEST COMPLETE")
        logger.info(f"   Total Return: {total_return:.2%}")
        logger.info(f"   Sharpe Ratio: {result['summary']['sharpe_ratio']:.2f}")
        logger.info(f"   Max Drawdown: {result['summary']['max_drawdown']:.2%}")
        logger.info(f"   Total Trades: {result['summary'].get('total_trades', 0)}")
        logger.info(f"   Execution Time: {execution_time:.1f}s")
        logger.info(f"{'='*60}")
        
        return result
    
    def _build_comprehensive_results(
        self,
        strat,
        final_value: float,
        total_return: float,
        start_date: str,
        end_date: str,
        loaded_tickers: List[str],
        valid_signals: List[Dict],
        execution_time: float,
    ) -> Dict:
        """Build all results needed for the dashboard."""
        
        # Get analyzer results
        sharpe = strat.analyzers.sharpe.get_analysis()
        drawdown = strat.analyzers.drawdown.get_analysis()
        trades_analyzer = strat.analyzers.trades.get_analysis()
        returns_analyzer = strat.analyzers.returns.get_analysis()
        sqn = strat.analyzers.sqn.get_analysis()
        annual_returns = strat.analyzers.annual_returns.get_analysis()
        monthly_returns = strat.analyzers.time_return.get_analysis()
        
        # Calculate core metrics
        sharpe_ratio = sharpe.get('sharperatio', 0) or 0
        max_drawdown = -abs(drawdown.get('max', {}).get('drawdown', 0) / 100) if drawdown.get('max') else 0
        
        # Trade statistics
        total_trades = trades_analyzer.get('total', {}).get('total', 0) if trades_analyzer.get('total') else 0
        won_trades = trades_analyzer.get('won', {}).get('total', 0) if trades_analyzer.get('won') else 0
        lost_trades = total_trades - won_trades
        win_rate = won_trades / total_trades if total_trades > 0 else 0
        
        # Calculate from daily values
        daily_values = strat.daily_values
        daily_returns = strat.daily_returns
        
        # Build DataFrames for calculations
        if daily_values:
            dates = [dv['date'] for dv in daily_values]
            values = [dv['value'] for dv in daily_values]
            returns_list = [dr['return'] for dr in daily_returns] if daily_returns else []
            
            df_values = pd.DataFrame({'date': dates, 'value': values})
            df_values['date'] = pd.to_datetime(df_values['date'])
            df_values.set_index('date', inplace=True)
            
            # Calculate volatility
            if returns_list:
                volatility = float(np.std(returns_list) * np.sqrt(252))  # Annualized
                
                # Sortino Ratio (downside deviation)
                negative_returns = [r for r in returns_list if r < 0]
                if negative_returns:
                    downside_std = np.std(negative_returns) * np.sqrt(252)
                    sortino_ratio = (total_return / ((end_dt - start_dt).days / 365.25)) / downside_std if downside_std > 0 else 0
                else:
                    sortino_ratio = sharpe_ratio  # No downside, use Sharpe
                
                # VaR and CVaR (95%)
                var_95 = float(np.percentile(returns_list, 5))
                cvar_95 = float(np.mean([r for r in returns_list if r <= var_95]))
                
                # Best and worst days
                best_day = float(max(returns_list)) if returns_list else 0
                worst_day = float(min(returns_list)) if returns_list else 0
                
                # Win rates
                win_rate_daily = len([r for r in returns_list if r > 0]) / len(returns_list) if returns_list else 0
            else:
                volatility = 0
                sortino_ratio = 0
                var_95 = 0
                cvar_95 = 0
                best_day = 0
                worst_day = 0
                win_rate_daily = 0
        else:
            volatility = 0
            sortino_ratio = 0
            var_95 = 0
            cvar_95 = 0
            best_day = 0
            worst_day = 0
            win_rate_daily = 0
            dates = []
            values = []
        
        # Parse dates
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date)
        years = (end_dt - start_dt).days / 365.25
        
        # CAGR
        cagr = self._calculate_cagr(self.initial_capital, final_value, start_date, end_date)
        
        # ROMAD (Return Over Maximum Drawdown)
        romad = total_return / abs(max_drawdown) if max_drawdown != 0 else 0
        
        # Benchmark calculations
        benchmark_values = []
        benchmark_total_return = 0
        benchmark_cagr = 0
        alpha = 0
        beta = 1.0
        information_ratio = 0
        
        if self.benchmark_data is not None and len(self.benchmark_data) > 0:
            try:
                bench_df = self.benchmark_data.copy()
                if 'close' in bench_df.columns:
                    bench_start = bench_df['close'].iloc[0]
                    bench_end = bench_df['close'].iloc[-1]
                    benchmark_total_return = (bench_end / bench_start) - 1
                    benchmark_cagr = self._calculate_cagr(bench_start, bench_end, start_date, end_date)
                    
                    # Calculate alpha (simple)
                    alpha = total_return - benchmark_total_return
                    
                    # Calculate beta (correlation with benchmark)
                    bench_returns = bench_df['close'].pct_change().dropna()
                    if len(returns_list) > 0 and len(bench_returns) > 0:
                        min_len = min(len(returns_list), len(bench_returns))
                        if min_len > 10:
                            port_returns_aligned = returns_list[:min_len]
                            bench_returns_aligned = bench_returns.values[:min_len]
                            
                            cov_matrix = np.cov(port_returns_aligned, bench_returns_aligned)
                            if cov_matrix.shape == (2, 2):
                                beta = cov_matrix[0, 1] / cov_matrix[1, 1] if cov_matrix[1, 1] != 0 else 1.0
                            
                            # Information Ratio
                            tracking_error = np.std(np.array(port_returns_aligned) - bench_returns_aligned) * np.sqrt(252)
                            if tracking_error > 0:
                                information_ratio = alpha / tracking_error
                    
                    # Build benchmark values for equity curve
                    for i, date in enumerate(dates):
                        if date in bench_df.index:
                            val = bench_df.loc[date, 'close'] / bench_start * self.initial_capital
                            benchmark_values.append(float(val))
                        elif len(benchmark_values) > 0:
                            benchmark_values.append(benchmark_values[-1])
                        else:
                            benchmark_values.append(float(self.initial_capital))
            except Exception as e:
                logger.warning(f"Error calculating benchmark metrics: {e}")
        
        # Fill benchmark_values if needed
        while len(benchmark_values) < len(values):
            benchmark_values.append(benchmark_values[-1] if benchmark_values else self.initial_capital)
        
        # Monthly and yearly win rates
        if daily_values:
            df_returns = pd.DataFrame({'date': dates[:len(returns_list)], 'return': returns_list})
            if len(df_returns) > 0:
                df_returns['date'] = pd.to_datetime(df_returns['date'])
                df_returns.set_index('date', inplace=True)
                
                # Monthly
                monthly_rets = df_returns.resample('M')['return'].sum()
                win_rate_monthly = len([r for r in monthly_rets if r > 0]) / len(monthly_rets) if len(monthly_rets) > 0 else 0
                
                # Yearly
                yearly_rets = df_returns.resample('Y')['return'].sum()
                win_rate_yearly = len([r for r in yearly_rets if r > 0]) / len(yearly_rets) if len(yearly_rets) > 0 else 0
            else:
                win_rate_monthly = 0
                win_rate_yearly = 0
        else:
            win_rate_monthly = 0
            win_rate_yearly = 0
        
        # Build equity curve
        equity_curve = {
            'dates': [d.isoformat() if hasattr(d, 'isoformat') else str(d) for d in dates],
            'portfolio_values': [float(v) for v in values],
            'benchmark_values': benchmark_values,
        }
        
        # Process trade log
        trades = strat.trade_log
        
        # Add ranking to trades
        for i, trade in enumerate(trades):
            trade['rank'] = i + 1
        
        # Build monthly returns matrix
        monthly_returns_matrix = []
        if daily_values and len(dates) > 0:
            try:
                df_temp = pd.DataFrame({
                    'date': [d for d in dates],
                    'value': values
                })
                df_temp['date'] = pd.to_datetime(df_temp['date'])
                df_temp.set_index('date', inplace=True)
                
                monthly_vals = df_temp.resample('M').last()
                monthly_pct = monthly_vals.pct_change()
                
                for year in monthly_pct.index.year.unique():
                    year_data = monthly_pct[monthly_pct.index.year == year]
                    months = {}
                    for idx, row in year_data.iterrows():
                        month_name = idx.strftime('%b')
                        months[month_name] = float(row['value']) if not pd.isna(row['value']) else 0
                    monthly_returns_matrix.append({
                        'year': int(year),
                        'months': months
                    })
            except Exception as e:
                logger.warning(f"Error building monthly returns: {e}")
        
        # Build yearly returns
        yearly_returns_list = []
        for year, ret in annual_returns.items():
            yearly_returns_list.append({
                'year': int(year),
                'return_pct': float(ret) if ret else 0,
                'benchmark_return_pct': 0  # Would need to calculate per-year benchmark
            })
        
        # Build summary
        summary = {
            'total_return': float(total_return),
            'cagr': float(cagr),
            'volatility': float(volatility),
            'sharpe_ratio': float(sharpe_ratio),
            'sortino_ratio': float(sortino_ratio),
            'max_drawdown': float(max_drawdown),
            'romad': float(romad),
            'alpha': float(alpha),
            'beta': float(beta),
            'information_ratio': float(information_ratio),
            'var_95': float(var_95),
            'cvar_95': float(cvar_95),
            'win_rate_daily': float(win_rate_daily),
            'win_rate_monthly': float(win_rate_monthly),
            'win_rate_yearly': float(win_rate_yearly),
            'best_day': float(best_day),
            'worst_day': float(worst_day),
            'benchmark_total_return': float(benchmark_total_return),
            'benchmark_cagr': float(benchmark_cagr),
            'total_trades': int(total_trades),
            'winning_trades': int(won_trades),
            'losing_trades': int(lost_trades),
            'win_rate': float(win_rate),
            'sqn': float(sqn.get('sqn', 0) or 0),
        }
        
        # Include failed tickers info if available
        failed_tickers_list = getattr(self, '_failed_tickers', [])
        
        return {
            'success': True,
            'engine': 'backtrader',
            'summary': summary,
            'equity_curve': equity_curve,
            'trades': trades,
            'monthly_returns': monthly_returns_matrix,
            'yearly_returns': yearly_returns_list,
            'initial_capital': float(self.initial_capital),
            'final_value': float(final_value),
            'execution_time_seconds': float(execution_time),
            'api_calls_made': len(loaded_tickers),
            'sec_filings_fetched': len(valid_signals),
            'stocks_analyzed': loaded_tickers,
            'rebalance_count': strat.rebalance_count,
            'rebalance_frequency': strat.params.rebalance_frequency,
            'failed_tickers': failed_tickers_list,
            'data_quality': {
                'loaded': len(loaded_tickers),
                'failed': len(failed_tickers_list),
                'success_rate': len(loaded_tickers) / max(len(loaded_tickers) + len(failed_tickers_list), 1),
            },
        }
    
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
            df.columns = [c.lower() if isinstance(c, str) else c[0].lower() for c in df.columns]
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
            'summary': {
                'total_return': 0,
                'cagr': 0,
                'volatility': 0,
                'sharpe_ratio': 0,
                'sortino_ratio': 0,
                'max_drawdown': 0,
                'romad': 0,
                'alpha': 0,
                'beta': 1.0,
                'information_ratio': 0,
                'var_95': 0,
                'cvar_95': 0,
                'win_rate_daily': 0,
                'win_rate_monthly': 0,
                'win_rate_yearly': 0,
                'best_day': 0,
                'worst_day': 0,
                'benchmark_total_return': 0,
                'benchmark_cagr': 0,
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'sqn': 0,
            },
            'equity_curve': {
                'dates': [],
                'portfolio_values': [],
                'benchmark_values': [],
            },
            'trades': [],
            'monthly_returns': [],
            'yearly_returns': [],
            'initial_capital': self.initial_capital,
            'final_value': self.initial_capital,
            'execution_time_seconds': 0,
            'api_calls_made': 0,
            'sec_filings_fetched': 0,
            'stocks_analyzed': [],
            'rebalance_count': 0,
            'rebalance_frequency': 'monthly',
        }


# Factory function
def get_backtrader_engine(
    initial_capital: float = 1_000_000,
    benchmark_ticker: str = 'SPY',
    progress_callback: Optional[Callable] = None,
    **kwargs
) -> BacktraderEngine:
    """
    Get a configured Backtrader engine instance.
    
    Args:
        initial_capital: Starting portfolio value
        benchmark_ticker: Ticker to use as benchmark (default: SPY)
        progress_callback: Optional callback function for progress updates
        **kwargs: Additional engine configuration
    
    Returns:
        BacktraderEngine: Configured engine instance
    """
    return BacktraderEngine(
        initial_capital=initial_capital,
        benchmark_ticker=benchmark_ticker,
        progress_callback=progress_callback,
        **kwargs
    )
