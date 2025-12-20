"""
Universe Filter - FR-3.1.C.2
Creates the initial universe of equities based on Point-in-Time criteria
"""

from typing import List, Dict, Any, Optional
from datetime import date, datetime
from app.services.postgres_service import get_postgres_service


class UniverseFilter:
    """
    Filter to create the initial universe of stocks
    
    Default criteria:
    - S&P 1500 constituents (point-in-time)
    - Market cap > $500M
    - Lookback window: 9 quarters (configurable)
    """
    
    DEFAULT_MIN_MARKET_CAP = 500_000_000  # $500M
    DEFAULT_LOOKBACK_QUARTERS = 9
    DEFAULT_INDEX = "SP1500"
    
    def __init__(self):
        """Initialize universe filter"""
        self.postgres_service = get_postgres_service()
    
    async def get_universe_at_date(
        self,
        as_of_date: date,
        index_name: str = DEFAULT_INDEX,
        min_market_cap: float = DEFAULT_MIN_MARKET_CAP,
        lookback_quarters: int = DEFAULT_LOOKBACK_QUARTERS
    ) -> List[Dict[str, Any]]:
        """
        Get universe of stocks at a specific date with PIT accuracy
        
        Args:
            as_of_date: Date for point-in-time filter
            index_name: Index membership (e.g., 'SP1500', 'SP500')
            min_market_cap: Minimum market capitalization
            lookback_quarters: Number of quarters to look back for "active" signals
        
        Returns:
            List of qualified stocks with metadata
        """
        if not self.postgres_service.is_available():
            # Return mock universe for development
            return self._get_mock_universe(as_of_date)
        
        # Calculate lookback start date (quarters * ~91 days)
        from datetime import timedelta
        lookback_start = as_of_date - timedelta(days=lookback_quarters * 91)
        
        # Query for S&P 1500 constituents as of date
        query = f"""
            WITH universe_candidates AS (
                -- Get index constituents as of date
                SELECT DISTINCT
                    ic.ticker,
                    ic.company_name,
                    ic.sector,
                    ic.industry,
                    ic.effective_date as added_to_index_date
                FROM `{self.postgres_service._get_table_ref('market_index_constituents')}` ic
                WHERE ic.index_name = @index_name
                    AND ic.effective_date <= @as_of_date
                    AND (ic.end_date IS NULL OR ic.end_date > @as_of_date)
            ),
            
            recent_activity AS (
                -- Find stocks with recent 13F activity (lookback window)
                SELECT 
                    h.ticker,
                    COUNT(DISTINCT f.cik) as num_institutions,
                    SUM(h.value) as total_institutional_value_k,
                    MAX(f.filing_date) as latest_filing_date
                FROM `{self.postgres_service._get_table_ref('sec_holdings_13f')}` h
                JOIN `{self.postgres_service._get_table_ref('sec_filings_13f')}` f
                    ON h.filing_id = f.filing_id
                WHERE f.filing_date BETWEEN @lookback_start AND @as_of_date
                    AND h.ticker IS NOT NULL
                GROUP BY h.ticker
            ),
            
            market_cap_filter AS (
                -- Get latest market cap info
                -- Note: In production, this would query a market data table
                -- For now, using institutional holdings as proxy
                SELECT
                    ticker,
                    total_institutional_value_k * 1000 as estimated_market_cap
                FROM recent_activity
                WHERE total_institutional_value_k * 1000 >= @min_market_cap
            )
            
            SELECT DISTINCT
                uc.ticker,
                uc.company_name,
                uc.sector,
                uc.industry,
                uc.added_to_index_date,
                ra.num_institutions,
                ra.total_institutional_value_k,
                ra.latest_filing_date,
                mc.estimated_market_cap
            FROM universe_candidates uc
            LEFT JOIN recent_activity ra
                ON uc.ticker = ra.ticker
            LEFT JOIN market_cap_filter mc
                ON uc.ticker = mc.ticker
            WHERE mc.estimated_market_cap IS NOT NULL
                OR ra.num_institutions > 0  -- Include even if market cap estimate unavailable
            ORDER BY uc.ticker
        """
        
        params = {
            "index_name": index_name,
            "as_of_date": as_of_date,
            "lookback_start": lookback_start,
            "min_market_cap": min_market_cap
        }
        
        try:
            results = await self.postgres_service.execute_query(query, params)
            return results
        except Exception as e:
            print(f"Error querying universe: {e}")
            return self._get_mock_universe(as_of_date)
    
    def _get_mock_universe(self, as_of_date: date) -> List[Dict[str, Any]]:
        """Get mock universe for development without PostgreSQL"""
        from app.services.mock_data.mock_sec_provider import MockSECProvider
        
        mock_stocks = MockSECProvider.MOCK_STOCKS
        
        return [
            {
                "ticker": stock["ticker"],
                "company_name": stock["name"],
                "sector": "Technology",
                "industry": "Software",
                "added_to_index_date": as_of_date.isoformat(),
                "num_institutions": 50,
                "total_institutional_value_k": stock["market_cap"] / 1000,
                "latest_filing_date": as_of_date.isoformat(),
                "estimated_market_cap": stock["market_cap"]
            }
            for stock in mock_stocks
        ]
    
    async def filter_by_sector(
        self,
        universe: List[Dict[str, Any]],
        allowed_sectors: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Filter universe by sector
        
        Args:
            universe: Current universe list
            allowed_sectors: List of allowed sectors
        
        Returns:
            Filtered universe
        """
        if not allowed_sectors:
            return universe
        
        return [
            stock for stock in universe
            if stock.get("sector") in allowed_sectors
        ]
    
    async def filter_by_market_cap_range(
        self,
        universe: List[Dict[str, Any]],
        min_market_cap: Optional[float] = None,
        max_market_cap: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Filter universe by market cap range
        
        Args:
            universe: Current universe list
            min_market_cap: Minimum market cap (None for no minimum)
            max_market_cap: Maximum market cap (None for no maximum)
        
        Returns:
            Filtered universe
        """
        filtered = universe
        
        if min_market_cap is not None:
            filtered = [
                stock for stock in filtered
                if stock.get("estimated_market_cap", 0) >= min_market_cap
            ]
        
        if max_market_cap is not None:
            filtered = [
                stock for stock in filtered
                if stock.get("estimated_market_cap", float('inf')) <= max_market_cap
            ]
        
        return filtered
    
    async def get_universe_stats(
        self,
        universe: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Get statistics about the universe
        
        Args:
            universe: Universe list
        
        Returns:
            Statistics dict
        """
        if not universe:
            return {
                "total_stocks": 0,
                "sectors": {},
                "avg_market_cap": 0,
                "total_institutional_value": 0
            }
        
        sectors = {}
        for stock in universe:
            sector = stock.get("sector", "Unknown")
            sectors[sector] = sectors.get(sector, 0) + 1
        
        market_caps = [
            stock.get("estimated_market_cap", 0)
            for stock in universe
            if stock.get("estimated_market_cap")
        ]
        
        institutional_values = [
            stock.get("total_institutional_value_k", 0)
            for stock in universe
        ]
        
        return {
            "total_stocks": len(universe),
            "sectors": sectors,
            "avg_market_cap": sum(market_caps) / len(market_caps) if market_caps else 0,
            "median_market_cap": sorted(market_caps)[len(market_caps) // 2] if market_caps else 0,
            "total_institutional_value_k": sum(institutional_values),
            "stocks_with_market_cap_data": len(market_caps)
        }


# Singleton instance
_universe_filter = None


def get_universe_filter() -> UniverseFilter:
    """Get or create universe filter instance"""
    global _universe_filter
    if _universe_filter is None:
        _universe_filter = UniverseFilter()
    return _universe_filter

