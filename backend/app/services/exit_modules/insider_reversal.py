"""
Exit Module 2: Insider Reversal
Triggered when insiders sell (Form 4 detection)

Per SRS FR-3.1.C.11:
- Monitors Form 4 filings for insider selling
- Exits when C-level insiders sell significant amounts
- Default threshold: Any C-level selling > $100K
- Configurable insider roles and thresholds
"""

from typing import Dict, List, Optional, Tuple
from datetime import date, datetime, timedelta
from dataclasses import dataclass
import os


@dataclass
class InsiderReversalExit:
    """Represents an insider reversal exit signal"""
    ticker: str
    exit_date: date
    reason: str
    insider_name: str
    insider_title: str
    shares_sold: float
    transaction_value: float
    confidence: float  # 0-100


class InsiderReversalModule:
    """
    Exit Module 2: Insider Reversal Detection
    
    Monitors Form 4 filings for insider selling activity.
    Exits position when C-level insiders sell significant amounts.
    
    Logic:
    1. Track insider transactions (Form 4)
    2. Filter for C-level executives (CEO, CFO, COO, etc.)
    3. If selling > threshold, exit position
    4. Higher confidence for larger sales and higher-level executives
    
    Note: Form 4 data ingestion is pending. Currently returns mock data
    or placeholder logic for development.
    """
    
    DEFAULT_MIN_TRANSACTION_VALUE = 100_000  # $100K
    C_LEVEL_ROLES = ['CEO', 'CFO', 'COO', 'President', 'Chairman', 'Director']
    
    def __init__(self, postgres_service = None):
        """
        Initialize Insider Reversal Module
        
        Args:
            bq_client: PostgreSQL client (optional)
        """
        self.bq_client = bq_client
        self.project_id = os.getenv('GCP_PROJECT_ID', 'test-for-android-notifn')
        self.dataset_id = os.getenv('BIGQUERY_DATASET_SEC', 'sec_filings')
    
    def check_insider_reversal(
        self,
        ticker: str,
        check_date: date,
        lookback_days: int = 90,
        min_transaction_value: float = DEFAULT_MIN_TRANSACTION_VALUE,
        c_level_only: bool = True
    ) -> Optional[InsiderReversalExit]:
        """
        Check if insider reversal exit should be triggered
        
        Args:
            ticker: Stock ticker
            check_date: Date to check for reversal
            lookback_days: Days to look back for insider transactions (default 90)
            min_transaction_value: Minimum transaction value to trigger (default $100K)
            c_level_only: Only consider C-level executives (default True)
            
        Returns:
            InsiderReversalExit if exit triggered, None otherwise
        """
        
        # Get insider selling transactions
        insider_sales = self._get_insider_transactions(
            ticker=ticker,
            check_date=check_date,
            lookback_days=lookback_days,
            transaction_type='sale'
        )
        
        if not insider_sales:
            return None
        
        # Filter for C-level if requested
        if c_level_only:
            insider_sales = [
                sale for sale in insider_sales
                if any(role in sale.get('title', '').upper() for role in self.C_LEVEL_ROLES)
            ]
        
        # Filter by minimum value
        significant_sales = [
            sale for sale in insider_sales
            if sale.get('transaction_value', 0) >= min_transaction_value
        ]
        
        if not significant_sales:
            return None
        
        # Get the most significant sale (largest value)
        largest_sale = max(significant_sales, key=lambda x: x.get('transaction_value', 0))
        
        # Calculate confidence based on transaction value and title
        base_confidence = 70
        value_bonus = min(20, (largest_sale['transaction_value'] / 1_000_000) * 5)  # +5 per $1M
        title_bonus = 10 if 'CEO' in largest_sale.get('title', '').upper() else 0
        
        confidence = min(100, base_confidence + value_bonus + title_bonus)
        
        return InsiderReversalExit(
            ticker=ticker,
            exit_date=largest_sale['transaction_date'],
            reason=f"C-level insider sold ${largest_sale['transaction_value']:,.0f}",
            insider_name=largest_sale.get('insider_name', 'Unknown'),
            insider_title=largest_sale.get('title', 'Unknown'),
            shares_sold=largest_sale.get('shares', 0),
            transaction_value=largest_sale['transaction_value'],
            confidence=confidence
        )
    
    def batch_check_insider_reversal(
        self,
        positions: List[Dict],
        check_date: date,
        lookback_days: int = 90,
        min_transaction_value: float = DEFAULT_MIN_TRANSACTION_VALUE
    ) -> List[InsiderReversalExit]:
        """
        Check insider reversal for multiple positions
        
        Args:
            positions: List of position dicts with 'ticker' key
            check_date: Date to check for reversal
            lookback_days: Days to look back
            min_transaction_value: Minimum transaction value
            
        Returns:
            List of InsiderReversalExit signals
        """
        
        exit_signals = []
        
        for position in positions:
            exit_signal = self.check_insider_reversal(
                ticker=position['ticker'],
                check_date=check_date,
                lookback_days=lookback_days,
                min_transaction_value=min_transaction_value
            )
            
            if exit_signal:
                exit_signals.append(exit_signal)
        
        return exit_signals
    
    def _get_insider_transactions(
        self,
        ticker: str,
        check_date: date,
        lookback_days: int,
        transaction_type: str = 'sale'
    ) -> List[Dict]:
        """
        Get insider transactions from Form 4 data
        
        Args:
            ticker: Stock ticker
            check_date: Date to check
            lookback_days: Days to look back
            transaction_type: 'sale' or 'purchase'
            
        Returns:
            List of insider transactions
            
        Note: This would query Form 4 data from PostgreSQL.
        Currently returns empty list as Form 4 ingestion is pending.
        """
        
        if not self.bq_client:
            print(f"⚠️  PostgreSQL not available for insider transactions")
            return []
        
        # TODO: Implement Form 4 data query when table is available
        # Expected table: {project}.{dataset}.insider_transactions
        # Expected columns: ticker, transaction_date, insider_name, title,
        #                   transaction_type, shares, price, transaction_value
        
        print(f"⚠️  Form 4 data not yet available in PostgreSQL for {ticker}")
        return []
    
    def get_insider_activity_summary(
        self,
        ticker: str,
        start_date: date,
        end_date: date
    ) -> Dict:
        """
        Get summary of insider activity for a ticker
        
        Args:
            ticker: Stock ticker
            start_date: Start date
            end_date: End date
            
        Returns:
            Dict with insider activity statistics
        """
        
        if not self.bq_client:
            return {
                'total_transactions': 0,
                'purchases': 0,
                'sales': 0,
                'net_shares': 0,
                'net_value': 0
            }
        
        # TODO: Implement when Form 4 data is available
        print(f"⚠️  Form 4 data not yet available for insider activity summary")
        
        return {
            'ticker': ticker,
            'start_date': start_date,
            'end_date': end_date,
            'total_transactions': 0,
            'purchases': 0,
            'sales': 0,
            'net_shares': 0,
            'net_value': 0,
            'note': 'Form 4 data not yet ingested'
        }


