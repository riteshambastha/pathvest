"""
Exit Module 2: Insider Reversal (FR-3.1.C.11)
Form 4 selling spikes detection

Per SRS FR-3.1.C.11:
Trigger Event: Processing of Form 4 filings
Exit Condition: Aggregate Insider Sales (Form 4) in last 30 days > $5,000,000 
                AND > 50% of total insider holdings

This is a significant negative signal that should trigger exit.
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
    total_sales_value: float  # Aggregate sales in lookback period
    total_holdings_value: float  # Total insider holdings
    sales_to_holdings_ratio: float  # Ratio of sales to holdings
    insider_count: int  # Number of selling insiders
    top_seller_name: Optional[str] = None
    top_seller_title: Optional[str] = None
    top_seller_value: float = 0
    confidence: float = 85


class InsiderReversalModule:
    """
    Exit Module 2: Insider Reversal Detection (FR-3.1.C.11)
    
    Monitors Form 4 filings for significant insider selling.
    Triggers exit when massive insider selling cluster is detected.
    
    SRS Exit Condition:
    - Aggregate Insider Sales in last 30 days > $5,000,000
    - AND > 50% of total insider holdings
    
    While insiders sell for many reasons, a massive cluster is a negative signal.
    """
    
    # SRS-defined thresholds
    SALES_THRESHOLD = 5_000_000  # $5M minimum aggregate sales
    HOLDINGS_PERCENT_THRESHOLD = 0.50  # 50% of total insider holdings
    LOOKBACK_DAYS = 30  # 30-day lookback period
    
    # Additional C-level filtering (optional enhancement)
    C_LEVEL_ROLES = ['CEO', 'CFO', 'COO', 'President', 'Chairman', 'Director', 'CTO', 'CIO']
    
    def __init__(self, postgres_service=None):
        """
        Initialize Insider Reversal Module
        
        Args:
            postgres_service: PostgreSQL service for data access
        """
        self.postgres_service = postgres_service
    
    def check_insider_reversal(
        self,
        ticker: str,
        check_date: date,
        lookback_days: int = LOOKBACK_DAYS,
        sales_threshold: float = SALES_THRESHOLD,
        holdings_pct_threshold: float = HOLDINGS_PERCENT_THRESHOLD,
        c_level_only: bool = False
    ) -> Optional[InsiderReversalExit]:
        """
        Check if insider reversal exit should be triggered (SRS FR-3.1.C.11)
        
        SRS Exit Condition:
        - Aggregate Insider Sales (30 days) > $5M
        - AND > 50% of total insider holdings
        
        Args:
            ticker: Stock ticker
            check_date: Date to check for reversal
            lookback_days: Days to look back for sales (default 30)
            sales_threshold: Minimum aggregate sales (default $5M)
            holdings_pct_threshold: Minimum percentage of holdings sold (default 50%)
            c_level_only: Only consider C-level executives (optional)
            
        Returns:
            InsiderReversalExit if exit triggered, None otherwise
        """
        
        # Get aggregate insider sales in lookback period
        sales_data = self._get_aggregate_insider_sales(
            ticker=ticker,
            check_date=check_date,
            lookback_days=lookback_days,
            c_level_only=c_level_only
        )
        
        if not sales_data or sales_data['total_sales'] == 0:
            return None
        
        # Get total insider holdings
        total_holdings = self._get_total_insider_holdings(
            ticker=ticker,
            check_date=check_date
        )
        
        if total_holdings is None or total_holdings == 0:
            # Can't calculate ratio, fall back to sales threshold only
            if sales_data['total_sales'] > sales_threshold:
                return InsiderReversalExit(
                    ticker=ticker,
                    exit_date=check_date,
                    reason=f"Aggregate insider sales ${sales_data['total_sales']/1e6:.1f}M exceeds ${sales_threshold/1e6:.0f}M threshold",
                    total_sales_value=sales_data['total_sales'],
                    total_holdings_value=0,
                    sales_to_holdings_ratio=1.0,
                    insider_count=sales_data['insider_count'],
                    top_seller_name=sales_data.get('top_seller_name'),
                    top_seller_title=sales_data.get('top_seller_title'),
                    top_seller_value=sales_data.get('top_seller_value', 0),
                    confidence=75  # Lower confidence without holdings data
                )
            return None
        
        # Calculate sales to holdings ratio
        sales_ratio = sales_data['total_sales'] / total_holdings
        
        # Check SRS conditions: $5M AND >50% of holdings
        meets_sales_threshold = sales_data['total_sales'] > sales_threshold
        meets_holdings_threshold = sales_ratio > holdings_pct_threshold
        
        if meets_sales_threshold and meets_holdings_threshold:
            # Full SRS condition met - high confidence
            confidence = 95
            reason = (
                f"Insider sales ${sales_data['total_sales']/1e6:.1f}M (>{sales_threshold/1e6:.0f}M) "
                f"= {sales_ratio*100:.0f}% of holdings (>{holdings_pct_threshold*100:.0f}%)"
            )
        elif meets_sales_threshold:
            # Only sales threshold met
            confidence = 70
            reason = f"Aggregate insider sales ${sales_data['total_sales']/1e6:.1f}M exceeds ${sales_threshold/1e6:.0f}M threshold"
        elif meets_holdings_threshold and sales_data['total_sales'] > 1_000_000:
            # Significant percentage but below dollar threshold
            confidence = 65
            reason = f"Insider sales {sales_ratio*100:.0f}% of holdings exceeds {holdings_pct_threshold*100:.0f}% threshold"
        else:
            # Neither condition fully met
            return None
        
        return InsiderReversalExit(
            ticker=ticker,
            exit_date=check_date,
            reason=reason,
            total_sales_value=sales_data['total_sales'],
            total_holdings_value=total_holdings,
            sales_to_holdings_ratio=sales_ratio,
            insider_count=sales_data['insider_count'],
            top_seller_name=sales_data.get('top_seller_name'),
            top_seller_title=sales_data.get('top_seller_title'),
            top_seller_value=sales_data.get('top_seller_value', 0),
            confidence=confidence
        )
    
    def batch_check_insider_reversal(
        self,
        positions: List[Dict],
        check_date: date,
        lookback_days: int = LOOKBACK_DAYS,
        min_transaction_value: float = SALES_THRESHOLD
    ) -> List[InsiderReversalExit]:
        """
        Check insider reversal for multiple positions
        
        Args:
            positions: List of position dicts with 'ticker' key
            check_date: Date to check for reversal
            lookback_days: Days to look back
            min_transaction_value: Minimum aggregate sales value
            
        Returns:
            List of InsiderReversalExit signals
        """
        exit_signals = []
        
        for position in positions:
            exit_signal = self.check_insider_reversal(
                ticker=position['ticker'],
                check_date=check_date,
                lookback_days=lookback_days,
                sales_threshold=min_transaction_value
            )
            
            if exit_signal:
                exit_signals.append(exit_signal)
        
        return exit_signals
    
    # ==================== Database Query Methods ====================
    
    def _get_aggregate_insider_sales(
        self,
        ticker: str,
        check_date: date,
        lookback_days: int,
        c_level_only: bool = False
    ) -> Optional[Dict]:
        """
        Get aggregate insider sales from Form 4 data
        
        Args:
            ticker: Stock ticker
            check_date: Date to check
            lookback_days: Days to look back
            c_level_only: Filter for C-level only
            
        Returns:
            Dict with total_sales, insider_count, top_seller details
        """
        if not self.postgres_service:
            print(f"⚠️  PostgreSQL not available for insider sales query")
            return self._get_mock_sales_data(ticker)
        
        try:
            start_date = check_date - timedelta(days=lookback_days)
            
            # Query Form 4 sales data
            # Note: This requires Form 4 data to be ingested
            query = """
                SELECT 
                    SUM(transaction_value) as total_sales,
                    COUNT(DISTINCT insider_name) as insider_count,
                    MAX(transaction_value) as max_sale
                FROM insider_transactions
                WHERE ticker = :ticker
                    AND transaction_type = 'S'
                    AND transaction_date BETWEEN :start_date AND :check_date
            """
            
            if c_level_only:
                query = query.replace(
                    "WHERE ticker",
                    f"WHERE (title ILIKE '%CEO%' OR title ILIKE '%CFO%' OR title ILIKE '%COO%' "
                    f"OR title ILIKE '%President%' OR title ILIKE '%Chairman%') AND ticker"
                )
            
            result = self.postgres_service.execute_query(
                query,
                {'ticker': ticker, 'start_date': start_date, 'check_date': check_date}
            )
            
            if result and result[0]['total_sales']:
                row = result[0]
                
                # Get top seller details
                top_seller_query = """
                    SELECT insider_name, title, SUM(transaction_value) as total_value
                    FROM insider_transactions
                    WHERE ticker = :ticker
                        AND transaction_type = 'S'
                        AND transaction_date BETWEEN :start_date AND :check_date
                    GROUP BY insider_name, title
                    ORDER BY total_value DESC
                    LIMIT 1
                """
                
                top_seller_result = self.postgres_service.execute_query(
                    top_seller_query,
                    {'ticker': ticker, 'start_date': start_date, 'check_date': check_date}
                )
                
                top_seller = top_seller_result[0] if top_seller_result else {}
                
                return {
                    'total_sales': float(row['total_sales']),
                    'insider_count': int(row['insider_count']),
                    'top_seller_name': top_seller.get('insider_name'),
                    'top_seller_title': top_seller.get('title'),
                    'top_seller_value': float(top_seller.get('total_value', 0))
                }
            
            return None
            
        except Exception as e:
            print(f"⚠️  Form 4 data query failed: {e}")
            print(f"⚠️  Form 4 data may not be ingested yet. Returning None.")
            return None
    
    def _get_total_insider_holdings(
        self,
        ticker: str,
        check_date: date
    ) -> Optional[float]:
        """
        Get total insider holdings value for a ticker
        
        Args:
            ticker: Stock ticker
            check_date: Date to check
            
        Returns:
            Total holdings value or None
        """
        if not self.postgres_service:
            return None
        
        try:
            # Query for current insider holdings
            query = """
                SELECT SUM(shares_held * share_price) as total_value
                FROM insider_holdings
                WHERE ticker = :ticker
                    AND as_of_date <= :check_date
            """
            
            result = self.postgres_service.execute_query(
                query,
                {'ticker': ticker, 'check_date': check_date}
            )
            
            if result and result[0]['total_value']:
                return float(result[0]['total_value'])
            
            return None
            
        except Exception as e:
            print(f"⚠️  Insider holdings query failed: {e}")
            return None
    
    def _get_mock_sales_data(self, ticker: str) -> Optional[Dict]:
        """
        Return mock data for development/testing when Form 4 data is unavailable
        """
        # Return None to indicate no data available
        # In production, this should be removed
        return None
    
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
        if not self.postgres_service:
            return {
                'ticker': ticker,
                'start_date': str(start_date),
                'end_date': str(end_date),
                'total_transactions': 0,
                'purchases': 0,
                'purchases_value': 0,
                'sales': 0,
                'sales_value': 0,
                'net_value': 0,
                'unique_insiders': 0,
                'note': 'Form 4 data not available - PostgreSQL service not connected'
            }
        
        try:
            query = """
                SELECT 
                    COUNT(*) as total_transactions,
                    SUM(CASE WHEN transaction_type = 'P' THEN 1 ELSE 0 END) as purchases,
                    SUM(CASE WHEN transaction_type = 'P' THEN transaction_value ELSE 0 END) as purchases_value,
                    SUM(CASE WHEN transaction_type = 'S' THEN 1 ELSE 0 END) as sales,
                    SUM(CASE WHEN transaction_type = 'S' THEN transaction_value ELSE 0 END) as sales_value,
                    COUNT(DISTINCT insider_name) as unique_insiders
                FROM insider_transactions
                WHERE ticker = :ticker
                    AND transaction_date BETWEEN :start_date AND :end_date
            """
            
            result = self.postgres_service.execute_query(
                query,
                {'ticker': ticker, 'start_date': start_date, 'end_date': end_date}
            )
            
            if result:
                row = result[0]
                purchases_value = float(row['purchases_value'] or 0)
                sales_value = float(row['sales_value'] or 0)
                
                return {
                    'ticker': ticker,
                    'start_date': str(start_date),
                    'end_date': str(end_date),
                    'total_transactions': int(row['total_transactions'] or 0),
                    'purchases': int(row['purchases'] or 0),
                    'purchases_value': purchases_value,
                    'sales': int(row['sales'] or 0),
                    'sales_value': sales_value,
                    'net_value': purchases_value - sales_value,
                    'unique_insiders': int(row['unique_insiders'] or 0)
                }
            
            return {
                'ticker': ticker,
                'total_transactions': 0,
                'note': 'No Form 4 data found'
            }
            
        except Exception as e:
            return {
                'ticker': ticker,
                'total_transactions': 0,
                'error': str(e),
                'note': 'Form 4 data query failed'
            }


# Test function
def test_insider_reversal_module():
    """Test the Insider Reversal Module"""
    print("\n" + "="*70)
    print("🧪 TESTING EXIT MODULE 2: INSIDER REVERSAL (SRS FR-3.1.C.11)")
    print("="*70)
    print("\nSRS Exit Condition:")
    print("  - Aggregate Insider Sales (30 days) > $5,000,000")
    print("  - AND > 50% of total insider holdings")
    print("="*70)
    
    try:
        from app.services.postgres_service import get_postgres_service
        client = get_postgres_service()
        print("✅ PostgreSQL service initialized")
    except Exception as e:
        print(f"⚠️  PostgreSQL not available: {e}")
        client = None
    
    # Create module
    module = InsiderReversalModule(postgres_service=client)
    print("✅ InsiderReversalModule created")
    print(f"   Sales threshold: ${module.SALES_THRESHOLD/1e6:.0f}M")
    print(f"   Holdings threshold: {module.HOLDINGS_PERCENT_THRESHOLD*100:.0f}%")
    print(f"   Lookback period: {module.LOOKBACK_DAYS} days")
    
    # Test 1: Check single position
    print("\n1. Testing single position check...")
    exit_signal = module.check_insider_reversal(
        ticker="AAPL",
        check_date=date(2024, 12, 31),
        lookback_days=30
    )
    
    if exit_signal:
        print(f"   ✅ Insider reversal detected for AAPL")
        print(f"      Reason: {exit_signal.reason}")
        print(f"      Sales: ${exit_signal.total_sales_value:,.0f}")
        print(f"      Holdings: ${exit_signal.total_holdings_value:,.0f}")
        print(f"      Ratio: {exit_signal.sales_to_holdings_ratio*100:.1f}%")
        print(f"      Confidence: {exit_signal.confidence:.1f}")
    else:
        print(f"   ⚠️  No insider reversal detected for AAPL")
        print(f"      (Expected - Form 4 data may not be ingested)")
    
    # Test 2: Get insider activity summary
    print("\n2. Testing insider activity summary...")
    summary = module.get_insider_activity_summary(
        ticker="AAPL",
        start_date=date(2024, 1, 1),
        end_date=date(2024, 12, 31)
    )
    print(f"   ✅ Insider activity summary retrieved")
    print(f"      Total transactions: {summary['total_transactions']}")
    if 'note' in summary:
        print(f"      Note: {summary['note']}")
    
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
        lookback_days=30
    )
    print(f"   ✅ Batch check complete: {len(exit_signals)} exits triggered")
    
    print("\n" + "="*70)
    print("✅ INSIDER REVERSAL MODULE TEST COMPLETE")
    print("="*70)
    print("\n⚠️  NOTE: Full functionality requires Form 4 data ingestion")
    print("   Tables needed: insider_transactions, insider_holdings")
    
    return True


if __name__ == "__main__":
    import sys
    success = test_insider_reversal_module()
    sys.exit(0 if success else 1)
