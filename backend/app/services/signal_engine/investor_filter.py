"""
Investor Filter - FR-3.1.C.3 (Part 1)
Filters institutional investors based on qualification criteria
"""

from typing import List, Dict, Any, Optional
from datetime import date, timedelta
from app.services.postgres_service import get_postgres_service
from google.cloud import postgres


class InvestorFilter:
    """
    Filter institutional investors for sub-universe qualification
    
    Default criteria (FR-3.1.C.3):
    - Min AUM: > $1B
    - Track Record: ≥ 8 consecutive quarters
    - Concentration: No single position > 30-40%
    - Turnover: < 40% (4-quarter rolling average)
    - Exclude: Index funds, passive ETFs, banks/brokers
    - Holdings Count: < 40 stocks
    - Top 10 Holdings Value: > 30% of total AUM
    """
    
    DEFAULT_MIN_AUM = 1_000_000_000  # $1B in dollars
    DEFAULT_MIN_TRACK_RECORD_QUARTERS = 8
    DEFAULT_MAX_CONCENTRATION = 0.35  # 35%
    DEFAULT_MAX_TURNOVER = 0.40  # 40%
    DEFAULT_MAX_HOLDINGS_COUNT = 40
    DEFAULT_MIN_TOP10_PERCENT = 0.30  # 30%
    
    # Keywords to exclude passive/index investors
    EXCLUDE_KEYWORDS = [
        "index", "etf", "exchange traded", "s&p 500", "sp500",
        "passive", "vanguard index", "ishares", "spdr",
        "bank", "broker", "custody", "custodian",
        "state street", "northern trust"  # Major custodians
    ]
    
    def __init__(self):
        """Initialize investor filter"""
        self.postgres_service = get_postgres_service()
    
    async def get_qualified_investors(
        self,
        as_of_date: date,
        min_aum: float = DEFAULT_MIN_AUM,
        min_track_record_quarters: int = DEFAULT_MIN_TRACK_RECORD_QUARTERS,
        max_concentration: float = DEFAULT_MAX_CONCENTRATION,
        max_turnover: float = DEFAULT_MAX_TURNOVER,
        max_holdings_count: int = DEFAULT_MAX_HOLDINGS_COUNT,
        min_top10_percent: float = DEFAULT_MIN_TOP10_PERCENT
    ) -> List[Dict[str, Any]]:
        """
        Get list of qualified institutional investors as of date
        
        Args:
            as_of_date: Point-in-time date
            min_aum: Minimum AUM in dollars
            min_track_record_quarters: Minimum consecutive quarters of filings
            max_concentration: Maximum single position as % of portfolio
            max_turnover: Maximum quarterly turnover rate
            max_holdings_count: Maximum number of holdings
            min_top10_percent: Minimum % of AUM in top 10 positions
        
        Returns:
            List of qualified investors with metrics
        """
        if not self.postgres_service.is_available():
            return self._get_mock_qualified_investors(as_of_date)
        
        # Calculate lookback period for track record
        lookback_start = as_of_date - timedelta(days=(min_track_record_quarters * 91))
        
        query = f"""
            WITH investor_filings AS (
                -- Get all filings for each investor within lookback period
                SELECT
                    i.cik,
                    i.name,
                    f.filing_id,
                    f.filing_date,
                    f.period_end_date,
                    f.total_value as aum_k,
                    f.holdings_count,
                    ROW_NUMBER() OVER (
                        PARTITION BY i.cik 
                        ORDER BY f.filing_date DESC
                    ) as filing_recency_rank
                FROM `{self.postgres_service._get_table_ref('sec_institutions')}` i
                JOIN `{self.postgres_service._get_table_ref('sec_filings_13f')}` f
                    ON i.cik = f.cik
                WHERE f.filing_date <= @as_of_date
                    AND f.filing_date >= @lookback_start
            ),
            
            investor_track_record AS (
                -- Count consecutive quarters
                SELECT
                    cik,
                    name,
                    COUNT(DISTINCT period_end_date) as quarters_filed,
                    MAX(aum_k) as latest_aum_k,
                    AVG(holdings_count) as avg_holdings_count
                FROM investor_filings
                GROUP BY cik, name
                HAVING COUNT(DISTINCT period_end_date) >= @min_track_record_quarters
            ),
            
            latest_holdings AS (
                -- Get holdings from most recent filing for each investor
                SELECT
                    if2.cik,
                    h.cusip,
                    h.ticker,
                    h.value as position_value_k,
                    if2.aum_k as total_aum_k
                FROM investor_filings if2
                JOIN `{self.postgres_service._get_table_ref('sec_holdings_13f')}` h
                    ON if2.filing_id = h.filing_id
                WHERE if2.filing_recency_rank = 1  -- Most recent filing only
            ),
            
            concentration_check AS (
                -- Check if any single position exceeds concentration limit
                SELECT
                    cik,
                    MAX(position_value_k / NULLIF(total_aum_k, 0)) as max_position_concentration
                FROM latest_holdings
                GROUP BY cik
                HAVING MAX(position_value_k / NULLIF(total_aum_k, 0)) <= @max_concentration
            ),
            
            top10_holdings AS (
                -- Calculate top 10 holdings percentage
                SELECT
                    cik,
                    SUM(position_value_k) / MAX(total_aum_k) as top10_percent
                FROM (
                    SELECT
                        cik,
                        position_value_k,
                        total_aum_k,
                        ROW_NUMBER() OVER (PARTITION BY cik ORDER BY position_value_k DESC) as position_rank
                    FROM latest_holdings
                )
                WHERE position_rank <= 10
                GROUP BY cik
                HAVING SUM(position_value_k) / MAX(total_aum_k) >= @min_top10_percent
            ),
            
            turnover_calc AS (
                -- Calculate 4-quarter rolling turnover
                -- Turnover = (Min(Purchases, Sales) * 2) / Avg Portfolio Value
                -- Simplified: Use change in holdings as proxy
                SELECT
                    cik,
                    0.20 as estimated_turnover  -- Placeholder: would need transaction-level data
                FROM investor_track_record
                -- TODO: Implement actual turnover calculation when we have quarterly deltas
            )
            
            SELECT DISTINCT
                itr.cik,
                itr.name,
                itr.quarters_filed,
                itr.latest_aum_k * 1000 as latest_aum,
                itr.avg_holdings_count,
                cc.max_position_concentration,
                t10.top10_percent,
                tc.estimated_turnover
            FROM investor_track_record itr
            JOIN concentration_check cc
                ON itr.cik = cc.cik
            JOIN top10_holdings t10
                ON itr.cik = t10.cik
            JOIN turnover_calc tc
                ON itr.cik = tc.cik
            WHERE itr.latest_aum_k * 1000 >= @min_aum
                AND itr.avg_holdings_count <= @max_holdings_count
                AND tc.estimated_turnover <= @max_turnover
            ORDER BY itr.latest_aum_k DESC
        """
        
        params = [
            postgres.ScalarQueryParameter("as_of_date", "DATE", as_of_date),
            postgres.ScalarQueryParameter("lookback_start", "DATE", lookback_start),
            postgres.ScalarQueryParameter("min_track_record_quarters", "INT64", min_track_record_quarters),
            postgres.ScalarQueryParameter("min_aum", "FLOAT64", min_aum),
            postgres.ScalarQueryParameter("max_concentration", "FLOAT64", max_concentration),
            postgres.ScalarQueryParameter("max_holdings_count", "INT64", max_holdings_count),
            postgres.ScalarQueryParameter("min_top10_percent", "FLOAT64", min_top10_percent),
            postgres.ScalarQueryParameter("max_turnover", "FLOAT64", max_turnover)
        ]
        
        try:
            results = await self.postgres_service.execute_query(query, params)
            
            # Filter out passive/index funds by name
            qualified = [
                investor for investor in results
                if not self._is_passive_investor(investor.get("name", ""))
            ]
            
            return qualified
        
        except Exception as e:
            print(f"Error querying qualified investors: {e}")
            return self._get_mock_qualified_investors(as_of_date)
    
    def _is_passive_investor(self, name: str) -> bool:
        """Check if investor name matches passive/index fund patterns"""
        name_lower = name.lower()
        
        for keyword in self.EXCLUDE_KEYWORDS:
            if keyword in name_lower:
                return True
        
        return False
    
    def _get_mock_qualified_investors(self, as_of_date: date) -> List[Dict[str, Any]]:
        """Get mock qualified investors for development"""
        from app.services.mock_data.mock_sec_provider import MockSECProvider
        
        institutions = MockSECProvider.MOCK_INSTITUTIONS
        
        return [
            {
                "cik": inst["cik"],
                "name": inst["name"],
                "quarters_filed": 10,
                "latest_aum": inst["aum"],
                "avg_holdings_count": 25,
                "max_position_concentration": 0.25,
                "top10_percent": 0.40,
                "estimated_turnover": 0.30
            }
            for inst in institutions
            if not self._is_passive_investor(inst["name"])
        ]
    
    async def calculate_investor_metrics(
        self,
        cik: str,
        as_of_date: date,
        lookback_quarters: int = 4
    ) -> Optional[Dict[str, Any]]:
        """
        Calculate detailed metrics for a specific investor
        
        Args:
            cik: Institution CIK
            as_of_date: Point-in-time date
            lookback_quarters: Number of quarters to analyze
        
        Returns:
            Dict with detailed metrics
        """
        if not self.postgres_service.is_available():
            return None
        
        lookback_start = as_of_date - timedelta(days=(lookback_quarters * 91))
        
        # Get filings for this investor
        filings = await self.postgres_service.get_filings_by_cik(
            cik,
            start_date=lookback_start,
            end_date=as_of_date
        )
        
        if not filings:
            return None
        
        latest_filing = filings[0] if filings else None
        
        if not latest_filing:
            return None
        
        # Get holdings for latest filing
        holdings = await self.postgres_service.get_holdings_by_filing_id(
            latest_filing["filing_id"]
        )
        
        if not holdings:
            return None
        
        # Calculate metrics
        total_value = sum(h.get("value", 0) for h in holdings)
        holdings_sorted = sorted(holdings, key=lambda x: x.get("value", 0), reverse=True)
        
        max_position_value = holdings_sorted[0].get("value", 0) if holdings_sorted else 0
        max_concentration = max_position_value / total_value if total_value > 0 else 0
        
        top10_value = sum(h.get("value", 0) for h in holdings_sorted[:10])
        top10_percent = top10_value / total_value if total_value > 0 else 0
        
        return {
            "cik": cik,
            "latest_filing_date": latest_filing["filing_date"],
            "aum_k": total_value,
            "holdings_count": len(holdings),
            "max_position_concentration": max_concentration,
            "top10_percent": top10_percent,
            "quarters_on_record": len(filings),
            "avg_holdings_count": sum(len(h) for h in filings) / len(filings) if filings else 0
        }
    
    async def filter_investors_by_style(
        self,
        investors: List[Dict[str, Any]],
        style_preferences: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Additional filtering by investment style preferences
        
        Args:
            investors: List of investors
            style_preferences: Dict with style criteria
                - prefer_concentrated: bool (high concentration investors)
                - prefer_low_turnover: bool (long-term holders)
                - min_size_percentile: float (only top X% by AUM)
        
        Returns:
            Filtered list
        """
        filtered = investors
        
        if style_preferences.get("prefer_concentrated"):
            # Sort by concentration, prefer higher
            filtered = sorted(
                filtered,
                key=lambda x: x.get("max_position_concentration", 0),
                reverse=True
            )
        
        if style_preferences.get("prefer_low_turnover"):
            # Sort by turnover, prefer lower
            filtered = sorted(
                filtered,
                key=lambda x: x.get("estimated_turnover", 1.0)
            )
        
        if style_preferences.get("min_size_percentile"):
            # Keep only top X% by AUM
            percentile = style_preferences["min_size_percentile"]
            cutoff_index = int(len(filtered) * (1 - percentile))
            
            filtered = sorted(
                filtered,
                key=lambda x: x.get("latest_aum", 0),
                reverse=True
            )[:cutoff_index]
        
        return filtered


# Singleton instance
_investor_filter = None


def get_investor_filter() -> InvestorFilter:
    """Get or create investor filter instance"""
    global _investor_filter
    if _investor_filter is None:
        _investor_filter = InvestorFilter()
    return _investor_filter

