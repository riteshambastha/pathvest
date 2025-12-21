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
            print(f"🔍 DEBUG: About to fetch SEC signals")
            print(f"🔍 DEBUG: selected_institutions = {selected_institutions}")
            print(f"🔍 DEBUG: selected_institutions type = {type(selected_institutions)}")
            print(f"🔍 DEBUG: len(selected_institutions) = {len(selected_institutions) if selected_institutions else 0}")

            institutions_msg = f"{len(selected_institutions)} institutions selected" if selected_institutions else "❌ NO INSTITUTIONS SELECTED - This will cause backtest to fail!"
            update_progress("Analyzing institutional holdings from SEC data...", 10, [
                institutions_msg,
                f"Date range: {start_date} to {end_date}",
                f"CIKs: {', '.join(selected_institutions[:3]) + ('...' if len(selected_institutions or []) > 3 else '') if selected_institutions else 'NONE'}",
                "📊 Scanning 13F filings for buy/sell signals"
            ])
            signals = await self.fetch_sec_signals(
                start_date, 
                end_date, 
                selected_institutions,
                strategy_config
            )

            print(f"🔍 DEBUG: fetch_sec_signals returned {len(signals) if signals else 0} signals")

            # Log signal summary for debugging
            if signals:
                tickers_found = set(s.get('ticker') for s in signals)
                institutions_found = set(s.get('institution_cik') for s in signals)
                print(f"🔍 DEBUG: Signals from {len(institutions_found)} institutions, {len(tickers_found)} tickers")
                print(f"🔍 DEBUG: Sample signal: {signals[0] if signals else 'None'}")
            
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
            
            if len(signals) > 0:
                update_progress(f"✅ Found {len(signals)} trading signals from SEC data!", 30, [
                    f"📈 Signals ready for backtesting",
                    f"Date range covers institutional activity",
                    f"Next: Fetching historical stock prices"
                ])
            else:
                update_progress("❌ No trading signals found in SEC data", 30, [
                    f"⚠️ No institutional activity detected",
                    f"Try: Expand date range or select more institutions",
                    f"Check: Are institutions selected in Step 2?"
                ])
            
            # Step 2: Get unique CUSIPs from signals (use CUSIP as ticker for now)
            cusips = list(set([s['cusip'] for s in signals]))  # cusip field contains CUSIP
            print(f"🔍 Found {len(cusips)} unique CUSIPs in signals: {cusips[:5]}...")

            # Comprehensive CUSIP to ticker mapping for major stocks
            # This covers S&P 500 and popular institutional holdings
            cusip_to_ticker_map = {
                # Tech Giants (from actual database holdings)
                '69608A108': 'PLTR',   # Palantir Technologies (top holding)
                '67066G104': 'NVDA',   # NVIDIA
                '770700102': 'HOOD',   # Robinhood Markets
                '670100205': 'NVO',    # Novo-Nordisk
                '037833100': 'AAPL',   # Apple
                '594918104': 'MSFT',   # Microsoft
                '02079K305': 'GOOGL',  # Alphabet Class A
                '02079K107': 'GOOG',   # Alphabet Class C
                '023135106': 'AMZN',   # Amazon
                '30303M102': 'META',   # Meta Platforms
                '88160R101': 'TSLA',   # Tesla
                # Major Tech
                '46625H100': 'JPM',    # JPMorgan Chase
                '172967424': 'C',      # Citigroup
                '060505104': 'BAC',    # Bank of America
                '931142103': 'WMT',    # Walmart
                '713448108': 'PEP',    # PepsiCo
                '191216100': 'KO',     # Coca-Cola
                '78378X107': 'SPY',    # SPDR S&P 500 ETF
                '464287465': 'QQQ',    # Invesco QQQ Trust
                '922908363': 'VTI',    # Vanguard Total Stock
                # More Tech
                '001055102': 'ACN',    # Accenture
                '87612E106': 'TXN',    # Texas Instruments
                '742718109': 'QCOM',   # Qualcomm
                '571903202': 'MCD',    # McDonald's
                '459200101': 'IBM',    # IBM
                '92343E102': 'VZ',     # Verizon
                '218352102': 'CMG',    # Chipotle
                '770700102': 'SE',     # Sea Limited
                '85208M102': 'T',      # AT&T
                # Financial
                '38141G104': 'GS',     # Goldman Sachs
                '617446448': 'MS',     # Morgan Stanley
                '902973304': 'USB',    # US Bancorp
                '06738E204': 'BRK.B',  # Berkshire Hathaway B
                '742935100': 'TMO',    # Thermo Fisher
                '478160104': 'JNJ',    # Johnson & Johnson
                '91324P102': 'UNH',    # UnitedHealth
                '72919P200': 'LLY',    # Eli Lilly
                '084670702': 'BLK',    # BlackRock
                # Consumer
                '25179M103': 'DHR',    # Danaher
                '464288570': 'XOM',    # Exxon Mobil
                '20825C104': 'COP',    # ConocoPhillips
                '126650100': 'CVX',    # Chevron
                # Software/Cloud
                '79466L302': 'CRM',    # Salesforce
                '22160K105': 'COST',   # Costco
                '88579Y101': 'MMM',    # 3M
                '30231G102': 'XOM',    # Exxon
                '09247X101': 'BLK',    # BlackRock
                '254687106': 'DIS',    # Disney
                '580135101': 'MCD',    # McDonalds
                '460146103': 'INTC',   # Intel
                '67103H107': 'ORCL',   # Oracle
                '02313510': 'AMGN',    # Amgen
                '88025U109': 'TXG',    # 10X Genomics
                '282914100': 'EGHT',   # 8x8 Inc
                '002121101': 'ATEN',   # A10 Networks
            }
            
            # Try to extract ticker from company name for common patterns
            def infer_ticker_from_name(name: str) -> str:
                """Try to infer ticker symbol from company name"""
                if not name:
                    return None
                name_upper = name.upper()
                # Common name to ticker mappings
                name_patterns = {
                    'APPLE': 'AAPL', 'MICROSOFT': 'MSFT', 'AMAZON': 'AMZN',
                    'GOOGLE': 'GOOGL', 'ALPHABET': 'GOOGL', 'META': 'META',
                    'FACEBOOK': 'META', 'NVIDIA': 'NVDA', 'TESLA': 'TSLA',
                    'JPMORGAN': 'JPM', 'BANK OF AMERICA': 'BAC', 'WALMART': 'WMT',
                    'BERKSHIRE': 'BRK.B', 'UNITEDHEALTH': 'UNH', 'JOHNSON': 'JNJ',
                    'VISA': 'V', 'MASTERCARD': 'MA', 'PROCTER': 'PG',
                    'HOME DEPOT': 'HD', 'CHEVRON': 'CVX', 'EXXON': 'XOM',
                    'PFIZER': 'PFE', 'ABBVIE': 'ABBV', 'COCA-COLA': 'KO', 'COKE': 'KO',
                    'PEPSICO': 'PEP', 'DISNEY': 'DIS', 'NETFLIX': 'NFLX',
                    'ADOBE': 'ADBE', 'SALESFORCE': 'CRM', 'INTEL': 'INTC',
                    'CISCO': 'CSCO', 'ORACLE': 'ORCL', 'IBM': 'IBM',
                    'VERIZON': 'VZ', 'AT&T': 'T', 'T-MOBILE': 'TMUS',
                    'NVIDIA CORP': 'NVDA', 'ADVANCED MICRO': 'AMD',
                }
                for pattern, ticker in name_patterns.items():
                    if pattern in name_upper:
                        return ticker
                return None

            # Map CUSIPs to tickers with better fallback
            mapped_tickers = []
            unmapped_cusips = []
            for i, cusip in enumerate(cusips):
                if cusip in cusip_to_ticker_map:
                    ticker = cusip_to_ticker_map[cusip]
                else:
                    # Try to find the company name from signals
                    company_name = None
                    for s in signals:
                        if s.get('cusip') == cusip and s.get('name'):
                            company_name = s['name']
                            break
                    
                    inferred = infer_ticker_from_name(company_name) if company_name else None
                    if inferred:
                        ticker = inferred
                        print(f"✅ Inferred ticker from name: {company_name} -> {ticker}")
                    else:
                        # Skip unmapped CUSIPs for price fetching
                        unmapped_cusips.append((cusip, company_name))
                        ticker = None
                        
                if ticker:
                    mapped_tickers.append(ticker)
                    if i < 10:
                        print(f"🔍 Mapped {cusip} -> {ticker}")
            
            if unmapped_cusips:
                print(f"⚠️ {len(unmapped_cusips)} CUSIPs could not be mapped to tickers (skipped):")
                for cusip, name in unmapped_cusips[:5]:
                    print(f"   - {cusip}: {name or 'Unknown'}")

            # Build CUSIP to ticker lookup (only for successfully mapped)
            cusip_to_ticker_lookup = {}
            for i, cusip in enumerate(cusips):
                if cusip in cusip_to_ticker_map:
                    cusip_to_ticker_lookup[cusip] = cusip_to_ticker_map[cusip]
                else:
                    # Check if we inferred a ticker for this CUSIP
                    for s in signals:
                        if s.get('cusip') == cusip and s.get('name'):
                            inferred = infer_ticker_from_name(s['name'])
                            if inferred:
                                cusip_to_ticker_lookup[cusip] = inferred
                            break
            
            # Update signals with actual tickers (only if mapped)
            for signal in signals:
                if signal['cusip'] in cusip_to_ticker_lookup:
                    signal['ticker'] = cusip_to_ticker_lookup[signal['cusip']]
                else:
                    signal['ticker'] = None  # Mark as unmapped
            
            # Filter out signals without valid tickers and get unique tickers
            valid_signals = [s for s in signals if s.get('ticker')]
            tickers = list(set([s['ticker'] for s in valid_signals]))
            
            print(f"📊 {len(valid_signals)}/{len(signals)} signals have mappable tickers")
            print(f"📊 Unique tickers to fetch: {tickers[:10]}{'...' if len(tickers) > 10 else ''}")
            print(f"📊 Successfully processed {len(signals)} signals for {len(tickers)} tickers: {tickers[:5]}...")
            if len(tickers) > 0:
                update_progress(f"📊 Fetching real market data for {len(tickers)} stocks...", 40, [
                    f"Using AlphaVantage API (5 calls/minute limit)",
                    f"Stocks: {', '.join(tickers[:5])}{'...' if len(tickers) > 5 else ''}",
                    f"Estimated: {len(tickers) * 12 // 60}min {len(tickers) * 12 % 60}s",
                    "💰 Real prices ensure accurate backtest results"
                ])
            else:
                update_progress("❌ No stocks to analyze - no signals generated", 40, [
                    f"⚠️ Cannot fetch prices without trading signals",
                    f"Go back to Step 2 and select institutions",
                    f"This usually means SEC data query failed"
            ])
            
            # Step 3: Fetch historical prices (with rate limiting)
            prices_fetched = []
            prices_failed = []
            
            def price_progress_callback(ticker, idx, total, success=True):
                status = "✅" if success else "⚠️"
                if success:
                    prices_fetched.append(ticker)
                else:
                    prices_failed.append(ticker)
                    
                progress_percent = 40 + int((idx/total) * 40)

                update_progress(
                    f"📈 Market Data: {idx}/{total} stocks processed",
                    progress_percent,
                    [
                        f"✅ Completed: {len(prices_fetched)} stocks",
                        f"❌ Failed: {len(prices_failed)} stocks",
                        f"🎯 Current: {ticker} ({status})",
                        f"⏱️ Progress: {progress_percent}% complete"
                    ] + ([f"⚠️ Check ALPHAVANTAGE_API_KEY if many failures"] if len(prices_failed) > 3 else [])
                )
            
            historical_prices = await self.fetch_historical_prices_batch(
                tickers, 
                start_date, 
                end_date,
                price_progress_callback
            )
            
            if not historical_prices:
                print("❌ No price data available - AlphaVantage API key required")
                update_progress("Price data unavailable", 100, [
                    "❌ No price data fetched",
                    "⚠️ ALPHAVANTAGE_API_KEY environment variable required",
                    "📋 Get your free API key from: https://www.alphavantage.co/support/#api-key",
                    f"Attempted to fetch: {len(tickers)} tickers"
                ])
                # Even on API error, preserve signal information so user knows signals were found
                return {
                    'error': 'AlphaVantage API key required for real price data. Signals were generated but price data is unavailable.',
                    'total_return': 0,
                    'sharpe_ratio': 0,
                    'max_drawdown': 0,
                    'sec_filings_fetched': len(signals),  # Preserve signal count
                    'stocks_analyzed': tickers,  # Preserve tickers
                    'signals': signals  # Preserve the actual signals
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
                    
                    # Extract exit configuration
                    exit_rules = strategy_config.get('exit_rules', {})
                    exit_config = {
                        'enable_stop_loss': True,
                        'enable_take_profit': exit_rules.get('take_profit_enabled', True),
                        'enable_trailing_stop': exit_rules.get('trailing_stop_enabled', True),
                        'stop_loss_pct': exit_rules.get('trailing_stop_pct', 0.10),
                        'take_profit_pct': exit_rules.get('take_profit_pct', 0.30),
                        'trailing_stop_pct': exit_rules.get('trailing_stop_pct', 0.15)
                    }
                    
                    engine = HistoricalBacktestEngine(
                        initial_capital=strategy_config.get('initial_capital', 100000),
                        exit_config=exit_config
                    )
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
                print(f"🔍 Signals type: {type(signals)}, length: {len(signals) if signals else 0}")
                print(f"🔍 Historical prices type: {type(historical_prices)}")
                if historical_prices:
                    sample_ticker = list(historical_prices.keys())[0]
                    print(f"🔍 Sample price data for {sample_ticker}: {type(historical_prices[sample_ticker])}")

                # Extract exit configuration from strategy
                exit_rules = strategy_config.get('exit_rules', {})
                exit_config = {
                    'enable_stop_loss': exit_rules.get('trailing_stop_enabled', True),  # Use trailing stop as stop-loss toggle
                    'enable_take_profit': exit_rules.get('take_profit_enabled', True),
                    'enable_trailing_stop': exit_rules.get('trailing_stop_enabled', True),
                    'stop_loss_pct': exit_rules.get('trailing_stop_pct', 0.10),  # Default 10%
                    'take_profit_pct': exit_rules.get('take_profit_pct', 0.30),  # Default 30%
                    'trailing_stop_pct': exit_rules.get('trailing_stop_pct', 0.15)  # Default 15%
                }
                print(f"🛑 Exit config: Stop-Loss={exit_config['stop_loss_pct']*100:.0f}% | Take-Profit={exit_config['take_profit_pct']*100:.0f}% | Trailing-Stop={exit_config['trailing_stop_pct']*100:.0f}%")

                # Extract rebalancing configuration from strategy
                risk_management = strategy_config.get('risk_management', {})
                heartbeat = strategy_config.get('heartbeat', {})
                rebalance_frequency = heartbeat.get('rebalance_frequency') or risk_management.get('rebalancing_frequency', 'monthly')
                rebalance_config = {
                    'frequency': rebalance_frequency,
                    'drift_threshold': risk_management.get('drift_threshold', 0.05),  # 5% drift threshold
                    'target_weight': 0.05,  # Fixed 5% per SRS
                    'min_positions': strategy_config.get('min_positions', 5),
                    'max_positions': strategy_config.get('max_positions', 20)
                }
                print(f"⚖️ Rebalance config: Frequency={rebalance_config['frequency'].upper()} | Drift={rebalance_config['drift_threshold']*100:.0f}%")

                engine = HistoricalBacktestEngine(
                    initial_capital=strategy_config.get('initial_capital', 100000),
                    exit_config=exit_config,
                    rebalance_config=rebalance_config
                )
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

            # Debug: Log what we're returning
            print(f"🔍 Orchestrator returning results:")
            print(f"   sec_filings_fetched: {results.get('sec_filings_fetched', 'MISSING')}")
            print(f"   signals count: {len(signals)}")
            print(f"   results keys: {list(results.keys())}")
            
            return results
            
        except Exception as e:
            print(f"❌ Backtest error: {e}")
            import traceback
            traceback.print_exc()
            # Even on error, preserve the signal count so user knows signals were found
            return {
                'error': str(e),
                'total_return': 0,
                'sharpe_ratio': 0,
                'max_drawdown': 0,
                'sec_filings_fetched': len(signals),  # Preserve signal count
                'stocks_analyzed': tickers,
                'signals': signals  # Include the signals themselves
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
            print(f"❌ ERROR: selected_institutions is empty or None: {selected_institutions}")
            return []

        if not isinstance(selected_institutions, list):
            print(f"❌ ERROR: selected_institutions is not a list: {type(selected_institutions)}")
            return []

        # Validate institution format (should be CIK strings)
        invalid_institutions = [inst for inst in selected_institutions if not isinstance(inst, str) or not inst.strip()]
        if invalid_institutions:
            print(f"⚠️  WARNING: Found invalid institution identifiers: {invalid_institutions}")

        valid_institutions = [inst.strip() for inst in selected_institutions if isinstance(inst, str) and inst.strip()]
        if len(valid_institutions) != len(selected_institutions):
            print(f"⚠️  Filtered institutions: {len(selected_institutions)} -> {len(valid_institutions)}")
            selected_institutions = valid_institutions
        
        # Normalize CIKs: Remove leading zeros to match database format
        # Frontend sends '0001037389', database has '1037389'
        normalized_ciks = [cik.lstrip('0') or '0' for cik in selected_institutions]
        print(f"🔍 Normalized CIKs: {selected_institutions} -> {normalized_ciks}")
        selected_institutions = normalized_ciks
        
        signals = []
        db = SessionLocal()
        
        try:
            print(f"\n🔍 Fetching SEC signals from database...")
            print(f"   Institutions: {selected_institutions[:3]}... ({len(selected_institutions)} total)")
            print(f"   Date range: {start_date} to {end_date}")
            
            # Query holdings from database for selected institutions
            # Using CUSIP instead of ticker since ticker data is missing
            query = text("""
                SELECT 
                    h.cusip as ticker,  -- Using CUSIP as identifier since ticker is NULL
                    h.cusip,
                    i.cik,
                    f.filing_date as filing_date,
                    h.value as market_value,
                    h.shares_or_prn_amt as shares_held,
                    h.name_of_issuer
                FROM holdings h
                JOIN filings f ON h.filing_id = f.id
                JOIN institutions i ON f.institution_id = i.id
                WHERE i.cik = ANY(:ciks)
                    AND f.filing_date >= :start_date
                    AND f.filing_date <= :end_date
                    AND h.cusip IS NOT NULL
                    AND h.cusip != ''
                ORDER BY f.filing_date, h.value DESC
            """)
            
            print(f"🔍 DEBUG: Executing database query with params:")
            print(f"   ciks: {selected_institutions}")
            print(f"   start_date: {start_date}")
            print(f"   end_date: {end_date}")
            
            result = db.execute(query, {
                "ciks": selected_institutions,
                "start_date": start_date,
                "end_date": end_date
            })
            
            rows = result.fetchall()
            print(f"🔍 DEBUG: Database query returned {len(rows)} rows")

            if len(rows) == 0:
                print("⚠️  WARNING: No holdings data found in database!")
                print("   Possible issues:")
                print("   - SEC data not loaded into database")
                print("   - Date range too narrow")
                print("   - Institution CIKs not matching database records")
                return []

            # Group holdings by ticker and cik to detect position changes
            holdings_by_position = {}

            try:
                print(f"🔍 Processing {len(rows)} rows into position groups...")
                print(f"🔍 Result type: {type(result)}")
                print(f"🔍 First row type: {type(rows[0]) if rows else 'No rows'}")

                if rows:
                    first_row = rows[0]
                    print(f"🔍 First row sample: {first_row}")
                    print(f"🔍 Row has keys method: {hasattr(first_row, 'keys')}")

                for i, row in enumerate(rows):
                    try:
                        # Handle both tuple and Row objects
                        if hasattr(row, 'keys'):
                            # SQLAlchemy Row object
                            ticker = row.ticker
                            cik = row.cik
                            filing_date = row.filing_date
                            shares_held = row.shares_held
                            market_value = row.market_value
                            name = getattr(row, 'name_of_issuer', None)
                        else:
                            # Tuple format: (ticker, cusip, cik, filing_date, market_value, shares_held, name_of_issuer)
                            ticker = row[0]  # ticker (CUSIP)
                            cik = row[2]     # cik
                            filing_date = row[3]  # filing_date
                            market_value = row[4] # market_value
                            shares_held = row[5]  # shares_held
                            name = row[6] if len(row) > 6 else None

                        key = (ticker, cik)
                        if key not in holdings_by_position:
                            holdings_by_position[key] = []

                        holdings_by_position[key].append({
                            'date': filing_date.strftime('%Y-%m-%d') if hasattr(filing_date, 'strftime') else str(filing_date),
                            'ticker': ticker,
                            'cik': cik,
                            'shares': float(shares_held or 0),
                            'value': float(market_value or 0),
                            'name': name
                        })

                        if i < 3:
                            print(f"🔍 Processed row {i+1}: {key} - {shares_held} shares on {filing_date}")

                        if i >= 100:  # Limit processing for debug
                            print(f"🔍 Stopping after 100 rows for debug...")
                            break

                    except Exception as e:
                        print(f"❌ Error processing row {i}: {e}")
                        print(f"❌ Row data: {row}")
                        break

            except Exception as e:
                print(f"❌ Error in row processing loop: {e}")
                import traceback
                traceback.print_exc()

            print(f"🔍 Created {len(holdings_by_position)} position groups")
            
            # Analyze position changes to generate signals
            print(f"🔍 Analyzing {len(holdings_by_position)} position groups for signals...")

            signals_generated = 0
            total_positions_checked = 0

            for (cusip, cik), holdings in holdings_by_position.items():
                holdings = sorted(holdings, key=lambda x: x['date'])
                total_positions_checked += 1

                # Debug: show first few positions
                if total_positions_checked <= 3:
                    print(f"🔍 Position {total_positions_checked}: {cusip} (CIK: {cik}) - {len(holdings)} filings")
                    for i, h in enumerate(holdings[:2]):
                        print(f"   Filing {i+1}: {h['date']} - {h['shares']} shares, ${h['value']:,.0f} value")

                # Skip if no holdings data
                if not holdings:
                    continue

                # Check if shares are positive
                positive_shares = [h for h in holdings if h['shares'] > 0]
                if not positive_shares:
                    if total_positions_checked <= 3:
                        print(f"   ⚠️  No positive share holdings for {cusip}")
                    continue
                
                # Get company name from any holding record
                company_name = next((h.get('name') for h in holdings if h.get('name')), None)
                
                for i in range(len(holdings)):
                    current = holdings[i]
                    
                    if i == 0:
                        # First filing - new position
                        if current['shares'] > 0:
                            signals.append({
                                'date': current['date'],
                                'ticker': cusip,  # Will be mapped to ticker later
                                'cusip': cusip,
                                'name': company_name,  # Include company name for ticker inference
                                'action': 'BUY',
                                'signal_type': 'NEW_POSITION',
                                'signal_strength': 1.0,
                                'institution_cik': cik,
                                'shares_change': int(current['shares'])
                            })
                            signals_generated += 1
                            print(f"✅ Generated NEW_POSITION signal for {cusip} ({company_name}) - shares: {current['shares']}")
                        else:
                            if total_positions_checked <= 3:
                                print(f"   ⚠️  Skipping NEW_POSITION for {cusip} - shares: {current['shares']} (not > 0)")
                    else:
                        previous = holdings[i-1]
                        
                        if previous['shares'] > 0:
                            change_pct = (current['shares'] - previous['shares']) / previous['shares']
                            
                            # Doubling down - increased position by 50%+
                            if change_pct >= 0.5:
                                signals.append({
                                    'date': current['date'],
                                    'ticker': cusip,  # Will be mapped to ticker later
                                    'cusip': cusip,
                                    'name': company_name,  # Include company name for ticker inference
                                    'action': 'BUY',
                                    'signal_type': 'DOUBLING_DOWN',
                                    'signal_strength': min(change_pct, 1.0),
                                    'institution_cik': cik,
                                    'shares_change': int(current['shares'] - previous['shares'])
                                })
                                signals_generated += 1
                                print(f"✅ Generated DOUBLING_DOWN signal for {cusip} ({company_name}) - {change_pct:.1%}")
                            # Reducing - decreased position by 50%+
                            elif change_pct <= -0.5:
                                signals.append({
                                    'date': current['date'],
                                    'ticker': cusip,  # Will be mapped to ticker later
                                    'cusip': cusip,
                                    'name': company_name,  # Include company name for ticker inference
                                    'action': 'SELL',
                                    'signal_type': 'REDUCING',
                                    'signal_strength': min(abs(change_pct), 1.0),
                                    'institution_cik': cik,
                                    'shares_change': int(current['shares'] - previous['shares'])
                                })
                                signals_generated += 1
                                print(f"✅ Generated REDUCING signal for {cusip} ({company_name}) - {change_pct:.1%}")
                            else:
                                if total_positions_checked <= 3:
                                    print(f"   ⏭️  Change {change_pct:.1%} for {cusip} - not significant enough")
                        else:
                            if total_positions_checked <= 3:
                                print(f"   ⚠️  Previous shares for {cusip}: {previous['shares']} (not > 0)")

                # Stop after checking a few positions for debug
                if total_positions_checked >= 5:
                    print(f"🔍 Debug: Stopping after 5 positions...")
                    break

                # Stop after checking a few positions for debug
                if signals_generated >= 10:
                    break
            
            print(f"✅ Found {len(signals)} trading signals from {len(holdings_by_position)} positions")

            # Log signal breakdown
            signal_types = {}
            for signal in signals:
                sig_type = signal.get('signal_type', 'UNKNOWN')
                signal_types[sig_type] = signal_types.get(sig_type, 0) + 1

            print(f"📊 Signal breakdown: {signal_types}")

            if len(signals) == 0:
                print("❌ ERROR: No signals generated!")
                print(f"   Holdings by position keys: {list(holdings_by_position.keys())[:5]}")
                if holdings_by_position:
                    sample_key = list(holdings_by_position.keys())[0]
                    print(f"   Sample holdings for {sample_key}: {holdings_by_position[sample_key]}")
            
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
        
        # Rate limit: AlphaVantage free tier = 1 request/second, 25/day
        # Use semaphore of 1 to serialize requests
        semaphore = asyncio.Semaphore(1)
        
        async def fetch_one_ticker(ticker, idx):
            """Fetch a single ticker with semaphore and rate limiting"""
            async with semaphore:
                try:
                    # Wait 1.5 seconds between requests to avoid rate limits
                    if idx > 0:
                        await asyncio.sleep(1.5)
                    
                    df = await engine.fetch_historical_prices(ticker, start_date, end_date)
                    if not df.empty:
                        historical_prices[ticker] = df
                        print(f"   ✅ {ticker}: {len(df)} days")
                        
                        if progress_callback:
                            progress_callback(
                                ticker, 
                                idx, 
                                len(tickers),
                                success=True
                            )
                    else:
                        print(f"   ⚠️  {ticker}: No data returned")
                        if progress_callback:
                            progress_callback(
                                ticker, 
                                idx, 
                                len(tickers),
                                success=True
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
                            len(tickers),
                            success=False
                        )
        
        # Fetch all tickers in parallel (but limited by semaphore)
        tasks = [fetch_one_ticker(ticker, idx) for idx, ticker in enumerate(tickers, 1)]
        await asyncio.gather(*tasks)
        
        print(f"✅ Fetched prices for {len(historical_prices)}/{len(tickers)} stocks")
        return historical_prices

