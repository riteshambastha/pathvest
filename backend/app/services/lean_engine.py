"""
LEAN Engine Wrapper - Integrates QuantConnect LEAN with PathVest
Provides industrial-grade backtesting with event-driven architecture
"""
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import os
import sys

# Add lean directory to path for strategy translator
LEAN_DIR = Path(__file__).parent.parent.parent / "lean"
sys.path.insert(0, str(LEAN_DIR))

try:
    from algorithms.strategy_translator import StrategyTranslator
    from results.results_parser import LEANResultsParser
except ImportError:
    # Fallback if not available
    StrategyTranslator = None
    LEANResultsParser = None

class LEANBacktestEngine:
    """
    Wrapper for LEAN backtesting engine
    Translates PathVest strategies to LEAN and executes backtests
    """
    
    def __init__(self, 
                 start_date: datetime,
                 end_date: datetime,
                 initial_cash: float = 100000,
                 lean_cli_path: Optional[str] = None):
        """
        Initialize LEAN backtest engine
        
        Args:
            start_date: Backtest start date
            end_date: Backtest end date
            initial_cash: Starting capital
            lean_cli_path: Path to LEAN CLI (defaults to system lean)
        """
        self.start_date = start_date
        self.end_date = end_date
        self.initial_cash = initial_cash
        self.lean_cli = lean_cli_path or "lean"
        
        # Paths
        self.project_root = Path(__file__).parent.parent.parent
        self.lean_dir = self.project_root / "lean"
        self.algorithms_dir = self.lean_dir / "algorithms"
        self.data_dir = self.lean_dir / "data"
        self.results_dir = self.lean_dir / "results"
        self.config_dir = self.lean_dir / "config"
        
        # Ensure directories exist
        for directory in [self.algorithms_dir, self.data_dir, 
                         self.results_dir, self.config_dir]:
            directory.mkdir(parents=True, exist_ok=True)
        
        # Initialize strategy translator and results parser
        self.translator = StrategyTranslator() if StrategyTranslator else None
        self.results_parser = LEANResultsParser() if LEANResultsParser else None
    
    def create_algorithm(self, strategy_config: Dict[str, Any]) -> str:
        """
        Generate LEAN algorithm code from PathVest strategy configuration.
        
        This uses the StrategyTranslator to convert a JSON config into
        executable Python code for LEAN.
        
        Args:
            strategy_config: PathVest strategy configuration dictionary
            
        Returns:
            str: Python code for LEAN algorithm
        """
        if not self.translator:
            raise ImportError("StrategyTranslator not available")
        
        return self.translator.translate(strategy_config)
    
    def run_backtest(self, 
                    strategy_config: Dict[str, Any],
                    algorithm_code: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute LEAN backtest
        
        Args:
            strategy_config: PathVest strategy configuration
            algorithm_code: Optional LEAN algorithm Python code. If not provided,
                          will be auto-generated from strategy_config.
            
        Returns:
            Backtest results in PathVest format
        """
        try:
            # 1. Generate algorithm code if not provided
            if algorithm_code is None:
                if not self.translator:
                    raise ValueError("No algorithm code provided and StrategyTranslator not available")
                algorithm_code = self.create_algorithm(strategy_config)
            
            # 2. Write algorithm to file
            algorithm_file = self._write_algorithm(algorithm_code, strategy_config)
            
            # 3. Create LEAN configuration
            config_file = self._create_lean_config(strategy_config)
            
            # 4. Execute LEAN CLI backtest
            result_path = self._execute_lean_backtest(algorithm_file, config_file)
            
            # 5. Parse LEAN results using enhanced parser
            if self.results_parser:
                pathvest_results = self.results_parser.parse(result_path)
            else:
                # Fallback to basic parsing
                lean_results = self._read_lean_results(result_path)
                pathvest_results = self._convert_to_pathvest_format(
                    lean_results, 
                    strategy_config
                )
            
            return pathvest_results
            
        except Exception as e:
            return {
                "status": "error",
                "error_message": str(e),
                "engine": "LEAN"
            }
    
    def _write_algorithm(self, 
                        algorithm_code: str, 
                        config: Dict[str, Any]) -> Path:
        """Write algorithm code to file"""
        strategy_name = config.get("name", "strategy").replace(" ", "_")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{strategy_name}_{timestamp}.py"
        
        algorithm_file = self.algorithms_dir / filename
        algorithm_file.write_text(algorithm_code)
        
        return algorithm_file
    
    def _create_lean_config(self, strategy_config: Dict[str, Any]) -> Path:
        """Create LEAN configuration JSON"""
        config = {
            "algorithm-type-name": "PathVestStrategy",
            "algorithm-language": "Python",
            "data-folder": str(self.data_dir),
            "results-destination-folder": str(self.results_dir),
            "parameters": {
                "start-date": self.start_date.strftime("%Y-%m-%d"),
                "end-date": self.end_date.strftime("%Y-%m-%d"),
                "cash": self.initial_cash,
                "resolution": "Daily"
            },
            "environments": {
                "backtesting": {
                    "live-mode": False,
                    "setup-handler": "QuantConnect.Lean.Engine.Setup.BacktestingSetupHandler",
                    "result-handler": "QuantConnect.Lean.Engine.Results.BacktestingResultHandler",
                    "data-feed-handler": "QuantConnect.Lean.Engine.DataFeeds.FileSystemDataFeed",
                    "real-time-handler": "QuantConnect.Lean.Engine.RealTime.BacktestingRealTimeHandler",
                    "history-provider": "SubscriptionDataReaderHistoryProvider",
                    "transaction-handler": "BacktestingTransactionHandler"
                }
            }
        }
        
        config_file = self.config_dir / "lean-config.json"
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
        
        return config_file
    
    def _execute_lean_backtest(self, 
                               algorithm_file: Path, 
                               config_file: Path) -> Path:
        """
        Execute LEAN CLI backtest command
        
        Returns path to results JSON
        """
        # LEAN CLI command
        cmd = [
            self.lean_cli,
            "backtest",
            str(algorithm_file.parent),
            "--algorithm-file", algorithm_file.name,
            "--output", str(self.results_dir)
        ]
        
        # Execute command
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(self.project_root)
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"LEAN backtest failed: {result.stderr}")
        
        # Find results file (LEAN creates timestamped results)
        result_files = list(self.results_dir.glob("*.json"))
        if not result_files:
            raise FileNotFoundError("LEAN results file not found")
        
        # Return most recent results file
        return max(result_files, key=lambda p: p.stat().st_mtime)
    
    def _read_lean_results(self, result_path: Path) -> Dict[str, Any]:
        """Read LEAN results JSON file"""
        with open(result_path, 'r') as f:
            return json.load(f)
    
    def _convert_to_pathvest_format(self, 
                                    lean_results: Dict[str, Any],
                                    strategy_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert LEAN results to PathVest format
        
        LEAN provides:
        - TotalPerformance.PortfolioStatistics
        - Orders
        - Charts
        - Statistics
        
        PathVest expects:
        - summary (metrics)
        - equity_curve
        - trades
        - real_market_data
        """
        try:
            stats = lean_results.get("TotalPerformance", {}).get("PortfolioStatistics", {})
            
            # Extract metrics
            pathvest_results = {
                "status": "completed",
                "engine": "LEAN",
                "execution_time_seconds": lean_results.get("TotalSeconds", 0),
                "summary": {
                    "total_return": float(stats.get("TotalNetProfit", 0)),
                    "cagr": float(stats.get("CompoundingAnnualReturn", 0)),
                    "volatility": float(stats.get("AnnualStandardDeviation", 0)),
                    "sharpe_ratio": float(stats.get("SharpeRatio", 0)),
                    "sortino_ratio": float(stats.get("SortinoRatio", 0)),
                    "max_drawdown": float(stats.get("Drawdown", 0)),
                    "win_rate": float(stats.get("WinRate", 0)),
                    "alpha": float(stats.get("Alpha", 0)),
                    "beta": float(stats.get("Beta", 0)),
                    "information_ratio": float(stats.get("InformationRatio", 0)),
                },
                "equity_curve": self._extract_equity_curve(lean_results),
                "trades": self._extract_trades(lean_results),
                "lean_raw_results": lean_results  # Keep full LEAN output
            }
            
            return pathvest_results
            
        except Exception as e:
            return {
                "status": "error",
                "error_message": f"Failed to parse LEAN results: {str(e)}",
                "lean_raw_results": lean_results
            }
    
    def _extract_equity_curve(self, lean_results: Dict[str, Any]) -> Dict[str, List]:
        """Extract equity curve from LEAN charts"""
        try:
            charts = lean_results.get("Charts", {})
            strategy_equity = charts.get("Strategy Equity", {})
            series = strategy_equity.get("Series", {})
            equity_values = series.get("Equity", {}).get("Values", [])
            
            dates = [point.get("x", "") for point in equity_values]
            values = [point.get("y", 0) for point in equity_values]
            
            return {
                "dates": dates,
                "portfolio_values": values
            }
        except:
            return {"dates": [], "portfolio_values": []}
    
    def _extract_trades(self, lean_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract trade log from LEAN orders"""
        try:
            orders = lean_results.get("Orders", [])
            trades = []
            
            for order in orders:
                if order.get("Status") == "Filled":
                    trades.append({
                        "ticker": order.get("Symbol", ""),
                        "entry_date": order.get("Time", ""),
                        "entry_price": order.get("Price", 0),
                        "quantity": order.get("Quantity", 0),
                        "direction": order.get("Direction", ""),
                        "value": order.get("Value", 0),
                        "order_id": order.get("Id", 0)
                    })
            
            return trades
        except:
            return []
    
    def verify_installation(self) -> Dict[str, Any]:
        """
        Verify LEAN installation and Docker availability
        
        Returns status information
        """
        status = {
            "lean_cli": False,
            "docker": False,
            "python_version": None,
            "lean_version": None
        }
        
        try:
            # Check LEAN CLI
            result = subprocess.run(
                [self.lean_cli, "--version"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                status["lean_cli"] = True
                status["lean_version"] = result.stdout.strip()
        except:
            pass
        
        try:
            # Check Docker
            result = subprocess.run(
                ["docker", "--version"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                status["docker"] = True
        except:
            pass
        
        # Python version
        import sys
        status["python_version"] = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        
        return status


# Convenience function for PathVest API
def create_lean_engine(start_date: str, 
                      end_date: str, 
                      initial_cash: float = 100000) -> LEANBacktestEngine:
    """
    Create LEAN engine instance from string dates
    
    Args:
        start_date: Date string in format 'YYYY-MM-DD'
        end_date: Date string in format 'YYYY-MM-DD'
        initial_cash: Starting capital
        
    Returns:
        Configured LEANBacktestEngine instance
    """
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    
    return LEANBacktestEngine(start, end, initial_cash)

