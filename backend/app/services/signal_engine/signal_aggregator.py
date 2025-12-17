"""
Signal Aggregator - FR-3.1.C.9
Aggregates signals from all three primary signal generators
"""

from typing import List, Dict, Any
from datetime import date

from app.services.signal_engine.signal_doubling_down import get_doubling_down_signal
from app.services.signal_engine.signal_insider_buying import get_insider_buying_signal
from app.services.signal_engine.signal_herding import get_herding_signal


class SignalAggregator:
    """
    Aggregates and combines signals from multiple signal generators
    
    Step 1: Generate all 3 primary signals for the entire Sub-universe
    Step 2: Aggregate stocks that triggered ANY of the three signals
    
    This creates the "Primary Candidate List" that will then be filtered
    by technical confirmation (FR-3.1.C.9.2).
    """
    
    def __init__(self):
        """Initialize signal aggregator"""
        self.doubling_down = get_doubling_down_signal()
        self.insider_buying = get_insider_buying_signal()
        self.herding = get_herding_signal()
    
    async def generate_all_signals(
        self,
        qualified_investors: List[Dict[str, Any]],
        sub_universe: List[Dict[str, Any]],
        current_quarter_end: date,
        filing_date: date
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Generate signals from all three signal generators
        
        Args:
            qualified_investors: List of qualified institutional investors
            sub_universe: List of stocks in sub-universe
            current_quarter_end: Current quarter end date
            filing_date: Filing date for PIT accuracy
        
        Returns:
            Dict with signals from each generator
        """
        # Generate Signal A: Doubling Down
        doubling_down_signals = await self.doubling_down.generate_signals(
            qualified_investors=qualified_investors,
            sub_universe=sub_universe,
            current_quarter_end=current_quarter_end,
            filing_date=filing_date
        )
        
        # Generate Signal B: Insider Buying
        insider_buying_signals = await self.insider_buying.generate_signals(
            qualified_investors=qualified_investors,
            sub_universe=sub_universe,
            current_quarter_end=current_quarter_end,
            filing_date=filing_date
        )
        
        # Generate Signal C: Institutional Herding
        herding_signals = await self.herding.generate_signals(
            qualified_investors=qualified_investors,
            sub_universe=sub_universe,
            current_quarter_end=current_quarter_end,
            filing_date=filing_date
        )
        
        return {
            "doubling_down": doubling_down_signals,
            "insider_buying": insider_buying_signals,
            "institutional_herding": herding_signals
        }
    
    async def create_primary_candidate_list(
        self,
        all_signals: Dict[str, List[Dict[str, Any]]]
    ) -> List[Dict[str, Any]]:
        """
        Aggregate signals into a Primary Candidate List
        
        Stocks that triggered ANY of the three primary signals are included.
        
        Args:
            all_signals: Dict with signals from each generator
        
        Returns:
            List of candidate stocks with their triggered signals
        """
        # Track stocks by ticker
        candidates = {}
        
        # Process Doubling Down signals
        for signal in all_signals.get("doubling_down", []):
            ticker = signal.get("ticker")
            if ticker not in candidates:
                candidates[ticker] = {
                    "ticker": ticker,
                    "cusip": signal.get("cusip"),
                    "signal_date": signal.get("signal_date"),
                    "signals_triggered": [],
                    "conviction_indicators": []
                }
            
            candidates[ticker]["signals_triggered"].append("doubling_down")
            candidates[ticker]["conviction_indicators"].append(
                signal.get("conviction_indicator", "medium")
            )
            candidates[ticker]["doubling_down_details"] = signal
        
        # Process Insider Buying signals
        for signal in all_signals.get("insider_buying", []):
            ticker = signal.get("ticker")
            if ticker not in candidates:
                candidates[ticker] = {
                    "ticker": ticker,
                    "cusip": signal.get("cusip"),
                    "signal_date": signal.get("signal_date"),
                    "signals_triggered": [],
                    "conviction_indicators": []
                }
            
            candidates[ticker]["signals_triggered"].append("insider_buying")
            candidates[ticker]["conviction_indicators"].append(
                signal.get("conviction_indicator", "medium")
            )
            candidates[ticker]["insider_buying_details"] = signal
        
        # Process Institutional Herding signals
        for signal in all_signals.get("institutional_herding", []):
            ticker = signal.get("ticker")
            if ticker not in candidates:
                candidates[ticker] = {
                    "ticker": ticker,
                    "cusip": signal.get("cusip"),
                    "signal_date": signal.get("signal_date"),
                    "signals_triggered": [],
                    "conviction_indicators": []
                }
            
            candidates[ticker]["signals_triggered"].append("institutional_herding")
            candidates[ticker]["conviction_indicators"].append(
                signal.get("conviction_indicator", "medium")
            )
            candidates[ticker]["institutional_herding_details"] = signal
        
        # Calculate aggregate conviction
        for ticker, candidate in candidates.items():
            conviction_counts = {
                "high": candidate["conviction_indicators"].count("high"),
                "medium": candidate["conviction_indicators"].count("medium"),
                "low": candidate["conviction_indicators"].count("low")
            }
            
            # Overall conviction based on highest conviction level and number of signals
            if conviction_counts["high"] >= 2:
                aggregate_conviction = "very_high"
            elif conviction_counts["high"] >= 1:
                aggregate_conviction = "high"
            elif len(candidate["signals_triggered"]) >= 2:
                aggregate_conviction = "medium_high"
            else:
                aggregate_conviction = "medium"
            
            candidate["aggregate_conviction"] = aggregate_conviction
            candidate["num_signals_triggered"] = len(candidate["signals_triggered"])
        
        # Convert to list and sort by number of signals (most signals first)
        candidate_list = sorted(
            candidates.values(),
            key=lambda x: (x["num_signals_triggered"], x["aggregate_conviction"]),
            reverse=True
        )
        
        return candidate_list
    
    async def get_signal_statistics(
        self,
        all_signals: Dict[str, List[Dict[str, Any]]],
        primary_candidate_list: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Calculate statistics about signal generation
        
        Args:
            all_signals: Dict with signals from each generator
            primary_candidate_list: Aggregated candidate list
        
        Returns:
            Statistics dict
        """
        total_doubling_down = len(all_signals.get("doubling_down", []))
        total_insider_buying = len(all_signals.get("insider_buying", []))
        total_herding = len(all_signals.get("institutional_herding", []))
        
        # Count stocks with multiple signals
        multiple_signals = sum(
            1 for candidate in primary_candidate_list
            if candidate["num_signals_triggered"] >= 2
        )
        
        # Count by conviction
        conviction_counts = {}
        for candidate in primary_candidate_list:
            conviction = candidate.get("aggregate_conviction", "unknown")
            conviction_counts[conviction] = conviction_counts.get(conviction, 0) + 1
        
        return {
            "total_signals": total_doubling_down + total_insider_buying + total_herding,
            "by_type": {
                "doubling_down": total_doubling_down,
                "insider_buying": total_insider_buying,
                "institutional_herding": total_herding
            },
            "unique_stocks_with_signals": len(primary_candidate_list),
            "stocks_with_multiple_signals": multiple_signals,
            "stocks_with_all_three_signals": sum(
                1 for c in primary_candidate_list
                if c["num_signals_triggered"] == 3
            ),
            "conviction_distribution": conviction_counts
        }


# Singleton instance
_signal_aggregator = None


def get_signal_aggregator() -> SignalAggregator:
    """Get or create signal aggregator instance"""
    global _signal_aggregator
    if _signal_aggregator is None:
        _signal_aggregator = SignalAggregator()
    return _signal_aggregator

