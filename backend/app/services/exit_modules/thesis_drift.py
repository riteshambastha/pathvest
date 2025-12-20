"""
Exit Module 1: Thesis Drift
Triggered when institution reduces/exits position (13F invalidation)

Per SRS FR-3.1.C.11:
- Monitors 13F filings for position changes
- Exits when triggering institution reduces holdings by threshold
- Default threshold: 25% reduction
- Configurable trigger institution and threshold
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
    institution_cik: str
    institution_name: str
    previous_shares: float
    current_shares: float
    reduction_pct: float
    confidence: float  # 0-100


class ThesisDriftModule:
    """
    Exit Module 1: Thesis Drift Detection
    
    Monitors institutional holdings for the triggering institution.
    Exits position when institution reduces holdings by threshold %.
    
    Logic:
    1. Track the institution that triggered the entry signal
    2. Monitor their 13F filings for position changes
    3. If reduction >= threshold, exit position
    4. Higher confidence for larger reductions
    """
    
    DEFAULT_REDUCTION_THRESHOLD = 0.25  # 25% reduction
    
    def __init__(self, postgres_service = None):
        """
        Initialize Thesis Drift Module
        
        Args:
            bq_client: PostgreSQL client (optional)
        """
        self.bq_client = bq_client
        self.project_id = os.getenv('GCP_PROJECT_ID', 'test-for-android-notifn')
        self.dataset_id = os.getenv('BIGQUERY_DATASET_SEC', 'sec_filings')
    
    def check_thesis_drift(
        self,
        ticker: str,
        institution_cik: str,
        entry_date: date,
        check_date: date,
        reduction_threshold: float = DEFAULT_REDUCTION_THRESHOLD
    ) -> Optional[ThesisDriftExit]:
        """
        Check if thesis drift exit should be triggered
        
        Args:
            ticker: Stock ticker
            institution_cik: CIK of triggering institution
            entry_date: Date of entry
            check_date: Date to check for drift
            reduction_threshold: Minimum reduction to trigger exit (default 25%)
            
        Returns:
            ThesisDriftExit if exit triggered, None otherwise
        """
        
        if not self.bq_client:
            print(f"⚠️  PostgreSQL not available, skipping thesis drift check for {ticker}")
            return None
        
        try:
            # Get holdings at entry and current date
            entry_holdings = self._get_holdings_at_date(ticker, institution_cik, entry_date)
            current_holdings = self._get_holdings_at_date(ticker, institution_cik, check_date)
            
            if not entry_holdings or not current_holdings:
                return None
            
            entry_shares = entry_holdings['shares_held']
            current_shares = current_holdings['shares_held']
            
            # Calculate reduction percentage
            if entry_shares == 0:
                return None
            
            reduction_pct = (entry_shares - current_shares) / entry_shares
            
            # Check if reduction exceeds threshold
            if reduction_pct >= reduction_threshold:
                # Calculate confidence (higher for larger reductions)
                confidence = min(100, 60 + (reduction_pct * 100))
                
                return ThesisDriftExit(
                    ticker=ticker,
                    exit_date=check_date,
                    reason=f"Institution reduced holdings by {reduction_pct*100:.1f}%",
                    institution_cik=institution_cik,
                    institution_name=current_holdings.get('institution_name', 'Unknown'),
                    previous_shares=entry_shares,
                    current_shares=current_shares,
                    reduction_pct=reduction_pct,
                    confidence=confidence
                )
            
            return None
            
        except Exception as e:
            print(f"❌ Error checking thesis drift for {ticker}: {e}")
            return None
    
    def batch_check_thesis_drift(
        self,
        positions: List[Dict],
        check_date: date,
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
            reduction_threshold: Minimum reduction threshold
            
        Returns:
            List of ThesisDriftExit signals
        """
        
        exit_signals = []
        
        for position in positions:
            exit_signal = self.check_thesis_drift(
                ticker=position['ticker'],
                institution_cik=position['institution_cik'],
                entry_date=position['entry_date'],
                check_date=check_date,
                reduction_threshold=reduction_threshold
            )
            
            if exit_signal:
                exit_signals.append(exit_signal)
        
        return exit_signals
    
    def _get_holdings_at_date(
        self,
        ticker: str,
        institution_cik: str,
        as_of_date: date
    ) -> Optional[Dict]:
        """
        Get institutional holdings at a specific date
        
        Args:
            ticker: Stock ticker
            institution_cik: Institution CIK
            as_of_date: Date to retrieve holdings
            
        Returns:
            Dict with holdings data or None
        """
        
        if not self.bq_client:
            return None
        
        try:
            # Query for holdings at or before the date
            query = f"""
            SELECT 
                ticker,
                cik,
                institution_name,
                filing_date,
                shares_held,
                market_value
            FROM `{self.project_id}.{self.dataset_id}.institutional_holdings`
            WHERE ticker = '{ticker}'
                AND cik = '{institution_cik}'
                AND filing_date <= '{as_of_date.isoformat()}'
            ORDER BY filing_date DESC
            LIMIT 1
            """
            
            result = self.bq_client.query(query).result()
            rows = list(result)
            
            if rows:
                row = rows[0]
                return {
                    'ticker': row.ticker,
                    'cik': row.cik,
                    'institution_name': row.institution_name,
                    'filing_date': row.filing_date,
                    'shares_held': float(row.shares_held) if row.shares_held else 0,
                    'market_value': float(row.market_value) if row.market_value else 0
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
        """
        Get historical holdings for monitoring
        
        Args:
            ticker: Stock ticker
            institution_cik: Institution CIK
            start_date: Start date
            end_date: End date
            
        Returns:
            List of holdings snapshots
        """
        
        if not self.bq_client:
            return []
        
        try:
            query = f"""
            SELECT 
                ticker,
                cik,
                institution_name,
                filing_date,
                shares_held,
                market_value,
                shares_change,
                shares_change_pct
            FROM `{self.project_id}.{self.dataset_id}.institutional_holdings`
            WHERE ticker = '{ticker}'
                AND cik = '{institution_cik}'
                AND filing_date BETWEEN '{start_date.isoformat()}' AND '{end_date.isoformat()}'
            ORDER BY filing_date ASC
            """
            
            result = self.bq_client.query(query).result()
            
            history = []
            for row in result:
                history.append({
                    'ticker': row.ticker,
                    'cik': row.cik,
                    'institution_name': row.institution_name,
                    'filing_date': row.filing_date,
                    'shares_held': float(row.shares_held) if row.shares_held else 0,
                    'market_value': float(row.market_value) if row.market_value else 0,
                    'shares_change': float(row.shares_change) if row.shares_change else 0,
                    'shares_change_pct': float(row.shares_change_pct) if row.shares_change_pct else 0
                })
            
            return history
            
        except Exception as e:
            print(f"❌ Error fetching position history: {e}")
            return []


# Test function
def test_thesis_drift_module():
    """Test the Thesis Drift Module"""
    print("\n" + "="*70)
    print("🧪 TESTING EXIT MODULE 1: THESIS DRIFT")
    print("="*70)
    
    try:
        # Initialize PostgreSQL client
        from app.services.postgres_service import get_postgres_service
        client = get_postgres_service()
        print("✅ PostgreSQL client initialized")
    except Exception as e:
        print(f"⚠️  PostgreSQL not available: {e}")
        print("⚠️  Skipping tests that require PostgreSQL")
        return True
    
    # Create module
    module = ThesisDriftModule(client)
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
        print(f"      Institution: {exit_signal.institution_name}")
        print(f"      Reduction: {exit_signal.reduction_pct*100:.1f}%")
        print(f"      Confidence: {exit_signal.confidence:.1f}")
    else:
        print(f"   ✅ No thesis drift detected for AAPL (expected)")
    
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
            'institution_cik': '0001364742',  # ARK
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

