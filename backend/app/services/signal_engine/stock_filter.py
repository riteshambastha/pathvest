"""
Stock Filter - FR-3.1.C.3 (Parts 2 & 3)
Filters stocks based on characteristics and transaction patterns
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import date, timedelta
from app.services.postgres_service import get_postgres_service


class StockFilter:
    """
    Filter stocks based on characteristics and institutional transaction patterns
    
    Stock Characteristics (FR-3.1.C.3 Part 2):
    - Market Cap: > $3B
    - Index Membership: S&P 1500
    
    Transaction Filters (FR-3.1.C.3 Part 3):
    - Min Buy Value: > $10M in primary and secondary quarters
    - Share count increase > 5%
    - Combined 2-quarter purchase ≥ 2% of average AUM
    """
    
    DEFAULT_MIN_MARKET_CAP = 3_000_000_000  # $3B
    DEFAULT_MIN_BUY_VALUE = 10_000_000  # $10M
    DEFAULT_MIN_SHARE_INCREASE_PCT = 0.05  # 5%
    DEFAULT_MIN_AUM_PCT = 0.02  # 2%
    
    def __init__(self, market_cap_min=None, index_membership=None, postgres_service=None):
        """Initialize stock filter"""
        self.postgres_service = postgres_service  # Lazy load

        # Set filter criteria from parameters or defaults
        self.market_cap_min = market_cap_min if market_cap_min is not None else self.DEFAULT_MIN_MARKET_CAP
        self.index_membership = index_membership

    def _get_postgres_service(self):
        """Get postgres service lazily"""
        if self.postgres_service is None:
        self.postgres_service = get_postgres_service()
        return self.postgres_service

    def meets_market_cap_threshold(self, market_cap: float) -> bool:
        """Check if market cap meets minimum threshold."""
        return market_cap >= self.market_cap_min

    def is_in_index(self, ticker: str, index: str) -> bool:
        """Check if stock is in specified index."""
        if self.index_membership == "SP1500":
            # SP1500 includes SP500, SP400, SP600
            return index in ["SP500", "SP400", "SP600", "SP1500"]
        return index == self.index_membership
    
    async def filter_by_market_cap(
        self,
        stocks: List[Dict[str, Any]],
        min_market_cap: float = DEFAULT_MIN_MARKET_CAP
    ) -> List[Dict[str, Any]]:
        """
        Filter stocks by minimum market capitalization
        
        Args:
            stocks: List of stocks to filter
            min_market_cap: Minimum market cap in dollars
        
        Returns:
            Filtered list
        """
        return [
            stock for stock in stocks
            if stock.get("estimated_market_cap", 0) >= min_market_cap
        ]
    
    async def get_institutional_transactions_for_stock(
        self,
        cusip: str,
        ticker: str,
        qualified_investor_ciks: List[str],
        as_of_date: date,
        lookback_quarters: int = 2
    ) -> List[Dict[str, Any]]:
        """
        Get institutional transactions for a stock from qualified investors
        
        Args:
            cusip: Stock CUSIP
            ticker: Stock ticker
            qualified_investor_ciks: List of qualified investor CIKs
            as_of_date: Point-in-time date
            lookback_quarters: Number of quarters to look back
        
        Returns:
            List of transactions with quarter-over-quarter changes
        """
        if not self._get_postgres_service().is_available():
            return []
        
        lookback_start = as_of_date - timedelta(days=(lookback_quarters * 91))
        
        query = f"""
            WITH quarterly_holdings AS (
                -- Get holdings for this stock by qualified investors
                SELECT
                    f.cik,
                    i.name as institution_name,
                    f.period_end_date as quarter_end,
                    f.filing_date,
                    f.total_value as institution_aum_k,
                    h.shares_or_prn_amt as shares,
                    h.value as position_value_k,
                    ROW_NUMBER() OVER (
                        PARTITION BY f.cik, f.period_end_date 
                        ORDER BY f.filing_date DESC
                    ) as filing_rank
                FROM `{self._get_postgres_service()._get_table_ref('sec_holdings_13f')}` h
                JOIN `{self._get_postgres_service()._get_table_ref('sec_filings_13f')}` f
                    ON h.filing_id = f.filing_id
                JOIN `{self._get_postgres_service()._get_table_ref('sec_institutions')}` i
                    ON f.cik = i.cik
                WHERE h.cusip = @cusip
                    AND f.filing_date <= @as_of_date
                    AND f.filing_date >= @lookback_start
                    AND f.cik IN UNNEST(@qualified_ciks)
            ),
            
            holdings_with_lag AS (
                -- Calculate quarter-over-quarter changes
                SELECT
                    cik,
                    institution_name,
                    quarter_end,
                    filing_date,
                    institution_aum_k,
                    shares,
                    position_value_k,
                    LAG(shares) OVER (PARTITION BY cik ORDER BY quarter_end) as prev_shares,
                    LAG(position_value_k) OVER (PARTITION BY cik ORDER BY quarter_end) as prev_value_k,
                    LAG(institution_aum_k) OVER (PARTITION BY cik ORDER BY quarter_end) as prev_aum_k
                FROM quarterly_holdings
                WHERE filing_rank = 1  -- Most recent filing for each quarter
            )
            
            SELECT
                cik,
                institution_name,
                quarter_end,
                filing_date,
                institution_aum_k,
                shares,
                position_value_k,
                prev_shares,
                prev_value_k,
                (shares - IFNULL(prev_shares, 0)) as share_change,
                (position_value_k - IFNULL(prev_value_k, 0)) as value_change_k,
                SAFE_DIVIDE(
                    (shares - IFNULL(prev_shares, 0)),
                    NULLIF(prev_shares, 0)
                ) as share_change_pct,
                SAFE_DIVIDE(
                    (prev_aum_k + institution_aum_k),
                    2
                ) as avg_aum_k
            FROM holdings_with_lag
            ORDER BY filing_date DESC
        """
        
        params = {
            "cusip": cusip,
            "as_of_date": as_of_date,
            "lookback_start": lookback_start,
            "qualified_ciks": qualified_investor_ciks
        }
        
        try:
            results = await self._get_postgres_service().execute_query(query, params)
            return results
        except Exception as e:
            print(f"Error querying institutional transactions for {ticker}: {e}")
            return []
    
    async def filter_by_transaction_criteria(
        self,
        stock_transactions: List[Dict[str, Any]],
        min_buy_value: float = DEFAULT_MIN_BUY_VALUE,
        min_share_increase_pct: float = DEFAULT_MIN_SHARE_INCREASE_PCT,
        min_aum_pct: float = DEFAULT_MIN_AUM_PCT
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Check if stock transactions meet the transaction filter criteria
        
        Args:
            stock_transactions: List of institutional transactions for the stock
            min_buy_value: Minimum buy value in dollars
            min_share_increase_pct: Minimum share count increase percentage
            min_aum_pct: Minimum combined purchase as % of AUM
        
        Returns:
            (passes_filter, reason_dict)
        """
        if not stock_transactions:
            return False, {"reason": "No transactions found"}
        
        # Need at least 2 quarters of data (primary + secondary)
        unique_quarters = set(t.get("quarter_end") for t in stock_transactions)
        if len(unique_quarters) < 2:
            return False, {"reason": "Insufficient quarterly data (need 2+ quarters)"}
        
        # Sort by quarter (most recent first)
        sorted_txns = sorted(
            stock_transactions,
            key=lambda x: x.get("filing_date", ""),
            reverse=True
        )
        
        # Group by quarter
        quarters_data = {}
        for txn in sorted_txns:
            quarter = txn.get("quarter_end")
            if quarter not in quarters_data:
                quarters_data[quarter] = []
            quarters_data[quarter].append(txn)
        
        quarters_sorted = sorted(quarters_data.keys(), reverse=True)
        
        if len(quarters_sorted) < 2:
            return False, {"reason": "Need data for 2 consecutive quarters"}
        
        primary_quarter = quarters_sorted[0]  # Most recent
        secondary_quarter = quarters_sorted[1]  # Second most recent
        
        # Check criteria for each quarter
        results = {
            "primary_quarter": primary_quarter,
            "secondary_quarter": secondary_quarter,
            "primary_checks": {},
            "secondary_checks": {},
            "combined_checks": {}
        }
        
        # Primary quarter checks
        primary_increases = [
            txn for txn in quarters_data[primary_quarter]
            if txn.get("share_change", 0) > 0  # Positive change = increase
        ]
        
        primary_total_value = sum(
            abs(txn.get("value_change_k", 0)) * 1000  # Convert to dollars
            for txn in primary_increases
        )
        
        results["primary_checks"]["num_increases"] = len(primary_increases)
        results["primary_checks"]["total_buy_value"] = primary_total_value
        results["primary_checks"]["passes_min_buy"] = primary_total_value >= min_buy_value
        
        # Secondary quarter checks
        secondary_increases = [
            txn for txn in quarters_data[secondary_quarter]
            if txn.get("share_change", 0) > 0
        ]
        
        secondary_total_value = sum(
            abs(txn.get("value_change_k", 0)) * 1000
            for txn in secondary_increases
        )
        
        results["secondary_checks"]["num_increases"] = len(secondary_increases)
        results["secondary_checks"]["total_buy_value"] = secondary_total_value
        results["secondary_checks"]["passes_min_buy"] = secondary_total_value >= min_buy_value
        
        # Combined 2-quarter checks
        all_increases = primary_increases + secondary_increases
        
        # Check share increase percentage
        share_increases_pct = [
            txn.get("share_change_pct", 0)
            for txn in all_increases
            if txn.get("share_change_pct") is not None
        ]
        
        avg_share_increase = (
            sum(share_increases_pct) / len(share_increases_pct)
            if share_increases_pct else 0
        )
        
        results["combined_checks"]["avg_share_increase_pct"] = avg_share_increase
        results["combined_checks"]["passes_share_increase"] = avg_share_increase >= min_share_increase_pct
        
        # Check combined purchase as % of AUM
        combined_value = primary_total_value + secondary_total_value
        
        # Calculate average AUM across investors and quarters
        avg_aums = [
            txn.get("avg_aum_k", 0) * 1000  # Convert to dollars
            for txn in all_increases
            if txn.get("avg_aum_k")
        ]
        
        avg_aum = sum(avg_aums) / len(avg_aums) if avg_aums else 1
        
        purchase_pct_of_aum = combined_value / avg_aum if avg_aum > 0 else 0
        
        results["combined_checks"]["combined_purchase_value"] = combined_value
        results["combined_checks"]["avg_aum"] = avg_aum
        results["combined_checks"]["purchase_pct_of_aum"] = purchase_pct_of_aum
        results["combined_checks"]["passes_aum_pct"] = purchase_pct_of_aum >= min_aum_pct
        
        # Overall pass/fail
        passes = all([
            results["primary_checks"]["passes_min_buy"],
            results["secondary_checks"]["passes_min_buy"],
            results["combined_checks"]["passes_share_increase"],
            results["combined_checks"]["passes_aum_pct"]
        ])
        
        return passes, results
    
    async def get_stocks_with_significant_buying(
        self,
        universe: List[Dict[str, Any]],
        qualified_investor_ciks: List[str],
        as_of_date: date,
        min_buy_value: float = DEFAULT_MIN_BUY_VALUE,
        min_share_increase_pct: float = DEFAULT_MIN_SHARE_INCREASE_PCT,
        min_aum_pct: float = DEFAULT_MIN_AUM_PCT
    ) -> List[Dict[str, Any]]:
        """
        Filter universe to stocks with significant institutional buying
        
        Args:
            universe: List of stocks to check
            qualified_investor_ciks: List of qualified investor CIKs
            as_of_date: Point-in-time date
            min_buy_value: Minimum buy value per quarter
            min_share_increase_pct: Minimum share increase percentage
            min_aum_pct: Minimum combined purchase as % of AUM
        
        Returns:
            List of stocks that pass transaction filters with analysis
        """
        qualified_stocks = []
        
        for stock in universe:
            ticker = stock.get("ticker")
            cusip = stock.get("cusip")
            
            if not ticker or not cusip:
                continue
            
            # Get institutional transactions
            transactions = await self.get_institutional_transactions_for_stock(
                cusip=cusip,
                ticker=ticker,
                qualified_investor_ciks=qualified_investor_ciks,
                as_of_date=as_of_date,
                lookback_quarters=2
            )
            
            # Check if passes transaction criteria
            passes, analysis = await self.filter_by_transaction_criteria(
                stock_transactions=transactions,
                min_buy_value=min_buy_value,
                min_share_increase_pct=min_share_increase_pct,
                min_aum_pct=min_aum_pct
            )
            
            if passes:
                qualified_stocks.append({
                    **stock,
                    "transaction_analysis": analysis,
                    "num_buying_institutions": len(set(
                        t.get("cik") for t in transactions
                        if t.get("share_change", 0) > 0
                    ))
                })
        
        return qualified_stocks


# Singleton instance
_stock_filter = None


def get_stock_filter() -> StockFilter:
    """Get or create stock filter instance"""
    global _stock_filter
    if _stock_filter is None:
        _stock_filter = StockFilter()
    return _stock_filter

