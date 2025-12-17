"""
LEAN Backtest Worker
Executes backtests using the LEAN engine and parses results
"""

import json
import subprocess
import tempfile
import os
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path
import pandas as pd

from app.schemas.backtest_request import BacktestRequest
from app.schemas.backtest_response import (
    BacktestResponse,
    BacktestSummary,
    EquityCurve,
    Trade,
    PositionHistory
)


class BacktestWorker:
    """
    Worker service for executing LEAN backtests
    
    Responsibilities:
    1. Translate BacktestRequest → LEAN configuration
    2. Execute LEAN backtest in subprocess/container
    3. Parse LEAN results → BacktestResponse
    4. Handle errors and logging
    """
    
    def __init__(
        self,
        lean_cli_path: str = "lean",
        lean_project_dir: str = "/Users/riteshambastha/projects/pathvest/backend/lean_engine"
    ):
        """
        Initialize backtest worker
        
        Args:
            lean_cli_path: Path to LEAN CLI executable
            lean_project_dir: Path to LEAN project directory
        """
        self.lean_cli_path = lean_cli_path
        self.lean_project_dir = Path(lean_project_dir)
        self.strategies_dir = self.lean_project_dir / "strategies"
        self.data_dir = self.lean_project_dir / "data"
        self.results_dir = self.lean_project_dir / "results"
        
        # Ensure directories exist
        self.strategies_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.results_dir.mkdir(parents=True, exist_ok=True)
    
    def execute_backtest(
        self,
        backtest_id: str,
        request: BacktestRequest,
        progress_callback: Optional[callable] = None
    ) -> BacktestResponse:
        """
        Execute a complete backtest
        
        Args:
            backtest_id: Unique backtest identifier
            request: Backtest configuration
            progress_callback: Optional callback(progress_pct, message)
        
        Returns:
            BacktestResponse with results
        """
        start_time = datetime.utcnow()
        
        try:
            # Step 1: Generate LEAN configuration
            if progress_callback:
                progress_callback(10, "Generating LEAN configuration...")
            
            lean_config = self._translate_to_lean_config(request)
            
            # Step 2: Write configuration files
            if progress_callback:
                progress_callback(20, "Writing configuration files...")
            
            config_file = self._write_lean_config(backtest_id, lean_config)
            
            # Step 3: Execute LEAN
            if progress_callback:
                progress_callback(30, "Executing LEAN backtest...")
            
            lean_output = self._run_lean_backtest(config_file, progress_callback)
            
            # Step 4: Parse results
            if progress_callback:
                progress_callback(80, "Parsing results...")
            
            result = self._parse_lean_results(
                backtest_id=backtest_id,
                lean_output=lean_output,
                request=request
            )
            
            # Calculate execution time
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            result.execution_time_seconds = execution_time
            
            if progress_callback:
                progress_callback(100, "Backtest completed successfully")
            
            return result
        
        except Exception as e:
            raise Exception(f"Backtest execution failed: {str(e)}")
    
    def _translate_to_lean_config(self, request: BacktestRequest) -> Dict[str, Any]:
        """
        Translate BacktestRequest to LEAN configuration format
        
        Args:
            request: BacktestRequest
        
        Returns:
            Dict with LEAN configuration
        """
        config = request.strategy_config
        
        lean_config = {
            "algorithm-type-name": "InstitutionalFollowingStrategy",
            "algorithm-language": "Python",
            "algorithm-location": "strategies/institutional_strategy.py",
            
            "parameters": {
                "initial-cash": config.initial_capital,
                "start-date": config.backtest_period.start_date.isoformat(),
                "end-date": config.backtest_period.end_date.isoformat(),
                "enable-fractional-shares": True,
                
                # Universe filters
                "universe_market_cap_min": config.universe_filters.market_cap_min,
                "universe_index": config.universe_filters.index_membership,
                "universe_lookback_quarters": config.universe_filters.lookback_quarters,
                
                # Investor filters
                "investor_aum_min": config.sub_universe_filters.investor.aum_min,
                "investor_track_record_quarters": config.sub_universe_filters.investor.track_record_quarters,
                "investor_concentration_max": config.sub_universe_filters.investor.concentration_max,
                "investor_turnover_max": config.sub_universe_filters.investor.turnover_max,
                
                # Transaction filters
                "transaction_min_buy_value": config.sub_universe_filters.transaction.min_buy_value,
                "transaction_share_increase_min": config.sub_universe_filters.transaction.share_increase_min,
                
                # Entry signals
                "enable_doubling_down": config.entry_signals.enable_doubling_down,
                "enable_insider_buying": config.entry_signals.enable_insider_buying,
                "enable_herding": config.entry_signals.enable_herding,
                
                # Technical confirmation
                "price_breakout_days": config.entry_signals.technical_confirmation.price_breakout_days,
                "sma_period": config.entry_signals.technical_confirmation.sma_period,
                "rsi_period": config.entry_signals.technical_confirmation.rsi_period,
                "rsi_threshold": config.entry_signals.technical_confirmation.rsi_threshold,
                
                # Position sizing
                "position_size_pct": config.position_sizing.percent_per_position,
                "min_positions": config.position_sizing.min_positions,
                "max_positions": config.position_sizing.max_positions,
                "rank_buffer": config.position_sizing.rank_buffer,
                
                # Conviction weights
                "conviction_weight_herding": config.conviction_weights.herding,
                "conviction_weight_insider": config.conviction_weights.insider,
                
                # Exit rules
                "enable_thesis_drift": config.exit_rules.enable_thesis_drift,
                "enable_insider_reversal": config.exit_rules.enable_insider_reversal,
                "enable_trailing_stop": config.exit_rules.enable_trailing_stop,
                "trailing_stop_percent": config.exit_rules.trailing_stop_percent,
                "enable_dead_money": config.exit_rules.enable_dead_money,
                "dead_money_quarters": config.exit_rules.dead_money_quarters,
                
                # Transaction costs
                "commission_per_share": config.transaction_costs.commission_per_share,
                "slippage_bps": config.transaction_costs.slippage_bps,
                
                # Rebalancing
                "rebalance_frequency": config.heartbeat.rebalance_frequency
            },
            
            "data-folder": str(self.data_dir),
            "results": str(self.results_dir)
        }
        
        return lean_config
    
    def _write_lean_config(self, backtest_id: str, config: Dict[str, Any]) -> Path:
        """
        Write LEAN configuration to file
        
        Args:
            backtest_id: Backtest identifier
            config: LEAN configuration dict
        
        Returns:
            Path to configuration file
        """
        config_file = self.results_dir / f"{backtest_id}_config.json"
        
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
        
        return config_file
    
    def _run_lean_backtest(
        self,
        config_file: Path,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Execute LEAN backtest as subprocess
        
        Args:
            config_file: Path to LEAN configuration
            progress_callback: Optional callback for progress
        
        Returns:
            Dict with LEAN output
        """
        # For MVP, we'll simulate LEAN execution
        # In production, this would run actual LEAN CLI:
        # subprocess.run([self.lean_cli_path, "backtest", str(config_file)])
        
        # Simulate progress
        if progress_callback:
            progress_callback(40, "Running backtest simulation...")
            progress_callback(50, "Processing historical data...")
            progress_callback(60, "Executing trades...")
            progress_callback(70, "Calculating performance...")
        
        # Return mock LEAN output
        # In production, this would parse actual LEAN JSON output
        return {
            'Statistics': {
                'Total Trades': 47,
                'Average Win': 0.082,
                'Average Loss': -0.043,
                'Compounding Annual Return': 0.0623,
                'Drawdown': -0.234,
                'Sharpe Ratio': 1.23,
                'Alpha': 0.032,
                'Beta': 0.87
            },
            'Charts': {
                'Strategy Equity': {
                    'Series': {
                        'Equity': {
                            'Values': []  # Would contain equity curve data
                        }
                    }
                }
            },
            'Orders': []  # Would contain order history
        }
    
    def _parse_lean_results(
        self,
        backtest_id: str,
        lean_output: Dict[str, Any],
        request: BacktestRequest
    ) -> BacktestResponse:
        """
        Parse LEAN output into BacktestResponse
        
        Args:
            backtest_id: Backtest identifier
            lean_output: Raw LEAN output
            request: Original request
        
        Returns:
            BacktestResponse
        """
        # Extract statistics
        stats = lean_output.get('Statistics', {})
        
        # Build summary
        summary = BacktestSummary(
            total_return=float(stats.get('Total Return', 0.847)),
            cagr=float(stats.get('Compounding Annual Return', 0.0623)),
            volatility=float(stats.get('Annual Std Dev', 0.182)),
            sharpe_ratio=float(stats.get('Sharpe Ratio', 1.23)),
            sortino_ratio=float(stats.get('Sortino Ratio', 1.67)),
            max_drawdown=float(stats.get('Drawdown', -0.234)),
            romad=float(stats.get('RoMaD', 0.266)),
            alpha=float(stats.get('Alpha', 0.032)),
            beta=float(stats.get('Beta', 0.87)),
            information_ratio=float(stats.get('Information Ratio', 0.45)),
            var_95=float(stats.get('VaR 95%', -0.023)),
            cvar_95=float(stats.get('cVaR 95%', -0.031)),
            win_rate_daily=float(stats.get('Win Rate Daily', 0.54)),
            win_rate_monthly=float(stats.get('Win Rate Monthly', 0.61)),
            win_rate_yearly=float(stats.get('Win Rate Yearly', 0.70)),
            best_day=float(stats.get('Best Day', 0.068)),
            worst_day=float(stats.get('Worst Day', -0.052)),
            benchmark_total_return=float(stats.get('Benchmark Return', 0.612)),
            benchmark_cagr=float(stats.get('Benchmark CAGR', 0.048))
        )
        
        # Build equity curve
        equity_curve = self._build_equity_curve(lean_output)
        
        # Build trades list
        trades = self._build_trades_list(lean_output)
        
        return BacktestResponse(
            backtest_id=backtest_id,
            status='completed',
            execution_time_seconds=0,  # Will be set by caller
            summary=summary,
            equity_curve=equity_curve,
            trades=trades,
            strategy_name=request.strategy_config.name,
            start_date=str(request.strategy_config.backtest_period.start_date),
            end_date=str(request.strategy_config.backtest_period.end_date),
            initial_capital=request.strategy_config.initial_capital
        )
    
    def _build_equity_curve(self, lean_output: Dict[str, Any]) -> EquityCurve:
        """Build equity curve from LEAN output"""
        # In production, parse from LEAN Charts
        # For now, return mock data
        return EquityCurve(
            dates=["2013-01-01", "2013-06-30", "2013-12-31", "2023-12-31"],
            portfolio_values=[1000000, 1120000, 1247000, 1847000],
            benchmark_values=[1000000, 1085000, 1152000, 1612000]
        )
    
    def _build_trades_list(self, lean_output: Dict[str, Any]) -> List[Trade]:
        """Build trades list from LEAN output"""
        # In production, parse from LEAN Orders/Trades
        # For now, return mock trades
        return [
            Trade(
                entry_date="2013-03-15",
                exit_date="2013-09-22",
                ticker="AAPL",
                entry_price=62.35,
                exit_price=71.20,
                shares=801.6,
                pnl=7091.16,
                return_pct=0.142,
                holding_period_days=191,
                exit_reason="trailing_stop",
                signal_type="doubling_down",
                conviction_score=72.5,
                rank=3
            ),
            Trade(
                entry_date="2013-04-10",
                exit_date="2014-01-15",
                ticker="MSFT",
                entry_price=28.50,
                exit_price=37.20,
                shares=1754.4,
                pnl=15263.28,
                return_pct=0.305,
                holding_period_days=280,
                exit_reason="thesis_drift",
                signal_type="herding",
                conviction_score=68.2,
                rank=7
            )
        ]


# Singleton instance
_worker_instance = None


def get_backtest_worker() -> BacktestWorker:
    """Get singleton BacktestWorker instance"""
    global _worker_instance
    
    if _worker_instance is None:
        _worker_instance = BacktestWorker()
    
    return _worker_instance

