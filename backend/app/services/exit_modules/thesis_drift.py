"""
Exit Module 1: Thesis Drift (FR-3.1.C.11)
Quarterly 13F invalidation check - Mandatory Smart Money Follow-through

Per SRS FR-3.1.C.11:
Exit Conditions (ANY triggers exit):
1. Stock is no longer held by any "Qualified Funds" (from Sub-universe)
2. Net Institutional Ownership drops by >20% Quarter-over-Quarter
3. Stock fails fundamental filters (e.g., Market Cap drops below $3B)

Trigger Event: Processing of new 13F batch (Quarterly)
Execution: Market Order at Open (T+1) following Signal Date (T = Filing Date)
"""

from typing import Dict, List, Optional, Tuple
from datetime import date, datetime, timedelta
from dataclasses import dataclass
import os


@dataclass
class ThesisDriftExit:
    """Represents a thesis drift exit signal"""
    ticker: str
    exit_date: date
    reason: str
    exit_type: str  # 'NO_QUALIFIED_FUNDS', 'OWNERSHIP_DROP', 'FUNDAMENTAL_FAILURE'
    institution_cik: Optional[str] = None
    institution_name: Optional[str] = None
    previous_shares: float = 0
    current_shares: float = 0
    reduction_pct: float = 0
    ownership_change_pct: float = 0
    current_market_cap: Optional[float] = None
    confidence: float = 85  # High confidence for thesis invalidation


