"""
Unit tests for Signal Engine modules.
"""

import pytest
from datetime import datetime, timedelta
from app.services.signal_engine.investor_filter import InvestorFilter
from app.services.signal_engine.stock_filter import StockFilter
from app.services.signal_engine.conviction_scorer import ConvictionScorer


class TestInvestorFilter:
    """Test investor qualification filters."""
    
    def test_aum_filter(self):
        """Test minimum AUM filter."""
        filter_obj = InvestorFilter(aum_min=1e9)
        
        # Should pass
        assert filter_obj.meets_aum_threshold(1.5e9) == True
        assert filter_obj.meets_aum_threshold(1e9) == True
        
        # Should fail
        assert filter_obj.meets_aum_threshold(0.5e9) == False
    
    def test_track_record_filter(self):
        """Test track record (consecutive quarters) filter."""
        filter_obj = InvestorFilter(track_record_quarters=8)
        
        # 8 consecutive quarters
        quarters = [
            datetime(2023, 12, 31),
            datetime(2023, 9, 30),
            datetime(2023, 6, 30),
            datetime(2023, 3, 31),
            datetime(2022, 12, 31),
            datetime(2022, 9, 30),
            datetime(2022, 6, 30),
            datetime(2022, 3, 31),
        ]
        
        assert filter_obj.has_sufficient_track_record(quarters) == True
        
        # Only 6 quarters
        assert filter_obj.has_sufficient_track_record(quarters[:6]) == False
    
    def test_concentration_filter(self):
        """Test max concentration filter."""
        filter_obj = InvestorFilter(concentration_max=0.35)
        
        portfolio = [
            {"value": 30e6},  # 30%
            {"value": 20e6},  # 20%
            {"value": 50e6},  # 50% - too concentrated
        ]
        total_aum = 100e6
        
        assert filter_obj.meets_concentration_limit(portfolio, total_aum) == False
        
        # Balanced portfolio
        balanced = [
            {"value": 25e6},  # 25%
            {"value": 25e6},  # 25%
            {"value": 50e6},  # 50% split across others
        ]
        
        assert filter_obj.meets_concentration_limit(balanced, total_aum) == True
    
    def test_turnover_filter(self):
        """Test max turnover filter."""
        filter_obj = InvestorFilter(turnover_max=0.40)
        
        # Turnover = (Min(Purchases, Sales) * 2) / Avg Portfolio Value
        purchases = 20e6
        sales = 15e6
        avg_portfolio_value = 100e6
        
        # Turnover = (15M * 2) / 100M = 0.30 (30%)
        assert filter_obj.meets_turnover_limit(purchases, sales, avg_portfolio_value) == True
        
        # High turnover
        high_purchases = 50e6
        high_sales = 40e6
        # Turnover = (40M * 2) / 100M = 0.80 (80%)
        assert filter_obj.meets_turnover_limit(high_purchases, high_sales, avg_portfolio_value) == False


class TestStockFilter:
    """Test stock qualification filters."""
    
    def test_market_cap_filter(self):
        """Test minimum market cap filter."""
        filter_obj = StockFilter(market_cap_min=3e9)
        
        assert filter_obj.meets_market_cap_threshold(5e9) == True
        assert filter_obj.meets_market_cap_threshold(3e9) == True
        assert filter_obj.meets_market_cap_threshold(1e9) == False
    
    def test_index_membership_filter(self):
        """Test S&P index membership filter."""
        filter_obj = StockFilter(index_membership="SP1500")
        
        # SP1500 includes all three indices
        assert filter_obj.is_in_index("AAPL", "SP500") == True
        assert filter_obj.is_in_index("MSFT", "SP400") == True
        assert filter_obj.is_in_index("TSLA", "SP600") == True
        
        # Specific index requirement
        filter_sp500 = StockFilter(index_membership="SP500")
        assert filter_sp500.is_in_index("AAPL", "SP500") == True
        assert filter_sp500.is_in_index("SMALLCAP", "SP600") == False


