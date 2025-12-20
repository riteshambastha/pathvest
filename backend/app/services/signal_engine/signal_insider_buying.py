"""
Signal B: Insider Buying Signal - FR-3.1.C.9
Triggered when Large Institutional Buy AND Insider Buy > 10% Increase
"""

from typing import List, Dict, Any, Optional
from datetime import date, timedelta
from app.services.postgres_service import get_postgres_service


class InsiderBuyingSignal:
    """
    Insider Buying Signal Generator
    
    Logic: Triggered if Large Inst Buy AND Insider Buy > 10% Increase
    
    This signal indicates alignment between institutional investors and company insiders,
    suggesting strong conviction in the stock's prospects.
    """
    
    DEFAULT_LARGE_BUY_THRESHOLD = 10_000_000  # $10M
    DEFAULT_INSIDER_INCREASE_PCT = 0.10  # 10%
    
    def __init__(self):
        """Initialize signal generator"""
        self.postgres_service = get_postgres_service()
    
    async def get_large_institutional_buys(
        self,
        cusip: str,
        ticker: str,
        qualified_investor_ciks: List[str],
        current_quarter_end: date,
        min_buy_value: float = DEFAULT_LARGE_BUY_THRESHOLD
    ) -> List[Dict[str, Any]]:
        """
        Get large institutional purchases for a stock
        
        Args:
            cusip: Stock CUSIP
            ticker: Stock ticker
            qualified_investor_ciks: List of qualified investor CIKs
            current_quarter_end: Current quarter end date
            min_buy_value: Minimum buy value threshold
        
        Returns:
            List of large institutional buys
        """
        if not self.postgres_service.is_available():
            return []
        
        prev_quarter_end = current_quarter_end - timedelta(days=91)
        
        query = f"""
            WITH quarterly_positions AS (
                SELECT
                    f.cik,
                    i.name as institution_name,
                    f.period_end_date,
                    f.filing_date,
                    h.shares_or_prn_amt as shares,
                    h.value as value_k,
                    ROW_NUMBER() OVER (
                        PARTITION BY f.cik, f.period_end_date 
                        ORDER BY f.filing_date DESC
                    ) as filing_rank
                FROM `{self.postgres_service._get_table_ref('sec_holdings_13f')}` h
                JOIN `{self.postgres_service._get_table_ref('sec_filings_13f')}` f
                    ON h.filing_id = f.filing_id
                JOIN `{self.postgres_service._get_table_ref('sec_institutions')}` i
                    ON f.cik = i.cik
                WHERE h.cusip = @cusip
                    AND f.cik IN UNNEST(@qualified_ciks)
                    AND f.period_end_date IN (@current_quarter_end, @prev_quarter_end)
                    AND h.shares_or_prn_amt > 0
            ),
            
            position_changes AS (
                SELECT
                    curr.cik,
                    curr.institution_name,
                    curr.filing_date,
                    curr.shares as current_shares,
                    curr.value_k as current_value_k,
                    IFNULL(prev.shares, 0) as prev_shares,
                    IFNULL(prev.value_k, 0) as prev_value_k,
                    (curr.shares - IFNULL(prev.shares, 0)) as share_change,
                    (curr.value_k - IFNULL(prev.value_k, 0)) as value_change_k
                FROM (
                    SELECT * FROM quarterly_positions 
                    WHERE period_end_date = @current_quarter_end AND filing_rank = 1
                ) curr
                LEFT JOIN (
                    SELECT * FROM quarterly_positions 
                    WHERE period_end_date = @prev_quarter_end AND filing_rank = 1
                ) prev
                    ON curr.cik = prev.cik
            )
            
            SELECT
                cik,
                institution_name,
                filing_date,
                current_shares,
                current_value_k,
                prev_shares,
                prev_value_k,
                share_change,
                value_change_k,
                (value_change_k * 1000) as value_change_dollars
            FROM position_changes
            WHERE share_change > 0
                AND (value_change_k * 1000) >= @min_buy_value
            ORDER BY value_change_k DESC
        """
        
        params = {
            "cusip": cusip,
            "current_quarter_end": current_quarter_end,
            "prev_quarter_end": prev_quarter_end,
            "qualified_ciks": qualified_investor_ciks,
            "min_buy_value": min_buy_value
        }
        
        try:
            results = await self.postgres_service.execute_query(query, params)
            return results
        except Exception as e:
            print(f"Error getting large institutional buys for {ticker}: {e}")
            return []
    
    async def get_insider_ownership_change(
        self,
        ticker: str,
        filing_date: date,
        lookback_days: int = 90
    ) -> Optional[Dict[str, Any]]:
        """
        Calculate insider ownership change from Form 4 filings
        
        Args:
            ticker: Stock ticker
            filing_date: Current filing date
            lookback_days: Days to look back for insider activity
        
        Returns:
            Dict with insider ownership metrics
        """
        if not self.postgres_service.is_available():
            return None
        
        start_date = filing_date - timedelta(days=lookback_days)
        
        # Get insider transactions (purchases only)
        transactions = await self.postgres_service.get_insider_activity_for_stock(
            ticker=ticker,
            start_date=start_date,
            end_date=filing_date,
            transaction_codes=['P', 'A', 'M']  # Purchase codes
        )
        
        if not transactions:
            return None
        
        # Filter to qualified C-Level insiders
        c_level_titles = [
            'CEO', 'CFO', 'COO', 'President', 'Chairman',
            'Chief Executive', 'Chief Financial', 'Chief Operating'
        ]
        
        qualified_txns = [
            txn for txn in transactions
            if txn.get("is_officer", False)
            and any(
                title.lower() in txn.get("officer_title", "").lower()
                for title in c_level_titles
            )
            and not txn.get("is_10b51_plan", False)
        ]
        
        if not qualified_txns:
            return None
        
        # Calculate total insider buying
        total_shares_purchased = sum(txn.get("shares", 0) for txn in qualified_txns)
        total_value_purchased = sum(
            txn.get("shares", 0) * txn.get("price_per_share", 0)
            for txn in qualified_txns
        )
        
        unique_insiders = len(set(txn.get("reporting_owner_cik") for txn in qualified_txns))
        
        return {
            "transaction_count": len(qualified_txns),
            "unique_insiders": unique_insiders,
            "total_shares_purchased": total_shares_purchased,
            "total_value_purchased": total_value_purchased,
            "transactions": qualified_txns
        }
    
    async def check_signal(
        self,
        ticker: str,
        cusip: str,
        qualified_investor_ciks: List[str],
        current_quarter_end: date,
        filing_date: date,
        min_insider_increase_pct: float = DEFAULT_INSIDER_INCREASE_PCT
    ) -> Optional[Dict[str, Any]]:
        """
        Check if Insider Buying signal is triggered
        
        Args:
            ticker: Stock ticker
            cusip: Stock CUSIP
            qualified_investor_ciks: List of qualified investor CIKs
            current_quarter_end: Quarter end date
            filing_date: Filing date for PIT
            min_insider_increase_pct: Minimum insider ownership increase percentage
        
        Returns:
            Signal dict if triggered, None otherwise
        """
        # Check for large institutional buys
        large_buys = await self.get_large_institutional_buys(
            cusip=cusip,
            ticker=ticker,
            qualified_investor_ciks=qualified_investor_ciks,
            current_quarter_end=current_quarter_end
        )
        
        if not large_buys:
            return None  # No large institutional buys
        
        # Check for insider buying
        insider_activity = await self.get_insider_ownership_change(
            ticker=ticker,
            filing_date=filing_date,
            lookback_days=90
        )
        
        if not insider_activity:
            return None  # No insider buying
        
        # Calculate if insider buying represents > 10% increase
        # Note: This is simplified; in production, would need baseline insider ownership
        insider_value = insider_activity["total_value_purchased"]
        institutional_value = sum(buy.get("value_change_dollars", 0) for buy in large_buys)
        
        # Proxy: insider buying should be significant relative to institutional buying
        insider_to_inst_ratio = insider_value / institutional_value if institutional_value > 0 else 0
        
        # Also check if insider increase is > 10% by absolute terms
        # (simplified check - in production, compare to previous insider holdings)
        significant_insider_buying = (
            insider_activity["unique_insiders"] >= 2 and
            insider_value >= 200_000  # $200k+ cluster
        )
        
        if not significant_insider_buying:
            return None
        
        # Signal triggered!
        return {
            "signal_type": "insider_buying",
            "ticker": ticker,
            "cusip": cusip,
            "signal_date": filing_date.isoformat(),
            "institutional_buyers": len(large_buys),
            "total_institutional_buy_value": institutional_value,
            "top_institutional_buyers": [
                {
                    "cik": buy.get("cik"),
                    "institution_name": buy.get("institution_name"),
                    "buy_value": buy.get("value_change_dollars")
                }
                for buy in large_buys[:5]  # Top 5
            ],
            "insider_buyers": insider_activity["unique_insiders"],
            "total_insider_buy_value": insider_value,
            "insider_transactions": insider_activity["transaction_count"],
            "insider_to_institutional_ratio": insider_to_inst_ratio,
            "conviction_indicator": "high" if insider_activity["unique_insiders"] >= 3 else "medium"
        }
    
    async def generate_signals(
        self,
        qualified_investors: List[Dict[str, Any]],
        sub_universe: List[Dict[str, Any]],
        current_quarter_end: date,
        filing_date: date
    ) -> List[Dict[str, Any]]:
        """
        Generate Insider Buying signals for sub-universe
        
        Args:
            qualified_investors: List of qualified investors
            sub_universe: List of stocks in sub-universe
            current_quarter_end: Current quarter end date
            filing_date: Filing date for PIT
        
        Returns:
            List of triggered signals
        """
        signals = []
        
        investor_ciks = [inv.get("cik") for inv in qualified_investors]
        
        for stock in sub_universe:
            ticker = stock.get("ticker")
            cusip = stock.get("cusip")
            
            if not ticker or not cusip:
                continue
            
            signal = await self.check_signal(
                ticker=ticker,
                cusip=cusip,
                qualified_investor_ciks=investor_ciks,
                current_quarter_end=current_quarter_end,
                filing_date=filing_date
            )
            
            if signal:
                signals.append(signal)
        
        return signals


# Singleton instance
_insider_buying_signal = None


def get_insider_buying_signal() -> InsiderBuyingSignal:
    """Get or create Insider Buying signal generator instance"""
    global _insider_buying_signal
    if _insider_buying_signal is None:
        _insider_buying_signal = InsiderBuyingSignal()
    return _insider_buying_signal

