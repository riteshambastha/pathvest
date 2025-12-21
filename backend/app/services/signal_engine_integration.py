"""
Signal Engine Integration for Backtest Orchestrator
Integrates comprehensive signal engine with backtesting workflow
"""

from datetime import datetime, date, timedelta
from typing import Dict, List, Optional
import pandas as pd

from app.services.signal_engine import (
    DoublingDownSignal,
    InsiderBuyingSignal,
    HerdingSignal,
    TechnicalFilters,
    ConvictionScorer,
    UniverseFilter,
    InvestorFilter,
    StockFilter,
    SignalAggregator
)


class SignalEngineIntegration:
    """
    Integrates Signal Engine with Backtest Orchestrator
    Provides high-level interface for generating trading signals
    """
    
    def __init__(self, postgres_service = None):
        self.bq_client = bq_client
        
        # Initialize signal engine components
        self.doubling_down = DoublingDownSignal()
        self.insider_buying = InsiderBuyingSignal()
        self.herding = HerdingSignal()
        self.technical_filters = TechnicalFilters()
        self.conviction_scorer = ConvictionScorer()
        self.universe_filter = UniverseFilter()
        self.investor_filter = InvestorFilter()
        self.stock_filter = StockFilter()
        self.signal_aggregator = SignalAggregator()
    
    async def generate_comprehensive_signals(
        self,
        start_date: str,
        end_date: str,
        selected_institutions: List[str],
        strategy_config: Dict,
        price_data_dict: Optional[Dict[str, pd.DataFrame]] = None
    ) -> Dict:
        """
        Generate comprehensive trading signals using all signal types
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            selected_institutions: List of institution CIKs
            strategy_config: Strategy configuration
            price_data_dict: Optional price data for technical confirmation
            
        Returns:
            Dict with:
                - signals: List of trading signals
                - candidates: List of ranked candidates
                - statistics: Signal generation statistics
        """
        
        print(f"\n{'='*60}")
        print(f"🎯 COMPREHENSIVE SIGNAL ENGINE")
        print(f"{'='*60}")
        
        # Convert dates
        start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        # Step 1: Get universe
        print(f"\n1. Filtering universe...")
        universe = await self.universe_filter.get_universe_at_date(
            as_of_date=end_dt,
            index_name=strategy_config.get('index_membership', 'ALL'),
            min_market_cap=strategy_config.get('min_market_cap', 3_000_000_000)
        )
        print(f"   ✅ Universe: {len(universe)} stocks")
        
        # Step 2: Get qualified investors
        print(f"\n2. Filtering investors...")
        if selected_institutions:
            # Use selected institutions
            qualified_investors = [
                {"cik": cik, "institution_name": f"Institution_{cik}"}
                for cik in selected_institutions
            ]
        else:
            # Get qualified investors from filters
            qualified_investors = await self.investor_filter.get_qualified_investors(
                as_of_date=end_dt,
                min_aum=strategy_config.get('min_investor_aum', 1_000_000_000)
            )
        print(f"   ✅ Investors: {len(qualified_investors)} institutions")
        
        # Step 3: Filter stocks (create sub-universe)
        print(f"\n3. Creating sub-universe...")
        sub_universe = await self.stock_filter.filter_by_market_cap(
            stocks=universe,
            min_market_cap=strategy_config.get('min_stock_market_cap', 3_000_000_000)
        )
        print(f"   ✅ Sub-universe: {len(sub_universe)} stocks")
        
        # Step 4: Generate all signals
        print(f"\n4. Generating signals...")
        all_signals = await self.signal_aggregator.generate_all_signals(
            qualified_investors=qualified_investors,
            sub_universe=sub_universe,
            current_quarter_end=end_dt,
            filing_date=end_dt
        )
        
        # Count signals
        num_doubling_down = len(all_signals.get('doubling_down', []))
        num_insider_buying = len(all_signals.get('insider_buying', []))
        num_herding = len(all_signals.get('institutional_herding', []))
        total_signals = num_doubling_down + num_insider_buying + num_herding
        
        print(f"   ✅ Generated {total_signals} total signals:")
        print(f"      - Doubling Down: {num_doubling_down}")
        print(f"      - Insider Buying: {num_insider_buying}")
        print(f"      - Herding: {num_herding}")
        
        # Step 5: Create primary candidate list
        print(f"\n5. Creating primary candidate list...")
        candidates = await self.signal_aggregator.create_primary_candidate_list(all_signals)
        print(f"   ✅ Primary candidates: {len(candidates)} stocks")
        
        # Step 6: Apply technical confirmation if price data provided
        if price_data_dict and strategy_config.get('apply_technical_confirmation', True):
            print(f"\n6. Applying technical confirmation...")
            confirmed_candidates = await self.apply_technical_confirmation(
                candidates=candidates,
                price_data_dict=price_data_dict,
                signal_date=end_dt
            )
            print(f"   ✅ Technically confirmed: {len(confirmed_candidates)} stocks")
            candidates = confirmed_candidates
        
        # Step 7: Rank by conviction
        print(f"\n7. Ranking by conviction...")
        ranked_candidates = []
        for candidate in candidates:
            herding_score = self.conviction_scorer.calculate_herding_score(candidate)
            insider_score = self.conviction_scorer.calculate_insider_score(candidate)
            conviction_score = self.conviction_scorer.calculate_conviction_score(candidate)
            
            ranked_candidates.append({
                **candidate,
                'herding_score': herding_score,
                'insider_score': insider_score,
                'conviction_score': conviction_score
            })
        
        # Sort by conviction score
        ranked_candidates.sort(key=lambda x: x['conviction_score'], reverse=True)
        print(f"   ✅ Candidates ranked by conviction")
        
        # Show top 10
        if ranked_candidates:
            print(f"\n📊 Top 10 Signals by Conviction:")
            for i, cand in enumerate(ranked_candidates[:10], 1):
                ticker = cand.get('ticker', 'N/A')
                conviction = cand.get('conviction_score', 0)
                signals = cand.get('triggered_signals', [])
                print(f"   {i:2d}. {ticker:6s} | Conviction: {conviction:5.1f} | Signals: {len(signals)}")
        
        # Prepare result
        result = {
            'signals': ranked_candidates,
            'candidates': ranked_candidates[:strategy_config.get('max_positions', 20)],
            'statistics': {
                'universe_size': len(universe),
                'qualified_investors': len(qualified_investors),
                'sub_universe_size': len(sub_universe),
                'total_signals': total_signals,
                'signal_breakdown': {
                    'doubling_down': num_doubling_down,
                    'insider_buying': num_insider_buying,
                    'herding': num_herding
                },
                'primary_candidates': len(candidates),
                'final_candidates': len(ranked_candidates[:strategy_config.get('max_positions', 20)])
            }
        }
        
        print(f"\n{'='*60}")
        print(f"✅ Signal Generation Complete")
        print(f"{'='*60}\n")
        
        return result
    
    async def apply_technical_confirmation(
        self,
        candidates: List[Dict],
        price_data_dict: Dict[str, pd.DataFrame],
        signal_date: date
    ) -> List[Dict]:
        """
        Apply technical confirmation filters to candidates
        
        Args:
            candidates: List of candidate stocks
            price_data_dict: Dictionary of ticker -> price DataFrame
            signal_date: Signal date for technical check
            
        Returns:
            List of candidates that pass technical confirmation
        """
        
        confirmed_candidates = []
        
        for candidate in candidates:
            ticker = candidate.get('ticker')
            if not ticker:
                continue
            
            price_data = price_data_dict.get(ticker)
            if price_data is None or len(price_data) == 0:
                continue
            
            # Check technical confirmation
            confirmation = await self.technical_filters.check_technical_confirmation(
                ticker=ticker,
                signal_date=signal_date,
                lookback_days=200
            )
            
            if confirmation and confirmation.get('confirmed', False):
                candidate['technical_confirmation'] = confirmation
                confirmed_candidates.append(candidate)
        
        return confirmed_candidates
    
    def convert_signals_to_backtest_format(self, signals: List[Dict]) -> List[Dict]:
        """
        Convert signal engine output to backtest engine format
        
        Args:
            signals: List of signals from signal engine
            
        Returns:
            List of signals in backtest format
        """
        
        backtest_signals = []
        
        for signal in signals:
            backtest_signal = {
                'ticker': signal.get('ticker'),
                'signal_date': signal.get('filing_date') or signal.get('signal_date'),
                'signal_type': signal.get('signal_type', 'unknown'),
                'institution_cik': signal.get('cik'),
                'institution_name': signal.get('institution_name'),
                'conviction_score': signal.get('conviction_score', 50),
                'details': signal.get('details', {})
            }
            backtest_signals.append(backtest_signal)
        
        return backtest_signals


# Singleton instance
_signal_engine_integration = None

def get_signal_engine_integration(postgres_service = None):
    """Get or create signal engine integration instance"""
    global _signal_engine_integration
    if _signal_engine_integration is None:
        _signal_engine_integration = SignalEngineIntegration(bq_client)
    return _signal_engine_integration