class TestConvictionScorer:
    """Test conviction ranking algorithm."""
    
    def test_herding_score_calculation(self):
        """Test institutional herding score."""
        scorer = ConvictionScorer(herding_weight=0.6, insider_weight=0.4)
        
        # 5 institutions buying, total increase 10M shares
        herding_data = {
            "num_institutions": 5,
            "net_share_increase": 10000000,
            "total_institutions": 50  # 10% of funds buying
        }
        
        score = scorer.calculate_herding_score(herding_data)
        
        assert 0 <= score <= 100
        assert score > 50  # Strong herding should score high
    
    def test_insider_confidence_score(self):
        """Test insider confidence score."""
        scorer = ConvictionScorer(herding_weight=0.6, insider_weight=0.4)
        
        # C-level insiders bought $500K in last 90 days
        insider_data = {
            "num_insiders": 3,
            "total_purchase_value": 500000,
            "avg_purchase_size": 166667
        }
        
        score = scorer.calculate_insider_score(insider_data)
        
        assert 0 <= score <= 100
        assert score > 60  # Strong insider buying
    
    def test_composite_conviction_score(self):
        """Test composite conviction score."""
        scorer = ConvictionScorer(herding_weight=0.6, insider_weight=0.4)
        
        herding_score = 80
        insider_score = 70
        
        # Expected: (0.6 * 80) + (0.4 * 70) = 48 + 28 = 76
        composite = scorer.calculate_composite_score(herding_score, insider_score)
        
        assert composite == 76.0
    
    def test_ranking_with_tie_breaking(self):
        """Test ranking with market cap tie-breaking."""
        scorer = ConvictionScorer(herding_weight=0.6, insider_weight=0.4)
        
        candidates = [
            {"ticker": "AAPL", "conviction_score": 85, "market_cap": 3e12},
            {"ticker": "MSFT", "conviction_score": 85, "market_cap": 2.5e12},  # Lower cap, higher rank
            {"ticker": "GOOGL", "conviction_score": 90, "market_cap": 2e12},
        ]
        
        ranked = scorer.rank_candidates(candidates)
        
        # GOOGL should be #1 (highest score)
        assert ranked[0]["ticker"] == "GOOGL"
        
        # MSFT should be #2 (same score as AAPL but lower cap)
        assert ranked[1]["ticker"] == "MSFT"
        
        # AAPL should be #3
        assert ranked[2]["ticker"] == "AAPL"


class TestSignalGeneration:
    """Test primary signal generation."""
    
    def test_doubling_down_signal(self):
        """Test Signal A: Doubling Down."""
        from app.services.signal_engine.signal_doubling_down import DoublingDownSignal
        
        signal = DoublingDownSignal()
        
        # Stock price below cost basis AND share count increased
        result = signal.evaluate(
            current_price=150.00,
            estimated_cost_basis=160.00,
            current_shares=10000000,
            previous_shares=8000000
        )
        
        assert result == True
        
        # Price above cost basis
        result_fail = signal.evaluate(
            current_price=170.00,
            estimated_cost_basis=160.00,
            current_shares=10000000,
            previous_shares=8000000
        )
        
        assert result_fail == False
    
    def test_insider_buying_signal(self):
        """Test Signal B: Insider Buying."""
        from app.services.signal_engine.signal_insider_buying import InsiderBuyingSignal
        
        signal = InsiderBuyingSignal()
        
        # Large inst buy AND insider buy > 10% increase
        result = signal.evaluate(
            institutional_buy_value=20e6,
            insider_holdings_increase_pct=0.15
        )
        
        assert result == True
        
        # Insider increase too small
        result_fail = signal.evaluate(
            institutional_buy_value=20e6,
            insider_holdings_increase_pct=0.05
        )
        
        assert result_fail == False
    
    def test_herding_signal(self):
        """Test Signal C: Institutional Herding."""
        from app.services.signal_engine.signal_herding import HerdingSignal
        
        signal = HerdingSignal()
        
        # 1 large leader + 2+ followers
        result = signal.evaluate(
            leader_buy_value=30e6,
            num_followers=3,
            follower_total_value=50e6
        )
        
        assert result == True
        
        # Only 1 follower
        result_fail = signal.evaluate(
            leader_buy_value=30e6,
            num_followers=1,
            follower_total_value=10e6
        )
        
        assert result_fail == False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