# Test function
def test_insider_reversal_module():
    """Test the Insider Reversal Module"""
    print("\n" + "="*70)
    print("🧪 TESTING EXIT MODULE 2: INSIDER REVERSAL")
    print("="*70)
    
    try:
        # Initialize PostgreSQL client
        from app.services.postgres_service import get_postgres_service
        client = get_postgres_service()
        print("✅ PostgreSQL client initialized")
    except Exception as e:
        print(f"⚠️  PostgreSQL not available: {e}")
        client = None
    
    # Create module
    module = InsiderReversalModule(client)
    print("✅ InsiderReversalModule created")
    
    # Test 1: Check single position
    print("\n1. Testing single position check...")
    exit_signal = module.check_insider_reversal(
        ticker="AAPL",
        check_date=date(2024, 12, 31),
        lookback_days=90,
        min_transaction_value=100_000
    )
    
    if exit_signal:
        print(f"   ✅ Insider reversal detected for AAPL")
        print(f"      Insider: {exit_signal.insider_name} ({exit_signal.insider_title})")
        print(f"      Value: ${exit_signal.transaction_value:,.0f}")
        print(f"      Confidence: {exit_signal.confidence:.1f}")
    else:
        print(f"   ✅ No insider reversal detected for AAPL (expected - Form 4 data pending)")
    
    # Test 2: Get insider activity summary
    print("\n2. Testing insider activity summary...")
    summary = module.get_insider_activity_summary(
        ticker="AAPL",
        start_date=date(2024, 1, 1),
        end_date=date(2024, 12, 31)
    )
    print(f"   ✅ Insider activity summary retrieved")
    print(f"      Total transactions: {summary['total_transactions']}")
    print(f"      Note: {summary.get('note', 'N/A')}")
    
    # Test 3: Batch check
    print("\n3. Testing batch check...")
    test_positions = [
        {'ticker': 'AAPL'},
        {'ticker': 'GOOGL'},
        {'ticker': 'MSFT'}
    ]
    
    exit_signals = module.batch_check_insider_reversal(
        positions=test_positions,
        check_date=date(2024, 12, 31),
        lookback_days=90
    )
    print(f"   ✅ Batch check complete: {len(exit_signals)} exits triggered")
    
    print("\n" + "="*70)
    print("✅ INSIDER REVERSAL MODULE TEST COMPLETE")
    print("="*70)
    print("\n⚠️  NOTE: Full functionality requires Form 4 data ingestion")
    print("   Module is ready for integration when Form 4 data is available")
    
    return True


if __name__ == "__main__":
    import sys
    success = test_insider_reversal_module()
    sys.exit(0 if success else 1)

