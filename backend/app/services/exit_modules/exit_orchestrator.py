"""
Exit Module Orchestrator
Coordinates all exit modules and determines which positions to exit

Per SRS FR-3.1.C.11:
- Orchestrates all 4 exit modules
- Prioritizes exit signals by confidence
- Provides comprehensive exit analysis
- Supports configurable exit strategies
"""

from typing import Dict, List, Optional, Union
from datetime import date
from dataclasses import dataclass
import pandas as pd

try:
    # Try relative imports first (for package usage)
    from .thesis_drift import ThesisDriftModule, ThesisDriftExit
    from .insider_reversal import InsiderReversalModule, InsiderReversalExit
    from .trailing_stop import TrailingStopModule, TrailingStopExit
    from .dead_money import DeadMoneyModule, DeadMoneyExit
except ImportError:
    # Fall back to direct imports (for standalone testing)
    from thesis_drift import ThesisDriftModule, ThesisDriftExit
    from insider_reversal import InsiderReversalModule, InsiderReversalExit
    from trailing_stop import TrailingStopModule, TrailingStopExit
    from dead_money import DeadMoneyModule, DeadMoneyExit


@dataclass
class ExitDecision:
    """Unified exit decision across all modules"""
    ticker: str
    exit_date: date
    exit_price: Optional[float]
    exit_module: str  # 'thesis_drift', 'insider_reversal', 'trailing_stop', 'dead_money'
    reason: str
    confidence: float
    details: Dict


