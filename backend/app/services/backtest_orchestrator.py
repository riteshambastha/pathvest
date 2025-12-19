"""
Backtest Orchestrator
Integrates SEC data, historical prices, and backtest engine
Supports both Custom Engine and LEAN Engine
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import pandas as pd
import os

# Import services with error handling
try:
    from app.services.historical_backtest_engine import HistoricalBacktestEngine
except ImportError as e:
    print(f"⚠️ Could not import HistoricalBacktestEngine: {e}")
    HistoricalBacktestEngine = None

try:
    from app.services.sec_edgar_service import SECEdgarService
except ImportError as e:
    print(f"⚠️ Could not import SECEdgarService: {e}")
    SECEdgarService = None

try:
    from app.services.alphavantage_service import AlphaVantageService
except ImportError as e:
    print(f"⚠️ Could not import AlphaVantageService: {e}")
    AlphaVantageService = None

# LEANAdapter is optional
try:
    from app.services.lean_adapter import LEANAdapter
    LEAN_ADAPTER_AVAILABLE = True
except ImportError:
    LEAN_ADAPTER_AVAILABLE = False
    LEANAdapter = None


class BacktestOrchestrator:
    """
    Orchestrates the full backtesting process:
    1. Fetch SEC filing signals from PostgreSQL database
    2. Fetch historical prices for relevant stocks from AlphaVantage
    3. Run backtest simulation
    4. Return performance metrics
    """
    
    def __init__(self):
        # Initialize services
        if SECEdgarService is None or AlphaVantageService is None:
            raise ImportError("Required services (SEC or AlphaVantage) not available")
        
        self.sec_service = SECEdgarService()
        self.alphavantage_service = AlphaVantageService()
        print("✅ Backtest Orchestrator initialized with real data services")
    
    async def run_strategy_backtest(
        self,
        start_date: str,
        end_date: str,
        selected_institutions: List[str],
        strategy_config: Dict,
        progress_callback: Optional[callable] = None
    ) -> Dict:
        """
        Run a complete backtest for a given strategy
        Supports both Custom Engine and LEAN Engine
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            selected_institutions: List of institution CIKs
            strategy_config: Full strategy configuration (includes engine_type)
            progress_callback: Optional callback for progress updates
            
        Returns:
            Dict with backtest results and metrics
        """
        
        # Determine which engine to use
        engine_type = strategy_config.get('engine_type', 'custom')
        
        print(f"\n{'='*60}")
        print(f"🎯 Backtest Engine: {engine_type.upper()}")
        print(f"{'='*60}\n")
        
        def update_progress(message: str, percent: int, details: List[str] = None):
            if progress_callback:
                progress_callback(message, percent, details or [])
            print(f"📍 [{percent}%] {message}")
            if details:
                for detail in details:
                    print(f"    • {detail}")
        
        try:
            # Step 1: Fetch SEC signals from PostgreSQL
            update_progress("Fetching SEC filing signals...", 10, [
                f"Querying {len(selected_institutions)} institutions",
                f"Date range: {start_date} to {end_date}"
            ])
            signals = await self.fetch_sec_signals(
                start_date, 
                end_date, 
                selected_institutions,
                strategy_config
            )
            
            if not signals:
                update_progress("No signals found", 100, [
                    "⚠️ No institutional activity found for selected criteria",
                    "Try: Expand date range or select more institutions"
                ])
                return {
                    'error': 'No signals found for the given criteria',
                    'total_return': 0,
                    'sharpe_ratio': 0,
                    'max_drawdown': 0
                }
            
            update_progress(f"Found {len(signals)} trading signals", 30, [
                f"✅ SEC signals extracted successfully",
                f"Signal types: BUY, SELL, DOUBLING_DOWN"
            ])
            
            # Step 2: Get unique tickers from signals
            tickers = list(set([s['ticker'] for s in signals]))
            update_progress(f"Fetching historical prices for {len(tickers)} stocks...", 40, [
                f"Using AlphaVantage API (free tier: 5 calls/min)",
                f"Estimated time: ~{len(tickers) * 12 / 60:.1f} minutes",
                "⏱️ Please wait while we fetch real market data..."
            ])
            
            # Step 3: Fetch historical prices (with rate limiting)
            prices_fetched = []
            prices_failed = []
            
            def price_progress_callback(ticker, idx, total):
                status = "✅" if ticker in historical_prices else "⚠️"
                if ticker in historical_prices:
                    prices_fetched.append(ticker)
                else:
                    prices_failed.append(ticker)
                    
                update_progress(
                    f"Fetching prices: {idx}/{total} ({status} {ticker})",
                    40 + int((idx/total) * 40),
                    [
                        f"Completed: {len(prices_fetched)} stocks",
                        f"Failed: {len(prices_failed)} stocks",
                        f"Current: {ticker}"
                    ] + ([f"⚠️ Check ALPHAVANTAGE_API_KEY if many failures"] if len(prices_failed) > 3 else [])
                )
            
            historical_prices = await self.fetch_historical_prices_batch(
                tickers, 
                start_date, 
                end_date,
                price_progress_callback
            )
            
            if not historical_prices:
                update_progress("Price fetch failed", 100, [
                    "❌ No price data fetched",
                    "⚠️ Check: ALPHAVANTAGE_API_KEY environment variable",
                    "⚠️ Check: AlphaVantage API rate limits",
                    f"Attempted to fetch: {len(tickers)} tickers"
                ])
                return {
                    'error': 'Failed to fetch historical prices',
                    'total_return': 0,
                    'sharpe_ratio': 0,
                    'max_drawdown': 0
                }
            
            update_progress(f"Price data ready: {len(historical_prices)}/{len(tickers)} stocks", 80, [
                f"✅ Successfully fetched: {len(prices_fetched)} stocks",
                f"⚠️ Failed: {len(prices_failed)} stocks" if prices_failed else "✅ All stocks fetched successfully",
                f"Moving to portfolio simulation..."
            ])
            
            update_progress("Running portfolio simulation...", 85)
            
            # Step 4: Run backtest with selected engine
            if engine_type == 'lean':
                # Use LEAN Engine
                print(f"📍 Using LEAN Engine (QuantConnect)")
                lean_adapter = LEANAdapter()
                
                # Prepare LEAN-compatible config
                lean_config = {
                    'start_date': start_date,
                    'end_date': end_date,
                    'initial_capital': strategy_config.get('initial_capital', 100000)
                }
                
                # Run LEAN backtest
                lean_results = lean_adapter.run_full_backtest(signals, lean_config)
                
                if lean_results is None or 'error' in lean_results:
                    # LEAN failed, fallback to custom engine
                    print(f"⚠️  LEAN engine failed, falling back to Custom Engine")
                    update_progress("LEAN failed, using Custom Engine...", 85)
                    engine = HistoricalBacktestEngine(initial_capital=strategy_config.get('initial_capital', 100000))
                    raw_results = engine.run_backtest(signals, historical_prices, start_date, end_date)
                    
                    # Wrap metrics under 'summary' key
                    results = {
                        'engine': 'custom (fallback from LEAN)',
                        'summary': {k: v for k, v in raw_results.items() if k not in ['portfolio_history', 'dates', 'trades', 'initial_capital', 'final_value', 'total_trades']},
                        'equity_curve': {
                            'dates': raw_results.get('dates', []),
                            'portfolio_values': raw_results.get('portfolio_history', []),
                            'benchmark_values': []
                        },
                        'trades': raw_results.get('trades', []),
                        'initial_capital': raw_results.get('initial_capital', 100000),
                        'final_value': raw_results.get('final_value', 100000),
                        'execution_time_seconds': 0,
                        'api_calls_made': len(tickers) * 2,
                        'sec_filings_fetched': len(signals),
                        'stocks_analyzed': tickers
                    }
                else:
                    print(f"✅ LEAN backtest completed successfully")
                    results = lean_results
                    results['engine'] = 'LEAN'
            
            else:
                # Use Custom Engine (default)
                print(f"📍 Using Custom Engine (PathVest)")
                engine = HistoricalBacktestEngine(initial_capital=strategy_config.get('initial_capital', 100000))
                raw_results = engine.run_backtest(signals, historical_prices, start_date, end_date)
                
                # Wrap metrics under 'summary' key for API schema compatibility
                results = {
                    'engine': 'custom',
                    'summary': {k: v for k, v in raw_results.items() if k not in ['portfolio_history', 'dates', 'trades', 'initial_capital', 'final_value', 'total_trades']},
                    'equity_curve': {
                        'dates': raw_results.get('dates', []),
                        'portfolio_values': raw_results.get('portfolio_history', []),
                        'benchmark_values': []  # Benchmark not implemented yet
                    },
                    'trades': raw_results.get('trades', []),
                    'initial_capital': raw_results.get('initial_capital', 100000),
                    'final_value': raw_results.get('final_value', 100000),
                    'execution_time_seconds': 0,  # Will be calculated by API
                    'api_calls_made': len(tickers) * 2,  # Rough estimate
                    'sec_filings_fetched': len(signals),
                    'stocks_analyzed': tickers
                }
            
            update_progress("Backtest complete!", 100)
            
            # Step 5: Add additional context
            results['signals'] = signals
            results['tickers'] = tickers
            results['institutions'] = selected_institutions
            results['start_date'] = start_date
            results['end_date'] = end_date
            
            return results
            
        except Exception as e:
            print(f"❌ Backtest error: {e}")
            import traceback
            traceback.print_exc()
            return {
                'error': str(e),
                'total_return': 0,
                'sharpe_ratio': 0,
                'max_drawdown': 0
            }
    
    async def fetch_sec_signals(
        self,
        start_date: str,
        end_date: str,
        selected_institutions: List[str],
        strategy_config: Dict
    ) -> List[Dict]:
        """
        Fetch SEC filing-based trading signals from PostgreSQL database
        
        Signal generation logic:
        - Doubling Down: Institution increases position by 50%+
        - New Position: Institution enters a new position (top holdings)
        """
        from app.services.strategy_db import SessionLocal
        from sqlalchemy import text
        
        if not selected_institutions:
            print("⚠️  No institutions selected, returning empty signals")
            return []
        
        signals = []
        db = SessionLocal()
        
        try:
            print(f"\n🔍 Fetching SEC signals from database...")
            print(f"   Institutions: {selected_institutions[:3]}... ({len(selected_institutions)} total)")
            print(f"   Date range: {start_date} to {end_date}")
            
            # Query holdings from database for selected institutions
            query = text("""
                SELECT 
                    h.ticker_symbol as ticker,
                    h.cusip,
                    f.cik,
                    f.period_of_report as filing_date,
                    h.value as market_value,
                    h.shares as shares_held
                FROM holdings h
                JOIN filings f ON h.filing_id = f.id
                JOIN institutions i ON f.institution_id = i.id
                WHERE i.cik = ANY(:ciks)
                    AND f.period_of_report >= :start_date
                    AND f.period_of_report <= :end_date
                    AND h.ticker_symbol IS NOT NULL
                    AND h.ticker_symbol != ''
                ORDER BY f.period_of_report, h.value DESC
            """)
            
            result = db.execute(query, {
                "ciks": selected_institutions,
                "start_date": start_date,
                "end_date": end_date
            })
            
            # Group holdings by ticker and cik to detect position changes
            holdings_by_position = {}
            for row in result:
                key = (row.ticker, row.cik)
                if key not in holdings_by_position:
                    holdings_by_position[key] = []
                holdings_by_position[key].append({
                    'date': row.filing_date.strftime('%Y-%m-%d') if hasattr(row.filing_date, 'strftime') else str(row.filing_date),
                    'ticker': row.ticker,
                    'cik': row.cik,
                    'shares': float(row.shares_held or 0),
                    'value': float(row.market_value or 0)
                })
            
            # Analyze position changes to generate signals
            for (ticker, cik), holdings in holdings_by_position.items():
                holdings = sorted(holdings, key=lambda x: x['date'])
                
                for i in range(len(holdings)):
                    current = holdings[i]
                    
                    if i == 0:
                        # First filing - new position
                        if current['shares'] > 0:
                            signals.append({
                                'date': current['date'],
                                'ticker': ticker,
                                'action': 'BUY',
                                'signal_type': 'NEW_POSITION',
                                'signal_strength': 1.0,
                                'institution_cik': cik,
                                'shares_change': int(current['shares'])
                            })
                    else:
                        previous = holdings[i-1]
                        
                        if previous['shares'] > 0:
                            change_pct = (current['shares'] - previous['shares']) / previous['shares']
                            
                            # Doubling down - increased position by 50%+
                            if change_pct >= 0.5:
                                signals.append({
                                    'date': current['date'],
                                    'ticker': ticker,
                                    'action': 'BUY',
                                    'signal_type': 'DOUBLING_DOWN',
                                    'signal_strength': min(change_pct, 1.0),
                                    'institution_cik': cik,
                                    'shares_change': int(current['shares'] - previous['shares'])
                                })
                            # Reducing - decreased position by 50%+
                            elif change_pct <= -0.5:
                                signals.append({
                                    'date': current['date'],
                                    'ticker': ticker,
                                    'action': 'SELL',
                                    'signal_type': 'REDUCING',
                                    'signal_strength': min(abs(change_pct), 1.0),
                                    'institution_cik': cik,
                                    'shares_change': int(current['shares'] - previous['shares'])
                                })
            
            print(f"✅ Found {len(signals)} trading signals from {len(holdings_by_position)} positions")
            
        except Exception as e:
            print(f"❌ Error fetching SEC signals: {e}")
            import traceback
            traceback.print_exc()
        finally:
            db.close()
        
        return signals
    
    async def fetch_historical_prices_batch(
        self,
        tickers: List[str],
        start_date: str,
        end_date: str,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, pd.DataFrame]:
        """
        Fetch historical prices for multiple tickers with PARALLEL processing
        Uses semaphore to respect AlphaVantage rate limit (5 calls/min)
        
        Improvements:
        - Parallel fetching (5 stocks at once)
        - Much faster than sequential
        - Respects API rate limits
        """
        
        from .historical_backtest_engine import HistoricalBacktestEngine
        import asyncio
        
        engine = HistoricalBacktestEngine()
        historical_prices = {}
        
        # Semaphore to limit concurrent requests (5 per minute = 5 concurrent)
        semaphore = asyncio.Semaphore(5)
        
        async def fetch_one_ticker(ticker, idx):
            """Fetch a single ticker with semaphore"""
            async with semaphore:
                try:
                    df = await engine.fetch_historical_prices(ticker, start_date, end_date)
                    if not df.empty:
                        historical_prices[ticker] = df
                        print(f"   ✅ {ticker}: {len(df)} days")
                        
                        if progress_callback:
                            progress_callback(
                                ticker, 
                                idx, 
                                len(tickers)
                            )
                    else:
                        print(f"   ⚠️  {ticker}: No data returned")
                        if progress_callback:
                            progress_callback(
                                ticker, 
                                idx, 
                                len(tickers)
                            )
                    
                    # Rate limiting: Wait 12 seconds between each fetch (5 calls/min)
                    await asyncio.sleep(12)
                    
                except Exception as e:
                    error_msg = str(e)[:100]
                    print(f"   ❌ {ticker}: {error_msg}")
                    
                    # Check if it's an API key error
                    if 'API' in error_msg.upper() or 'KEY' in error_msg.upper() or '401' in error_msg or '403' in error_msg:
                        print(f"   ⚠️  ALPHAVANTAGE_API_KEY may be invalid or missing!")
                    
                    if progress_callback:
                        progress_callback(
                            ticker, 
                            idx, 
                            len(tickers)
                        )
        
        # Fetch all tickers in parallel (but limited by semaphore)
        tasks = [fetch_one_ticker(ticker, idx) for idx, ticker in enumerate(tickers, 1)]
        await asyncio.gather(*tasks)
        
        print(f"✅ Fetched prices for {len(historical_prices)}/{len(tickers)} stocks")
        return historical_prices