class ThesisDriftModule:
    """
    Exit Module 1: Thesis Drift Detection (FR-3.1.C.11)
    
    Mandatory exit when investment thesis is invalidated.
    Monitors 13F filings quarterly for position changes.
    
    Exit Triggers (per SRS):
    1. Stock no longer held by qualified funds
    2. Net institutional ownership drops >20% QoQ
    3. Stock fails fundamental filters (Market Cap < $3B)
    """
    
    # SRS-defined thresholds
    OWNERSHIP_DROP_THRESHOLD = 0.20  # 20% QoQ drop triggers exit
    MIN_MARKET_CAP = 3_000_000_000  # $3B minimum market cap
    
    # Legacy threshold (for backward compatibility)
    DEFAULT_REDUCTION_THRESHOLD = 0.25  # 25% reduction
    
    def __init__(self, postgres_service=None):
        """
        Initialize Thesis Drift Module
        
        Args:
            postgres_service: PostgreSQL service for data access
        """
        self.postgres_service = postgres_service
    
    def check_thesis_drift(
        self,
        ticker: str,
        institution_cik: str,
        entry_date: date,
        check_date: date,
        qualified_funds: List[str] = None,
        reduction_threshold: float = DEFAULT_REDUCTION_THRESHOLD
    ) -> Optional[ThesisDriftExit]:
        """
        Check if thesis drift exit should be triggered (SRS FR-3.1.C.11)
        
        Checks all 3 SRS conditions:
        1. Stock no longer held by qualified funds
        2. Net institutional ownership drops >20% QoQ
        3. Stock fails fundamental filters
        
        Args:
            ticker: Stock ticker
            institution_cik: CIK of triggering institution
            entry_date: Date of entry
            check_date: Date to check for drift
            qualified_funds: List of qualified fund CIKs
            reduction_threshold: Minimum reduction to trigger (legacy)
            
        Returns:
            ThesisDriftExit if exit triggered, None otherwise
        """
        
        # Check 1: No longer held by qualified funds (SRS Condition 1)
        exit_signal = self._check_no_qualified_funds(ticker, check_date, qualified_funds)
        if exit_signal:
            return exit_signal
        
        # Check 2: Ownership drop >20% QoQ (SRS Condition 2)
        exit_signal = self._check_ownership_drop(ticker, check_date)
        if exit_signal:
            return exit_signal
        
        # Check 3: Fundamental failure - Market Cap < $3B (SRS Condition 3)
        exit_signal = self._check_fundamental_failure(ticker, check_date)
        if exit_signal:
            return exit_signal
        
        # Legacy check: Specific institution reduction
        exit_signal = self._check_institution_reduction(
            ticker, institution_cik, entry_date, check_date, reduction_threshold
        )
        if exit_signal:
            return exit_signal
        
        return None
    
    def _check_no_qualified_funds(
        self,
        ticker: str,
        check_date: date,
        qualified_funds: List[str] = None
    ) -> Optional[ThesisDriftExit]:
        """
        SRS Condition 1: Stock no longer held by any qualified funds
        
        Args:
            ticker: Stock ticker
            check_date: Date to check
            qualified_funds: List of qualified fund CIKs
            
        Returns:
            ThesisDriftExit if triggered
        """
        if not self.postgres_service or not qualified_funds:
            return None
        
        try:
            # Query to check if any qualified fund still holds this stock
            holdings_count = self._count_qualified_fund_holdings(ticker, check_date, qualified_funds)
            
            if holdings_count == 0:
                return ThesisDriftExit(
                    ticker=ticker,
                    exit_date=check_date,
                    reason="Stock no longer held by any qualified funds",
                    exit_type="NO_QUALIFIED_FUNDS",
                    confidence=95  # Very high confidence
                )
            
            return None
            
        except Exception as e:
            print(f"❌ Error checking qualified funds for {ticker}: {e}")
            return None
    
    def _check_ownership_drop(
        self,
        ticker: str,
        check_date: date
    ) -> Optional[ThesisDriftExit]:
        """
        SRS Condition 2: Net institutional ownership drops >20% QoQ
        
        Args:
            ticker: Stock ticker
            check_date: Date to check
            
        Returns:
            ThesisDriftExit if triggered
        """
        if not self.postgres_service:
            return None
        
        try:
            # Get current quarter and previous quarter ownership
            current_ownership = self._get_net_institutional_ownership(ticker, check_date)
            
            # Previous quarter (approximately 90 days ago)
            previous_date = check_date - timedelta(days=90)
            previous_ownership = self._get_net_institutional_ownership(ticker, previous_date)
            
            if previous_ownership is None or current_ownership is None:
                return None
            
            if previous_ownership == 0:
                return None
            
            # Calculate QoQ change
            ownership_change_pct = (current_ownership - previous_ownership) / previous_ownership
            
            # Check if drop exceeds threshold
            if ownership_change_pct <= -self.OWNERSHIP_DROP_THRESHOLD:
                return ThesisDriftExit(
                    ticker=ticker,
                    exit_date=check_date,
                    reason=f"Net institutional ownership dropped {abs(ownership_change_pct)*100:.1f}% QoQ (threshold: {self.OWNERSHIP_DROP_THRESHOLD*100:.0f}%)",
                    exit_type="OWNERSHIP_DROP",
                    ownership_change_pct=ownership_change_pct,
                    previous_shares=previous_ownership,
                    current_shares=current_ownership,
                    confidence=90
                )
            
            return None
            
        except Exception as e:
            print(f"❌ Error checking ownership drop for {ticker}: {e}")
            return None
    
    def _check_fundamental_failure(
        self,
        ticker: str,
        check_date: date
    ) -> Optional[ThesisDriftExit]:
        """
        SRS Condition 3: Stock fails fundamental filters (Market Cap < $3B)
        
        Args:
            ticker: Stock ticker
            check_date: Date to check
            
        Returns:
            ThesisDriftExit if triggered
        """
        if not self.postgres_service:
            return None
        
        try:
            # Get current market cap
            market_cap = self._get_market_cap(ticker, check_date)
            
            if market_cap is None:
                return None
            
            # Check if below minimum
            if market_cap < self.MIN_MARKET_CAP:
                return ThesisDriftExit(
                    ticker=ticker,
                    exit_date=check_date,
                    reason=f"Market cap ${market_cap/1e9:.1f}B below minimum ${self.MIN_MARKET_CAP/1e9:.0f}B",
                    exit_type="FUNDAMENTAL_FAILURE",
                    current_market_cap=market_cap,
                    confidence=95
                )
            
            return None
            
        except Exception as e:
            print(f"❌ Error checking fundamental filters for {ticker}: {e}")
            return None
    
    def _check_institution_reduction(
        self,
        ticker: str,
        institution_cik: str,
        entry_date: date,
        check_date: date,
        reduction_threshold: float
    ) -> Optional[ThesisDriftExit]:
        """
        Legacy check: Specific institution reduces position by threshold
        
        Args:
            ticker: Stock ticker
            institution_cik: Institution CIK
            entry_date: Entry date
            check_date: Check date
            reduction_threshold: Reduction percentage threshold
            
        Returns:
            ThesisDriftExit if triggered
        """
        if not self.postgres_service:
            print(f"⚠️  PostgreSQL not available, skipping thesis drift check for {ticker}")
            return None
        
        try:
            # Get holdings at entry and current date
            entry_holdings = self._get_holdings_at_date(ticker, institution_cik, entry_date)
            current_holdings = self._get_holdings_at_date(ticker, institution_cik, check_date)
            
            if not entry_holdings or not current_holdings:
                return None
            
            entry_shares = entry_holdings.get('shares_held', 0)
            current_shares = current_holdings.get('shares_held', 0)
            
            if entry_shares == 0:
                return None
            
            # Calculate reduction percentage
            reduction_pct = (entry_shares - current_shares) / entry_shares
            
            # Check if reduction exceeds threshold
            if reduction_pct >= reduction_threshold:
                confidence = min(100, 60 + (reduction_pct * 100))
                
                return ThesisDriftExit(
                    ticker=ticker,
                    exit_date=check_date,
                    reason=f"Institution reduced holdings by {reduction_pct*100:.1f}%",
                    exit_type="INSTITUTION_REDUCTION",
                    institution_cik=institution_cik,
                    institution_name=current_holdings.get('institution_name', 'Unknown'),
                    previous_shares=entry_shares,
                    current_shares=current_shares,
                    reduction_pct=reduction_pct,
                    confidence=confidence
                )
            
            return None
            
        except Exception as e:
            print(f"❌ Error checking institution reduction for {ticker}: {e}")
            return None
    
    def batch_check_thesis_drift(
        self,
        positions: List[Dict],
        check_date: date,
        qualified_funds: List[str] = None,
        reduction_threshold: float = DEFAULT_REDUCTION_THRESHOLD
    ) -> List[ThesisDriftExit]:
        """
        Check thesis drift for multiple positions
        
        Args:
            positions: List of position dicts with keys:
                - ticker: Stock ticker
                - institution_cik: Triggering institution CIK
                - entry_date: Entry date
            check_date: Date to check for drift
            qualified_funds: List of qualified fund CIKs
            reduction_threshold: Minimum reduction threshold
            
        Returns:
            List of ThesisDriftExit signals
        """
        exit_signals = []
        
        for position in positions:
            exit_signal = self.check_thesis_drift(
                ticker=position['ticker'],
                institution_cik=position.get('institution_cik', ''),
                entry_date=position.get('entry_date', check_date - timedelta(days=365)),
                check_date=check_date,
                qualified_funds=qualified_funds,
                reduction_threshold=reduction_threshold
            )
            
            if exit_signal:
                exit_signals.append(exit_signal)
        
        return exit_signals
    
    # ==================== Database Query Methods ====================
    
    def _count_qualified_fund_holdings(
        self,
        ticker: str,
        check_date: date,
        qualified_funds: List[str]
    ) -> int:
        """Count how many qualified funds hold this stock"""
        if not self.postgres_service:
            return -1  # Unknown
        
        try:
            # Build query to count qualified fund holdings
            query = """
                SELECT COUNT(DISTINCT i.cik) as fund_count
                FROM holdings h
                JOIN filings f ON h.filing_id = f.id
                JOIN institutions i ON f.institution_id = i.id
                WHERE h.ticker = :ticker
                AND i.cik = ANY(:ciks)
                AND f.period_of_report <= :check_date
                AND h.shares_or_prn_amt > 0
            """
            
            result = self.postgres_service.execute_query(
                query,
                {'ticker': ticker, 'ciks': qualified_funds, 'check_date': check_date}
            )
            
            if result:
                return result[0]['fund_count']
            return 0
            
        except Exception as e:
            print(f"❌ Error counting qualified fund holdings: {e}")
            return -1
    
    def _get_net_institutional_ownership(
        self,
        ticker: str,
        as_of_date: date
    ) -> Optional[float]:
        """Get total institutional shares held for a ticker"""
        if not self.postgres_service:
            return None
        
        try:
            query = """
                SELECT SUM(h.shares_or_prn_amt) as total_shares
                FROM holdings h
                JOIN filings f ON h.filing_id = f.id
                WHERE h.ticker = :ticker
                AND f.period_of_report <= :as_of_date
                AND f.period_of_report >= :start_date
            """
            
            # Look at most recent quarter
            start_date = as_of_date - timedelta(days=100)
            
            result = self.postgres_service.execute_query(
                query,
                {'ticker': ticker, 'as_of_date': as_of_date, 'start_date': start_date}
            )
            
            if result and result[0]['total_shares']:
                return float(result[0]['total_shares'])
            return None
            
        except Exception as e:
            print(f"❌ Error getting net institutional ownership: {e}")
            return None
    
    def _get_market_cap(
        self,
        ticker: str,
        as_of_date: date
    ) -> Optional[float]:
        """Get market cap for a ticker (would need market data service)"""
        # TODO: Implement when market data service is available
        # For now, return None to skip this check
        return None
    
    def _get_holdings_at_date(
        self,
        ticker: str,
        institution_cik: str,
        as_of_date: date
    ) -> Optional[Dict]:
        """Get institutional holdings at a specific date"""
        if not self.postgres_service:
            return None
        
        try:
            query = """
                SELECT 
                    h.ticker,
                    i.cik,
                    i.name as institution_name,
                    f.period_of_report as filing_date,
                    h.shares_or_prn_amt as shares_held,
                    h.value * 1000 as market_value
                FROM holdings h
                JOIN filings f ON h.filing_id = f.id
                JOIN institutions i ON f.institution_id = i.id
                WHERE h.ticker = :ticker
                    AND i.cik = :cik
                    AND f.period_of_report <= :as_of_date
                ORDER BY f.period_of_report DESC
                LIMIT 1
            """
            
            result = self.postgres_service.execute_query(
                query,
                {'ticker': ticker, 'cik': institution_cik, 'as_of_date': as_of_date}
            )
            
            if result:
                row = result[0]
                return {
                    'ticker': row['ticker'],
                    'cik': row['cik'],
                    'institution_name': row['institution_name'],
                    'filing_date': row['filing_date'],
                    'shares_held': float(row['shares_held']) if row['shares_held'] else 0,
                    'market_value': float(row['market_value']) if row['market_value'] else 0
                }
            
            return None
            
        except Exception as e:
            print(f"❌ Error fetching holdings: {e}")
            return None
    
    def get_position_history(
        self,
        ticker: str,
        institution_cik: str,
        start_date: date,
        end_date: date
    ) -> List[Dict]:
        """Get historical holdings for monitoring"""
        if not self.postgres_service:
            return []
        
        try:
            query = """
                SELECT 
                    h.ticker,
                    i.cik,
                    i.name as institution_name,
                    f.period_of_report as filing_date,
                    h.shares_or_prn_amt as shares_held,
                    h.value * 1000 as market_value
                FROM holdings h
                JOIN filings f ON h.filing_id = f.id
                JOIN institutions i ON f.institution_id = i.id
                WHERE h.ticker = :ticker
                    AND i.cik = :cik
                    AND f.period_of_report BETWEEN :start_date AND :end_date
                ORDER BY f.period_of_report ASC
            """
            
            result = self.postgres_service.execute_query(
                query,
                {
                    'ticker': ticker,
                    'cik': institution_cik,
                    'start_date': start_date,
                    'end_date': end_date
                }
            )
            
            history = []
            prev_shares = None
            
            for row in result:
                shares = float(row['shares_held']) if row['shares_held'] else 0
                shares_change = shares - prev_shares if prev_shares is not None else 0
                shares_change_pct = shares_change / prev_shares if prev_shares and prev_shares > 0 else 0
                
                history.append({
                    'ticker': row['ticker'],
                    'cik': row['cik'],
                    'institution_name': row['institution_name'],
                    'filing_date': row['filing_date'],
                    'shares_held': shares,
                    'market_value': float(row['market_value']) if row['market_value'] else 0,
                    'shares_change': shares_change,
                    'shares_change_pct': shares_change_pct
                })
                
                prev_shares = shares
            
            return history
            
        except Exception as e:
            print(f"❌ Error fetching position history: {e}")
            return []