class ExitOrchestrator:
    """
    Exit Module Orchestrator
    
    Coordinates all exit modules and makes final exit decisions.
    
    Exit Module Priority (by default):
    1. Insider Reversal (highest priority - direct signal)
    2. Thesis Drift (high priority - invalidates entry thesis)
    3. Trailing Stop (medium priority - risk management)
    4. Dead Money (lowest priority - capital efficiency)
    
    Users can configure which modules to enable and their priorities.
    """
    
    def __init__(self, postgres_service = None):
        """
        Initialize Exit Orchestrator
        
        Args:
            postgres_service: PostgreSQL service for data access
        """
        self.bq_client = bq_client
        
        # Initialize all modules
        self.thesis_drift = ThesisDriftModule(bq_client)
        self.insider_reversal = InsiderReversalModule(bq_client)
        self.trailing_stop = TrailingStopModule()
        self.dead_money = DeadMoneyModule()
        
        # Default module priorities (1=highest, 4=lowest)
        self.module_priorities = {
            'insider_reversal': 1,
            'thesis_drift': 2,
            'trailing_stop': 3,
            'dead_money': 4
        }
    
    def check_all_exits(
        self,
        positions: List[Dict],
        current_date: date,
        price_data_dict: Dict[str, pd.DataFrame],
        config: Optional[Dict] = None
    ) -> List[ExitDecision]:
        """
        Check all exit modules for given positions
        
        Args:
            positions: List of position dicts with keys:
                - ticker: Stock ticker
                - entry_date: Entry date
                - entry_price: Entry price
                - institution_cik: Triggering institution CIK (for thesis drift)
            current_date: Current date
            price_data_dict: Dict of ticker -> price DataFrame
            config: Optional configuration dict with module-specific settings
            
        Returns:
            List of ExitDecision objects, sorted by priority and confidence
        """
        
        if config is None:
            config = {}
        
        all_exit_signals = []
        
        # Module 1: Thesis Drift
        if config.get('enable_thesis_drift', True):
            print("📍 Checking Module 1: Thesis Drift...")
            thesis_exits = self.thesis_drift.batch_check_thesis_drift(
                positions=positions,
                check_date=current_date,
                reduction_threshold=config.get('thesis_drift_threshold', 0.25)
            )
            for exit_signal in thesis_exits:
                all_exit_signals.append(self._convert_to_decision(exit_signal, 'thesis_drift'))
            print(f"   Found {len(thesis_exits)} thesis drift exits")
        
        # Module 2: Insider Reversal
        if config.get('enable_insider_reversal', True):
            print("📍 Checking Module 2: Insider Reversal...")
            insider_exits = self.insider_reversal.batch_check_insider_reversal(
                positions=positions,
                check_date=current_date,
                lookback_days=config.get('insider_lookback_days', 90),
                min_transaction_value=config.get('min_insider_transaction', 100_000)
            )
            for exit_signal in insider_exits:
                all_exit_signals.append(self._convert_to_decision(exit_signal, 'insider_reversal'))
            print(f"   Found {len(insider_exits)} insider reversal exits")
        
        # Module 3: Trailing Stop
        if config.get('enable_trailing_stop', True):
            print("📍 Checking Module 3: Trailing Stop/Take-Profit...")
            trailing_exits = self.trailing_stop.batch_check_trailing_stop(
                positions=positions,
                current_date=current_date,
                price_data_dict=price_data_dict,
                trailing_stop_pct=config.get('trailing_stop_pct', 0.15),
                take_profit_pct=config.get('take_profit_pct', 0.50)
            )
            for exit_signal in trailing_exits:
                all_exit_signals.append(self._convert_to_decision(exit_signal, 'trailing_stop'))
            print(f"   Found {len(trailing_exits)} trailing stop exits")
        
        # Module 4: Dead Money
        if config.get('enable_dead_money', True):
            print("📍 Checking Module 4: Dead Money Exit...")
            dead_money_exits = self.dead_money.batch_check_dead_money(
                positions=positions,
                current_date=current_date,
                price_data_dict=price_data_dict,
                min_quarters=config.get('dead_money_quarters', 4),
                max_return_pct=config.get('dead_money_max_return', 0.0)
            )
            for exit_signal in dead_money_exits:
                all_exit_signals.append(self._convert_to_decision(exit_signal, 'dead_money'))
            print(f"   Found {len(dead_money_exits)} dead money exits")
        
        # Sort by priority and confidence
        sorted_exits = self._prioritize_exits(all_exit_signals)
        
        # Deduplicate (keep highest priority exit per ticker)
        final_exits = self._deduplicate_exits(sorted_exits)
        
        return final_exits
    
    def _convert_to_decision(
        self,
        exit_signal: Union[ThesisDriftExit, InsiderReversalExit, TrailingStopExit, DeadMoneyExit],
        module_name: str
    ) -> ExitDecision:
        """
        Convert module-specific exit signal to unified ExitDecision
        
        Args:
            exit_signal: Exit signal from any module
            module_name: Name of the module
            
        Returns:
            Unified ExitDecision object
        """
        
        # Extract common fields
        ticker = exit_signal.ticker
        exit_date = exit_signal.exit_date
        reason = exit_signal.reason
        confidence = exit_signal.confidence
        
        # Get exit price if available
        exit_price = None
        if hasattr(exit_signal, 'exit_price'):
            exit_price = exit_signal.exit_price
        elif hasattr(exit_signal, 'current_price'):
            exit_price = exit_signal.current_price
        
        # Build details dict
        details = {k: v for k, v in exit_signal.__dict__.items() if k not in ['ticker', 'exit_date', 'reason', 'confidence']}
        
        return ExitDecision(
            ticker=ticker,
            exit_date=exit_date,
            exit_price=exit_price,
            exit_module=module_name,
            reason=reason,
            confidence=confidence,
            details=details
        )
    
    def _prioritize_exits(self, exit_signals: List[ExitDecision]) -> List[ExitDecision]:
        """
        Sort exit signals by priority and confidence
        
        Args:
            exit_signals: List of exit decisions
            
        Returns:
            Sorted list (highest priority first)
        """
        
        def sort_key(exit_decision):
            module_priority = self.module_priorities.get(exit_decision.exit_module, 99)
            # Lower priority number = higher priority
            # Higher confidence = higher priority
            # Return tuple: (module_priority, -confidence) for sorting
            return (module_priority, -exit_decision.confidence)
        
        return sorted(exit_signals, key=sort_key)
    
    def _deduplicate_exits(self, sorted_exits: List[ExitDecision]) -> List[ExitDecision]:
        """
        Remove duplicate exits (keep highest priority per ticker)
        
        Args:
            sorted_exits: Sorted list of exit decisions
            
        Returns:
            Deduplicated list
        """
        
        seen_tickers = set()
        deduplicated = []
        
        for exit_decision in sorted_exits:
            if exit_decision.ticker not in seen_tickers:
                deduplicated.append(exit_decision)
                seen_tickers.add(exit_decision.ticker)
        
        return deduplicated
    
    def get_exit_summary(self, exit_decisions: List[ExitDecision]) -> Dict:
        """
        Get summary statistics for exit decisions
        
        Args:
            exit_decisions: List of exit decisions
            
        Returns:
            Dict with summary statistics
        """
        
        if not exit_decisions:
            return {
                'total_exits': 0,
                'by_module': {},
                'avg_confidence': 0
            }
        
        # Count by module
        by_module = {}
        for decision in exit_decisions:
            module = decision.exit_module
            if module not in by_module:
                by_module[module] = 0
            by_module[module] += 1
        
        # Calculate average confidence
        avg_confidence = sum(d.confidence for d in exit_decisions) / len(exit_decisions)
        
        return {
            'total_exits': len(exit_decisions),
            'by_module': by_module,
            'avg_confidence': avg_confidence,
            'tickers': [d.ticker for d in exit_decisions]
        }


