"""
Exit Modules Package
Comprehensive exit logic for portfolio management

This package provides 4 exit modules per SRS FR-3.1.C.11:
- Module 1: Thesis Drift (13F invalidation detection)
- Module 2: Insider Reversal (Form 4 insider selling)
- Module 3: Trailing Stop/Take-Profit (price-based exits)
- Module 4: Dead Money Exit (time-based stagnation)

Plus an orchestrator that coordinates all modules.
"""

from .thesis_drift import ThesisDriftModule, ThesisDriftExit
from .insider_reversal import InsiderReversalModule, InsiderReversalExit
from .trailing_stop import TrailingStopModule, TrailingStopExit
from .dead_money import DeadMoneyModule, DeadMoneyExit
from .exit_orchestrator import ExitOrchestrator, ExitDecision

__all__ = [
    # Module 1: Thesis Drift
    'ThesisDriftModule',
    'ThesisDriftExit',
    
    # Module 2: Insider Reversal
    'InsiderReversalModule',
    'InsiderReversalExit',
    
    # Module 3: Trailing Stop
    'TrailingStopModule',
    'TrailingStopExit',
    
    # Module 4: Dead Money
    'DeadMoneyModule',
    'DeadMoneyExit',
    
    # Orchestrator
    'ExitOrchestrator',
    'ExitDecision'
]

