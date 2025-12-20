"""
LEAN Backtest Worker
Executes backtests using the LEAN engine and parses results
"""

import json
import subprocess
import tempfile
import os
import shutil
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from pathlib import Path
import pandas as pd

from app.schemas.backtest_request import BacktestRequest
from app.schemas.backtest_response import (
    BacktestResponse,
    BacktestSummary,
    EquityCurve,
    Trade,
)
from app.services.alphavantage_service import AlphaVantageService
from app.services.sec_edgar_service import SECEdgarService
from app.services.lean_engine import LEANBacktestEngine
from app.core.config import settings

# Database access
from app.services.strategy_db import SessionLocal
from sqlalchemy import text


class BacktestWorker:
    """
    Worker service for executing LEAN backtests
    """
    
    def __init__(
        self,
        lean_cli_path: str = "lean",
        lean_project_dir: str = None # defaults to backend/lean
    ):
        """
        Initialize backtest worker
        """
        self.lean_cli_path = lean_cli_path
        
        # Determine LEAN project root (backend/lean)
        if lean_project_dir:
            self.lean_project_dir = Path(lean_project_dir)
        else:
            # Assume we are in backend/lean_engine/worker/backtest_worker.py
            # Go up 3 levels to backend, then to lean
            self.lean_project_dir = Path(__file__).parent.parent.parent / "lean"

        self.data_dir = self.lean_project_dir / "data"
        self.results_dir = self.lean_project_dir / "results"
        
        # Custom data directories
        self.sec_13f_dir = self.data_dir / "sec_13f"
        self.sec_form4_dir = self.data_dir / "sec_form4"
        
        # Ensure directories exist
        self.sec_13f_dir.mkdir(parents=True, exist_ok=True)
        self.sec_form4_dir.mkdir(parents=True, exist_ok=True)
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"✅ BacktestWorker initialized (Root: {self.lean_project_dir})")
        print(f"   Data Dir: {self.data_dir}")
    
    def execute_backtest(
        self,
        backtest_id: str,
        request: BacktestRequest,
        progress_callback: Optional[callable] = None
    ) -> BacktestResponse:
        """
        Execute a complete backtest using LEAN
        """
        start_time = datetime.utcnow()
        
        try:
            # Step 1: Initialize Engine
            if progress_callback:
                progress_callback(5, "Initializing LEAN engine...")
                
            engine = LEANBacktestEngine(
                start_date=request.strategy_config.backtest_period.start_date,
                end_date=request.strategy_config.backtest_period.end_date,
                initial_cash=request.strategy_config.initial_capital,
                lean_cli_path=self.lean_cli_path
            )
            
            # Step 2: Prepare Data (Fetch from DB -> Write to JSONL)
            if progress_callback:
                progress_callback(15, "Preparing institutional data for LEAN...")
            
            stats = self._prepare_data_for_lean(request)
            
            if progress_callback:
                progress_callback(30, f"Data ready: {stats['filings']} filings, {stats['stocks']} stocks")

            # Step 2.5: Inject discovered stocks into config
            # This ensures the generated algorithm subscribes to data for these stocks
            config_dict = request.strategy_config.dict()
            if 'universe' not in config_dict:
                config_dict['universe'] = {}
            
            existing_tickers = config_dict['universe'].get('tickers', []) or []
            # Merge and deduplicate
            all_tickers = list(set(existing_tickers + stats['stocks_list']))
            config_dict['universe']['tickers'] = all_tickers
            
            print(f"✅ Auto-populated universe with {len(all_tickers)} stocks from institutional holdings")

            # Step 3: Run Backtest
            if progress_callback:
                progress_callback(40, "Running LEAN backtest (this may take a few minutes)...")
                
            # This generates algorithm, config, runs CLI, parses results
            result_dict = engine.run_backtest(config_dict)
            
            if result_dict.get('status') == 'error':
                 raise Exception(result_dict.get('error_message', 'Unknown LEAN error'))

            # Step 4: Finalize
            if progress_callback:
                progress_callback(90, "Finalizing results...")
            
            # Convert dict result to Pydantic Response
            response = self._convert_to_response(backtest_id, request, result_dict)
            
            response.execution_time_seconds = (datetime.utcnow() - start_time).total_seconds()
            
            # Add data stats
            response.api_calls_made = stats.get('api_calls', 0)
            response.sec_filings_fetched = stats.get('filings', 0)
            response.stocks_analyzed = stats.get('stocks_list', [])
            
            if progress_callback:
                progress_callback(100, "Backtest completed successfully")
                
            return response
        
        except Exception as e:
            print(f"❌ LEAN Execution Failed: {e}")
            import traceback
            traceback.print_exc()
            raise e

    def _prepare_data_for_lean(self, request: BacktestRequest) -> Dict[str, Any]:
        """
        Fetch data from Postgres and write to JSONL files for LEAN
        """
        config = request.strategy_config
        
        # Get selected institutions
        ciks = []
        if hasattr(config, 'selected_institutions'):
             ciks = config.selected_institutions
        # Fallback to dictionary lookups if needed (handled in backtest endpoint usually)
        if not ciks and config.stock_selection:
             ciks = config.stock_selection.get('selected_institutions', [])
        
        if not ciks:
            print("⚠️ No institutions selected for LEAN data prep")
            return {'filings': 0, 'stocks': 0, 'stocks_list': []}
            
        print(f"📊 Fetching data for {len(ciks)} institutions...")
        
        # Query DB
        db = SessionLocal()
        try:
            # 1. Fetch Holdings
            start_date = config.backtest_period.start_date
            # Lookback extra 1 year for trends/doubling down calculation
            query_start = start_date - timedelta(days=365)
            end_date = config.backtest_period.end_date
            
            query = text("""
                SELECT 
                    f.cik, i.name as institution_name, 
                    f.filing_date, f.period_of_report,
                    h.ticker, h.value as market_value, h.shares_or_prn_amt as shares
                FROM holdings h
                JOIN filings f ON h.filing_id = f.id
                JOIN institutions i ON f.institution_id = i.id
                WHERE f.cik = ANY(:ciks)
                AND f.filing_date >= :query_start
                AND f.filing_date <= :end_date
                AND h.ticker IS NOT NULL
                ORDER BY h.ticker, f.filing_date
            """)
            
            results = db.execute(query, {
                "ciks": ciks, 
                "query_start": query_start,
                "end_date": end_date
            }).fetchall()
            
            # Process results into Ticker -> [Events]
            ticker_events = {}
            stocks_set = set()
            
            # Simple tracking for calculating changes
            # (ticker, cik) -> last_shares
            history = {} 
            
            for row in results:
                ticker = row.ticker.upper()
                if not ticker: continue
                
                stocks_set.add(ticker)
                
                # Calculate change
                key = (ticker, row.cik)
                last_shares = history.get(key, 0)
                current_shares = float(row.shares or 0)
                
                shares_change_pct = 0.0
                if last_shares > 0:
                    shares_change_pct = ((current_shares - last_shares) / last_shares) * 100
                
                is_new = (last_shares == 0 and current_shares > 0)
                is_doubling_down = (shares_change_pct >= 100) # Simple rule
                
                # Update history
                history[key] = current_shares
                
                # Skip if outside actual backtest period (we fetched extra for history)
                if row.filing_date < start_date:
                    continue
                
                event = {
                    "cik": row.cik,
                    "institution_name": row.institution_name,
                    "filing_date": row.filing_date.strftime("%Y-%m-%d"),
                    "period_of_report": row.period_of_report,
                    "shares": current_shares,
                    "market_value": float(row.market_value or 0),
                    "shares_change_pct": shares_change_pct,
                    "is_new_position": is_new,
                    "is_doubling_down": is_doubling_down,
                    "conviction_score": 50.0 + (shares_change_pct if shares_change_pct > 0 else 0) # Simple proxy
                }
                
                if ticker not in ticker_events:
                    ticker_events[ticker] = []
                ticker_events[ticker].append(event)
            
            # Write JSONL files
            count = 0
            for ticker, events in ticker_events.items():
                file_path = self.sec_13f_dir / f"{ticker.lower()}.jsonl"
                with open(file_path, 'w') as f:
                    for event in events:
                        f.write(json.dumps(event) + "\n")
                count += 1
                
            print(f"✅ Wrote {count} data files for LEAN")
            
            return {
                'filings': len(results), # Approximate
                'stocks': count,
                'stocks_list': list(stocks_set),
                'api_calls': count * 2 # Proxy estimate
            }
            
        finally:
            db.close()

    def _convert_to_response(self, backtest_id: str, request: BacktestRequest, result: Dict) -> BacktestResponse:
        """Convert engine dict result to Pydantic response"""
        
        # Helper to safely get nested values
        summary = result.get('summary', {})
        equity = result.get('equity_curve', {})
        trades_list = result.get('trades', [])
        
        # Build Summary
        backtest_summary = BacktestSummary(
            total_return=summary.get('total_return', 0),
            cagr=summary.get('cagr', 0),
            sharpe_ratio=summary.get('sharpe_ratio', 0),
            max_drawdown=summary.get('max_drawdown', 0),
            win_rate_daily=summary.get('win_rate', 0),
            alpha=summary.get('alpha', 0),
            beta=summary.get('beta', 0),
            volatility=summary.get('volatility', 0),
            sortino_ratio=summary.get('sortino_ratio', 0),
            information_ratio=summary.get('information_ratio', 0)
        )
        
        # Build Equity Curve
        equity_curve = EquityCurve(
            dates=equity.get('dates', []),
            portfolio_values=equity.get('portfolio_values', []),
            benchmark_values=[] # Optional
        )
        
        # Build Trades
        trades = []
        for t in trades_list:
            trades.append(Trade(
                ticker=t.get('ticker'),
                entry_date=str(t.get('entry_date')),
                entry_price=t.get('entry_price'),
                shares=t.get('quantity'),
                signal_type=t.get('direction', 'BUY'), # Map direction to signal type loosely
                return_pct=0, # Calculated fields might be missing in raw trade list
                pnl=t.get('value', 0)
            ))

        return BacktestResponse(
            backtest_id=backtest_id,
            strategy_name=request.strategy_config.name,
            status="completed",
            start_date=result.get('start_date', str(request.strategy_config.backtest_period.start_date)),
            end_date=result.get('end_date', str(request.strategy_config.backtest_period.end_date)),
            initial_capital=result.get('initial_capital', request.strategy_config.initial_capital),
            final_value=result.get('final_value', 0),
            summary=backtest_summary,
            equity_curve=equity_curve,
            trades=trades,
            real_market_data={"source": "LEAN / AlphaVantage"},
            institutional_signals={"source": "PathVest DB"}
        )

# Singleton getter
_worker_instance = None
def get_backtest_worker() -> BacktestWorker:
    global _worker_instance
    if _worker_instance is None:
        _worker_instance = BacktestWorker()
    return _worker_instance