# Test function
def test_exit_orchestrator():
    """Test the Exit Orchestrator"""
    print("\n" + "="*70)
    print("🧪 TESTING EXIT MODULE ORCHESTRATOR")
    print("="*70)
    
    try:
        # Initialize PostgreSQL service
        from app.services.postgres_service import get_postgres_service
        client = get_postgres_service()
        print("✅ PostgreSQL service initialized")
    except Exception as e:
        print(f"⚠️  PostgreSQL not available: {e}")
        client = None
    
    # Create orchestrator
    orchestrator = ExitOrchestrator(client)
    print("✅ ExitOrchestrator created")
    
    # Create mock positions
    print("\n1. Creating mock positions...")
    entry_date = date(2023, 1, 1)
    current_date = date(2024, 6, 30)
    
    positions = [
        {
            'ticker': 'AAPL',
            'entry_date': entry_date,
            'entry_price': 100.0,
            'institution_cik': '0001067983'
        },
        {
            'ticker': 'GOOGL',
            'entry_date': entry_date,
            'entry_price': 90.0,
            'institution_cik': '0001364742'
        },
        {
            'ticker': 'MSFT',
            'entry_date': entry_date,
            'entry_price': 120.0,
            'institution_cik': '0001067983'
        }
    ]
    print(f"   ✅ Created {len(positions)} test positions")
    
    # Create mock price data
    print("\n2. Creating mock price data...")
    dates = pd.date_range(start=entry_date, end=current_date, freq='D')
    
    price_data_dict = {}
    for pos in positions:
        ticker = pos['ticker']
        base = pos['entry_price']
        
        if ticker == 'AAPL':
            # Declining (should trigger dead money and trailing stop)
            prices = [base * (1 - (i / len(dates)) * 0.20) for i in range(len(dates))]
        elif ticker == 'GOOGL':
            # Rising then falling (should trigger trailing stop)
            prices = []
            for i in range(len(dates)):
                if i < len(dates) // 2:
                    prices.append(base * (1 + (i / len(dates)) * 0.60))
                else:
                    prices.append(base * 1.30 - ((i - len(dates)//2) / len(dates)) * 0.50)
        else:  # MSFT
            # Strong gains (should trigger take profit)
            prices = [base * (1 + (i / len(dates)) * 0.70) for i in range(len(dates))]
        
        price_data_dict[ticker] = pd.DataFrame({
            'date': dates,
            'close': prices,
            'high': [p * 1.01 for p in prices],
            'low': [p * 0.99 for p in prices]
        })
    print(f"   ✅ Created price data for {len(price_data_dict)} tickers")
    
    # Test orchestrator
    print("\n3. Running exit orchestration...")
    print("="*70)
    
    exit_decisions = orchestrator.check_all_exits(
        positions=positions,
        current_date=current_date,
        price_data_dict=price_data_dict,
        config={
            'enable_thesis_drift': True,
            'enable_insider_reversal': True,
            'enable_trailing_stop': True,
            'enable_dead_money': True,
            'trailing_stop_pct': 0.15,
            'take_profit_pct': 0.50,
            'dead_money_quarters': 4
        }
    )
    
    print("="*70)
    print(f"\n✅ Orchestration complete: {len(exit_decisions)} exit decisions")
    
    # Display results
    print("\n4. Exit Decisions:")
    for i, decision in enumerate(exit_decisions, 1):
        print(f"\n   {i}. {decision.ticker}")
        print(f"      Module: {decision.exit_module}")
        print(f"      Reason: {decision.reason}")
        print(f"      Confidence: {decision.confidence:.1f}")
        if decision.exit_price:
            print(f"      Exit price: ${decision.exit_price:.2f}")
    
    # Get summary
    print("\n5. Exit Summary:")
    summary = orchestrator.get_exit_summary(exit_decisions)
    print(f"   Total exits: {summary['total_exits']}")
    print(f"   By module:")
    for module, count in summary['by_module'].items():
        print(f"      - {module}: {count}")
    print(f"   Average confidence: {summary['avg_confidence']:.1f}")
    
    print("\n" + "="*70)
    print("✅ EXIT ORCHESTRATOR TEST COMPLETE")
    print("="*70)
    
    return True


if __name__ == "__main__":
    import sys
    success = test_exit_orchestrator()
    sys.exit(0 if success else 1)

