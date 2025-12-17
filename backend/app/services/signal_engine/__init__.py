"""
Signal Engine Module
Generates trading signals from SEC filings and market data

This module provides comprehensive signal detection capabilities:
- Signal A: Doubling Down (price < cost basis + share increase)
- Signal B: Insider Buying (institutional + insider convergence)
- Signal C: Institutional Herding (leader + followers)
- Technical Confirmation (breakout, SMA, RSI)
- Conviction Ranking Algorithm
- Universe and Sub-universe Filtration
"""

from .signal_doubling_down import DoublingDownSignal
from .signal_insider_buying import InsiderBuyingSignal
from .signal_herding import HerdingSignal
from .technical_filters import TechnicalFilters
from .conviction_scorer import ConvictionScorer
from .universe_filter import UniverseFilter
from .investor_filter import InvestorFilter
from .stock_filter import StockFilter
from .insider_filter import InsiderFilter
from .signal_aggregator import SignalAggregator

__all__ = [
    'DoublingDownSignal',
    'InsiderBuyingSignal',
    'HerdingSignal',
    'TechnicalFilters',
    'ConvictionScorer',
    'UniverseFilter',
    'InvestorFilter',
    'StockFilter',
    'InsiderFilter',
    'SignalAggregator'
]