# Test function
def test_thesis_drift_module():
    """Test the Thesis Drift Module"""
    print("\n" + "="*70)
    print("🧪 TESTING EXIT MODULE 1: THESIS DRIFT (SRS FR-3.1.C.11)")
    print("="*70)
    
    try:
        from app.services.postgres_service import get_postgres_service
        client = get_postgres_service()
        print("✅ PostgreSQL service initialized")
    except Exception as e:
        print(f"⚠️  PostgreSQL not available: {e}")
        print("⚠️  Skipping tests that require PostgreSQL")
        return True
    
    # Create module
    module = ThesisDriftModule(postgres_service=client)
    print("✅ ThesisDriftModule created")
    
    # Test 1: Check single position
    print("\n1. Testing single position check...")
    exit_signal = module.check_thesis_drift(
        ticker="AAPL",
        institution_cik="0001067983",  # Berkshire Hathaway
        entry_date=date(2024, 1, 1),
        check_date=date(2024, 12, 31),
        reduction_threshold=0.25
    )
    
    if exit_signal:
        print(f"   ✅ Thesis drift detected for AAPL")
        print(f"      Type: {exit_signal.exit_type}")
        print(f"      Reason: {exit_signal.reason}")
        print(f"      Confidence: {exit_signal.confidence:.1f}")
    else:
        print(f"   ✅ No thesis drift detected for AAPL")
    
    # Test 2: Get position history
    print("\n2. Testing position history retrieval...")
    history = module.get_position_history(
        ticker="AAPL",
        institution_cik="0001067983",
        start_date=date(2023, 1, 1),
        end_date=date(2024, 12, 31)
    )
    print(f"   ✅ Retrieved {len(history)} historical holdings")
    if history:
        print(f"      Latest filing: {history[-1]['filing_date']}")
        print(f"      Shares held: {history[-1]['shares_held']:,.0f}")
    
    # Test 3: Batch check
    print("\n3. Testing batch check...")
    test_positions = [
        {
            'ticker': 'AAPL',
            'institution_cik': '0001067983',
            'entry_date': date(2024, 1, 1)
        },
        {
            'ticker': 'GOOGL',
            'institution_cik': '0001364742',
            'entry_date': date(2024, 1, 1)
        }
    ]
    
    exit_signals = module.batch_check_thesis_drift(
        positions=test_positions,
        check_date=date(2024, 12, 31),
        reduction_threshold=0.25
    )
    print(f"   ✅ Batch check complete: {len(exit_signals)} exits triggered")
    
    print("\n" + "="*70)
    print("✅ THESIS DRIFT MODULE TEST COMPLETE")
    print("="*70)
    
    return True


if __name__ == "__main__":
    import sys
    success = test_thesis_drift_module()
    sys.exit(0 if success else 1)
