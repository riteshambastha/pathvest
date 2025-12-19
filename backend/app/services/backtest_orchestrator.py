"""
Backtest Orchestrator
Integrates SEC data, historical prices, and backtest engine
Supports both Custom Engine and LEAN Engine
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import pandas as pd
from google.cloud import bigquery
import os

from app.services.historical_backtest_engine import HistoricalBacktestEngine
from app.services.lean_adapter import LEANAdapter


class BacktestOrchestrator:
    """
    Orchestrates the full backtesting process:
    1. Fetch SEC filing signals from PostgreSQL
    2. Fetch historical prices for relevant stocks
    3. Run backtest simulation
    4. Return performance metrics
    """
    
    def __init__(self):
        self.bq_client = None
        # Load environment variables from .env file if present
        from dotenv import load_dotenv
        load_dotenv()
        
        if os.getenv('ENABLE_BIGQUERY') == 'True' and os.getenv('GOOGLE_APPLICATION_CREDENTIALS'):
            try:
                self.bq_client = bigquery.Client()
                print("✅ BigQuery client initialized")
            except Exception as e:
                print(f"⚠️  BigQuery initialization failed: {e}")
                self.bq_client = None
    
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
                progress_callback(message, percent, details)
            print(f"📍 [{percent}%] {message}")
        
        try:
            # Step 1: Fetch SEC signals from PostgreSQL
            update_progress("Fetching SEC filing signals...", 10)
            signals = await self.fetch_sec_signals(
                start_date, 
                end_date, 
                selected_institutions,
                strategy_config
            )
            
            if not signals:
                return {
                    'error': 'No signals found for the given criteria',
                    'total_return': 0,
                    'sharpe_ratio': 0,
                    'max_drawdown': 0
                }
            
            update_progress(f"Found {len(signals)} trading signals", 30)
            
            # Step 2: Get unique tickers from signals
            tickers = list(set([s['ticker'] for s in signals]))
            update_progress(f"Fetching historical prices for {len(tickers)} stocks...", 40)
            
            # Step 3: Fetch historical prices (with rate limiting)
            historical_prices = await self.fetch_historical_prices_batch(
                tickers, 
                start_date, 
                end_date,
                lambda ticker, idx, total: update_progress(
                    f"Fetching {ticker} ({idx}/{total})",
                    40 + int((idx/total) * 40),
                    [f"Completed: {ticker}"]
                )
            )
            
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
                results = lean_adapter.run_full_backtest(signals, lean_config)
                
                if results is None or 'error' in results:
                    # LEAN failed, fallback to custom engine
                    print(f"⚠️  LEAN engine failed, falling back to Custom Engine")
                    update_progress("LEAN failed, using Custom Engine...", 85)
                    engine = HistoricalBacktestEngine(initial_capital=strategy_config.get('initial_capital', 100000))
                    results = engine.run_backtest(signals, historical_prices, start_date, end_date)
                    results['engine'] = 'custom (fallback from LEAN)'
                else:
                    print(f"✅ LEAN backtest completed successfully")
                    results['engine'] = 'LEAN'
            
            else:
                # Use Custom Engine (default)
                print(f"📍 Using Custom Engine (PathVest)")
                engine = HistoricalBacktestEngine(initial_capital=strategy_config.get('initial_capital', 100000))
                results = engine.run_backtest(signals, historical_prices, start_date, end_date)
                results['engine'] = 'custom'
            
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
        Fetch SEC filing-based trading signals from PostgreSQL
        
        Signal generation logic:
        - Doubling Down: Institution increases position by 50%+
        - New Position: Institution enters a new position (top holdings)
        """
        
        if not self.bq_client:
            print("⚠️  PostgreSQL not enabled, returning empty signals")
            return []
        
        signals = []
        
        # Query for institutional position changes
        query = f"""
        WITH position_changes AS (
            SELECT 
                h1.ticker,
                h1.cik,
                h1.filing_date,
                h1.shares_held as current_shares,
                h1.market_value as current_value,
                LAG(h1.shares_held) OVER (
                    PARTITION BY h1.ticker, h1.cik 
                    ORDER BY h1.filing_date
                ) as previous_shares,
                LAG(h1.market_value) OVER (
                    PARTITION BY h1.ticker, h1.cik 
                    ORDER BY h1.filing_date
                ) as previous_value
            FROM `{os.getenv('GCP_PROJECT_ID')}.{os.getenv('BIGQUERY_DATASET_SEC')}.institutional_holdings` h1
            WHERE h1.filing_date BETWEEN '{start_date}' AND '{end_date}'
                AND h1.cik IN ({','.join([f"'{cik}'" for cik in selected_institutions])})
        )
        SELECT 
            ticker,
            cik,
            filing_date,
            current_shares,
            previous_shares,
            current_value,
            previous_value,
            CASE 
                WHEN previous_shares IS NULL THEN 'NEW_POSITION'
                WHEN current_shares > previous_shares * 1.5 THEN 'DOUBLING_DOWN'
                WHEN current_shares < previous_shares * 0.5 THEN 'REDUCING'
                ELSE 'HOLDING'
            END as signal_type,
            CASE 
                WHEN previous_shares IS NULL THEN 1.0
                WHEN current_shares > previous_shares THEN (current_shares - previous_shares) / previous_shares
                ELSE 0.0
            END as signal_strength
        FROM position_changes
        WHERE filing_date IS NOT NULL
        ORDER BY filing_date ASC
        """
        
        try:
            print(f"\n🔍 Executing PostgreSQL query...")
            print(f"   Institutions: {selected_institutions}")
            print(f"   Date range: {start_date} to {end_date}")
            # print(f"\n   SQL:\n{query}\n")  # Uncomment to debug SQL
            
            query_job = self.bq_client.query(query)
            results = query_job.result()
            
            for row in results:
                # Only create BUY signals for NEW_POSITION and DOUBLING_DOWN
                if row.signal_type in ['NEW_POSITION', 'DOUBLING_DOWN']:
                    signals.append({
                        'date': row.filing_date.strftime('%Y-%m-%d'),
                        'ticker': row.ticker,
                        'action': 'BUY',
                        'signal_type': row.signal_type,
                        'signal_strength': min(float(row.signal_strength), 1.0),
                        'institution_cik': row.cik,
                        'shares_change': int(row.current_shares - (row.previous_shares or 0))
                    })
                
                # Create SELL signals for REDUCING
                elif row.signal_type == 'REDUCING':
                    signals.append({
                        'date': row.filing_date.strftime('%Y-%m-%d'),
                        'ticker': row.ticker,
                        'action': 'SELL',
                        'signal_type': row.signal_type,
                        'signal_strength': 1.0,
                        'institution_cik': row.cik,
                        'shares_change': int(row.current_shares - row.previous_shares)
                    })
            
            print(f"✅ Found {len(signals)} signals from PostgreSQL")
            return signals
            
        except Exception as e:
            print(f"❌ Error fetching signals from PostgreSQL: {e}")
            return []
    
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
                        progress_callback(ticker, idx, len(tickers))
                    
                    # Rate limiting: Wait 12 seconds between each fetch
                    await asyncio.sleep(12)
                    
                except Exception as e:
                    print(f"   ⚠️  {ticker}: {str(e)[:50]}")
        
        # Fetch all tickers in parallel (but limited by semaphore)
        tasks = [fetch_one_ticker(ticker, idx) for idx, ticker in enumerate(tickers, 1)]
        await asyncio.gather(*tasks)
        
        print(f"✅ Fetched prices for {len(historical_prices)}/{len(tickers)} stocks")
        return historical_prices

