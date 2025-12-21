"""
Signal A: Doubling Down Signal - FR-3.1.C.9
Triggered when price < estimated cost basis AND share count increased
"""

from typing import List, Dict, Any, Optional
from datetime import date, timedelta
from app.services.postgres_service import get_postgres_service
from app.services.alphavantage_service import get_alphavantage_service


class DoublingDownSignal:
    """
    Doubling Down Signal Generator
    
    Logic: Triggered if Stock Price < Investor's Estimated Cost Basis AND Share Count Increased
    
    This signal indicates conviction - the investor is buying more shares at a lower price,
    suggesting they believe the stock is undervalued.
    """
    
    def __init__(self):
        """Initialize signal generator with lazy-loaded services"""
        self._postgres_service = None
        self._alphavantage_service = None
    
    @property
    def postgres_service(self):
        """Lazy-load postgres service"""
        if self._postgres_service is None:
            self._postgres_service = get_postgres_service()
        return self._postgres_service
    
    @property
    def alphavantage_service(self):
        """Lazy-load alphavantage service"""
        if self._alphavantage_service is None:
            self._alphavantage_service = get_alphavantage_service()
        return self._alphavantage_service
    
    def evaluate(
        self,
        current_price: float,
        estimated_cost_basis: float,
        current_shares: int,
        previous_shares: int
    ) -> bool:
        """
        Evaluate if Doubling Down signal is triggered (synchronous)
        
        Signal A Logic:
        - Stock price < Investor's estimated cost basis
        - Share count increased from previous quarter
        
        Args:
            current_price: Current stock price
            estimated_cost_basis: Investor's estimated average cost
            current_shares: Current quarter share count
            previous_shares: Previous quarter share count
        
        Returns:
            True if signal is triggered
        """
        # Condition 1: Price below cost basis
        price_below_cost = current_price < estimated_cost_basis
        
        # Condition 2: Share count increased
        shares_increased = current_shares > previous_shares
        
        return price_below_cost and shares_increased
    
    async def calculate_estimated_cost_basis(
        self,
        cik: str,
        cusip: str,
        current_quarter_end: date,
        lookback_quarters: int = 4
    ) -> Optional[float]:
        """
        Calculate estimated cost basis for an investor's position
        
        Args:
            cik: Investor CIK
            cusip: Stock CUSIP
            current_quarter_end: Current quarter end date
            lookback_quarters: Quarters to look back for averaging
        
        Returns:
            Estimated cost basis per share (VWAP)
        """
        if not self.postgres_service.is_available():
            return None
        
        lookback_start = current_quarter_end - timedelta(days=lookback_quarters * 91)
        
        query = f"""
            WITH quarterly_positions AS (
                SELECT
                    f.period_end_date,
                    f.filing_date,
                    h.shares_or_prn_amt as shares,
                    h.value as value_k,
                    SAFE_DIVIDE(h.value * 1000, h.shares_or_prn_amt) as implied_price
                FROM `{self.postgres_service._get_table_ref('sec_holdings_13f')}` h
                JOIN `{self.postgres_service._get_table_ref('sec_filings_13f')}` f
                    ON h.filing_id = f.filing_id
                WHERE f.cik = @cik
                    AND h.cusip = @cusip
                    AND f.period_end_date <= @current_quarter_end
                    AND f.period_end_date >= @lookback_start
                    AND h.shares_or_prn_amt > 0
                ORDER BY f.period_end_date DESC
            )
            
            SELECT
                AVG(implied_price) as avg_cost_basis,
                SUM(shares * implied_price) / SUM(shares) as vwap_cost_basis
            FROM quarterly_positions
        """
        
        params = {
            "cik": cik,
            "cusip": cusip,
            "current_quarter_end": current_quarter_end,
            "lookback_start": lookback_start
        }
        
        try:
            results = await self.postgres_service.execute_query(query, params)
            
            if results and len(results) > 0:
                # Prefer VWAP cost basis
                return results[0].get("vwap_cost_basis") or results[0].get("avg_cost_basis")
            
            return None
        
        except Exception as e:
            print(f"Error calculating cost basis for {cik}/{cusip}: {e}")
            return None
    
    async def get_share_count_change(
        self,
        cik: str,
        cusip: str,
        current_quarter_end: date
    ) -> Optional[Dict[str, Any]]:
        """
        Get share count change from previous quarter to current quarter
        
        Args:
            cik: Investor CIK
            cusip: Stock CUSIP
            current_quarter_end: Current quarter end date
        
        Returns:
            Dict with previous_shares, current_shares, change, change_pct
        """
        if not self.postgres_service.is_available():
            return None
        
        # Get last 2 quarters of holdings
        prev_quarter_end = current_quarter_end - timedelta(days=91)
        
        query = f"""
            SELECT
                f.period_end_date,
                h.shares_or_prn_amt as shares
            FROM `{self.postgres_service._get_table_ref('sec_holdings_13f')}` h
            JOIN `{self.postgres_service._get_table_ref('sec_filings_13f')}` f
                ON h.filing_id = f.filing_id
            WHERE f.cik = @cik
                AND h.cusip = @cusip
                AND f.period_end_date IN (@current_quarter_end, @prev_quarter_end)
            ORDER BY f.period_end_date DESC
        """
        
        params = {
            "cik": cik,
            "cusip": cusip,
            "current_quarter_end": current_quarter_end,
            "prev_quarter_end": prev_quarter_end
        }
        
        try:
            results = await self.postgres_service.execute_query(query, params)
            
            if len(results) < 2:
                return None  # Need both quarters
            
            current_shares = results[0].get("shares", 0)
            prev_shares = results[1].get("shares", 0)
            
            if prev_shares == 0:
                return None  # Can't calculate change
            
            change = current_shares - prev_shares
            change_pct = (change / prev_shares) * 100
            
            return {
                "previous_shares": prev_shares,
                "current_shares": current_shares,
                "share_change": change,
                "share_change_pct": change_pct,
                "increased": change > 0
            }
        
        except Exception as e:
            print(f"Error getting share count change for {cik}/{cusip}: {e}")
            return None
    
    async def check_signal(
        self,
        cik: str,
        ticker: str,
        cusip: str,
        current_quarter_end: date,
        filing_date: date
    ) -> Optional[Dict[str, Any]]:
        """
        Check if Doubling Down signal is triggered for this position
        
        Args:
            cik: Investor CIK
            ticker: Stock ticker
            cusip: Stock CUSIP
            current_quarter_end: Quarter end date
            filing_date: Filing date (for PIT price lookup)
        
        Returns:
            Signal dict if triggered, None otherwise
        """
        # Get estimated cost basis
        cost_basis = await self.calculate_estimated_cost_basis(
            cik=cik,
            cusip=cusip,
            current_quarter_end=current_quarter_end
        )
        
        if not cost_basis:
            return None  # Can't determine cost basis
        
        # Get share count change
        share_change = await self.get_share_count_change(
            cik=cik,
            cusip=cusip,
            current_quarter_end=current_quarter_end
        )
        
        if not share_change or not share_change.get("increased"):
            return None  # Share count didn't increase
        
        # Get current stock price (as of filing date for PIT accuracy)
        try:
            # For PIT, we need price as of filing date
            # In production, query historical price; for now use recent quote
            quote = await self.alphavantage_service.get_quote(ticker)
            current_price = quote.get("price", 0)
        except Exception as e:
            print(f"Error getting price for {ticker}: {e}")
            return None
        
        if current_price >= cost_basis:
            return None  # Price is not below cost basis
        
        # Signal triggered!
        discount_pct = ((cost_basis - current_price) / cost_basis) * 100
        
        return {
            "signal_type": "doubling_down",
            "ticker": ticker,
            "cusip": cusip,
            "cik": cik,
            "signal_date": filing_date.isoformat(),
            "current_price": current_price,
            "estimated_cost_basis": cost_basis,
            "discount_pct": discount_pct,
            "previous_shares": share_change["previous_shares"],
            "current_shares": share_change["current_shares"],
            "share_change": share_change["share_change"],
            "share_change_pct": share_change["share_change_pct"],
            "conviction_indicator": "high" if discount_pct > 15 else "medium"
        }
    
    async def generate_signals(
        self,
        qualified_investors: List[Dict[str, Any]],
        sub_universe: List[Dict[str, Any]],
        current_quarter_end: date,
        filing_date: date
    ) -> List[Dict[str, Any]]:
        """
        Generate Doubling Down signals for all qualified investor-stock pairs
        
        Args:
            qualified_investors: List of qualified institutional investors
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
            
            # Check each qualified investor's position
            for cik in investor_ciks:
                signal = await self.check_signal(
                    cik=cik,
                    ticker=ticker,
                    cusip=cusip,
                    current_quarter_end=current_quarter_end,
                    filing_date=filing_date
                )
                
                if signal:
                    signals.append(signal)
        
        return signals


# Singleton instance
_doubling_down_signal = None


def get_doubling_down_signal() -> DoublingDownSignal:
    """Get or create Doubling Down signal generator instance"""
    global _doubling_down_signal
    if _doubling_down_signal is None:
        _doubling_down_signal = DoublingDownSignal()
    return _doubling_down_signal

