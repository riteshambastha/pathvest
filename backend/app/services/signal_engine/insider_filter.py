"""
Insider Filter - FR-3.1.C.3 (Part 4)
Filters stocks based on Form 4 insider trading activity
"""

from typing import List, Dict, Any, Optional
from datetime import date, timedelta
from app.services.postgres_service import get_postgres_service
from google.cloud import postgres


class InsiderFilter:
    """
    Filter stocks based on insider trading qualification criteria
    
    Insider Qualification (FR-3.1.C.3 Part 4):
    - Roles: CEO, CFO, COO, President, Chairman
    - Exclude: 10b5-1 plans (fixed calendar)
    - Value: ≥ Max($100k or 0.05% Market Cap)
    - Volume: Total Bought/Sold (90d) ≥ 3 transactions
    - Cluster: Unique insiders ≥ 2 & ≥ $200k aggregate within 30 days
    - Timing: Insider buy must fall within Quarter End + 60 days where fund doubled stake
    """
    
    # C-Level titles that qualify
    QUALIFIED_TITLES = [
        'CEO', 'CFO', 'COO', 'CTO', 'CIO',
        'Chief Executive Officer',
        'Chief Financial Officer',
        'Chief Operating Officer',
        'Chief Technology Officer',
        'Chief Information Officer',
        'President',
        'Chairman',
        'Chair'
    ]
    
    DEFAULT_MIN_TRANSACTION_VALUE = 100_000  # $100k
    DEFAULT_MIN_MARKET_CAP_PCT = 0.0005  # 0.05%
    DEFAULT_MIN_TRANSACTION_COUNT_90D = 3
    DEFAULT_MIN_CLUSTER_INSIDERS = 2
    DEFAULT_MIN_CLUSTER_VALUE = 200_000  # $200k
    DEFAULT_CLUSTER_WINDOW_DAYS = 30
    DEFAULT_TIMING_WINDOW_DAYS = 60  # QE + 60 days
    
    def __init__(self):
        """Initialize insider filter"""
        self.postgres_service = get_postgres_service()
    
    def _is_qualified_title(self, title: Optional[str]) -> bool:
        """Check if officer title is C-Level"""
        if not title:
            return False
        
        title_upper = title.upper()
        
        return any(
            qualified.upper() in title_upper
            for qualified in self.QUALIFIED_TITLES
        )
    
    async def get_insider_activity_for_stock(
        self,
        ticker: str,
        as_of_date: date,
        lookback_days: int = 90
    ) -> List[Dict[str, Any]]:
        """
        Get insider trading activity for a stock
        
        Args:
            ticker: Stock ticker
            as_of_date: Point-in-time date
            lookback_days: Days to look back
        
        Returns:
            List of insider transactions
        """
        if not self.postgres_service.is_available():
            return []
        
        start_date = as_of_date - timedelta(days=lookback_days)
        
        # Query Form 4 transactions
        transactions = await self.postgres_service.get_insider_activity_for_stock(
            ticker=ticker,
            start_date=start_date,
            end_date=as_of_date,
            transaction_codes=['P', 'A', 'M']  # Purchase codes only
        )
        
        return transactions
    
    async def filter_qualified_insiders(
        self,
        transactions: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Filter transactions to only qualified C-Level insiders
        
        Args:
            transactions: List of insider transactions
        
        Returns:
            Filtered list of qualified transactions
        """
        qualified = []
        
        for txn in transactions:
            # Must be an officer
            if not txn.get("is_officer", False):
                continue
            
            # Must have qualified C-Level title
            title = txn.get("officer_title", "")
            if not self._is_qualified_title(title):
                continue
            
            # Exclude 10b5-1 plans
            if txn.get("is_10b51_plan", False):
                continue
            
            qualified.append(txn)
        
        return qualified
    
    async def check_value_threshold(
        self,
        transactions: List[Dict[str, Any]],
        market_cap: float,
        min_transaction_value: float = DEFAULT_MIN_TRANSACTION_VALUE,
        min_market_cap_pct: float = DEFAULT_MIN_MARKET_CAP_PCT
    ) -> List[Dict[str, Any]]:
        """
        Filter transactions by value threshold
        
        Value must be ≥ Max($100k, 0.05% of market cap)
        
        Args:
            transactions: List of transactions
            market_cap: Stock market capitalization
            min_transaction_value: Absolute minimum ($100k default)
            min_market_cap_pct: Percentage of market cap (0.05% default)
        
        Returns:
            Transactions meeting value threshold
        """
        # Calculate dynamic threshold
        market_cap_threshold = market_cap * min_market_cap_pct
        threshold = max(min_transaction_value, market_cap_threshold)
        
        qualified = []
        
        for txn in transactions:
            shares = txn.get("shares", 0)
            price = txn.get("price_per_share", 0)
            value = shares * price
            
            if value >= threshold:
                txn["transaction_value"] = value
                qualified.append(txn)
        
        return qualified
    
    async def check_volume_threshold(
        self,
        transactions: List[Dict[str, Any]],
        min_count: int = DEFAULT_MIN_TRANSACTION_COUNT_90D
    ) -> bool:
        """
        Check if total transaction count meets threshold
        
        Args:
            transactions: List of transactions (within 90d window)
            min_count: Minimum number of transactions (default: 3)
        
        Returns:
            True if volume threshold met
        """
        return len(transactions) >= min_count
    
    async def detect_insider_cluster(
        self,
        transactions: List[Dict[str, Any]],
        cluster_window_days: int = DEFAULT_CLUSTER_WINDOW_DAYS,
        min_unique_insiders: int = DEFAULT_MIN_CLUSTER_INSIDERS,
        min_cluster_value: float = DEFAULT_MIN_CLUSTER_VALUE
    ) -> Optional[Dict[str, Any]]:
        """
        Detect if there's a significant cluster of insider buying
        
        Cluster criteria:
        - ≥2 unique insiders
        - ≥$200k aggregate value
        - Within 30-day window
        
        Args:
            transactions: List of insider transactions
            cluster_window_days: Window for cluster detection
            min_unique_insiders: Minimum unique insiders
            min_cluster_value: Minimum aggregate value
        
        Returns:
            Cluster info dict if found, None otherwise
        """
        if len(transactions) < min_unique_insiders:
            return None
        
        # Sort by transaction date
        sorted_txns = sorted(transactions, key=lambda x: x.get("transaction_date", ""))
        
        # Sliding window to find clusters
        for i in range(len(sorted_txns)):
            window_start_date = sorted_txns[i].get("transaction_date")
            if not window_start_date:
                continue
            
            # Convert string to date if needed
            if isinstance(window_start_date, str):
                from datetime import datetime
                window_start_date = datetime.fromisoformat(window_start_date).date()
            
            window_end_date = window_start_date + timedelta(days=cluster_window_days)
            
            # Find all transactions in this window
            window_txns = [
                txn for txn in sorted_txns
                if window_start_date <= self._parse_date(txn.get("transaction_date")) <= window_end_date
            ]
            
            # Count unique insiders
            unique_insiders = set(txn.get("reporting_owner_cik") for txn in window_txns)
            
            # Calculate aggregate value
            aggregate_value = sum(
                txn.get("shares", 0) * txn.get("price_per_share", 0)
                for txn in window_txns
            )
            
            # Check if cluster criteria met
            if len(unique_insiders) >= min_unique_insiders and aggregate_value >= min_cluster_value:
                return {
                    "cluster_start_date": window_start_date.isoformat(),
                    "cluster_end_date": window_end_date.isoformat(),
                    "unique_insiders": len(unique_insiders),
                    "aggregate_value": aggregate_value,
                    "transaction_count": len(window_txns),
                    "transactions": window_txns
                }
        
        return None
    
    def _parse_date(self, date_val: Any) -> date:
        """Parse date from string or date object"""
        if isinstance(date_val, date):
            return date_val
        elif isinstance(date_val, str):
            from datetime import datetime
            return datetime.fromisoformat(date_val).date()
        else:
            return date.today()
    
    async def check_timing_alignment(
        self,
        insider_cluster_date: date,
        institutional_quarter_end: date,
        timing_window_days: int = DEFAULT_TIMING_WINDOW_DAYS
    ) -> bool:
        """
        Check if insider buying timing aligns with institutional buying
        
        Insider buy must fall within Quarter End + 60 days where fund doubled stake
        
        Args:
            insider_cluster_date: Date of insider cluster
            institutional_quarter_end: Quarter end date of institutional buying
            timing_window_days: Window after QE (default: 60 days)
        
        Returns:
            True if timing aligns
        """
        window_end = institutional_quarter_end + timedelta(days=timing_window_days)
        
        return institutional_quarter_end <= insider_cluster_date <= window_end
    
    async def get_stocks_with_qualified_insider_activity(
        self,
        stocks: List[Dict[str, Any]],
        as_of_date: date,
        quarter_end_date: Optional[date] = None
    ) -> List[Dict[str, Any]]:
        """
        Filter stocks to those with qualified insider activity
        
        Args:
            stocks: List of stocks to check
            as_of_date: Point-in-time date
            quarter_end_date: Quarter end for timing alignment (if applicable)
        
        Returns:
            Stocks with qualified insider activity
        """
        qualified_stocks = []
        
        for stock in stocks:
            ticker = stock.get("ticker")
            market_cap = stock.get("estimated_market_cap", 0)
            
            if not ticker or not market_cap:
                continue
            
            # Get insider transactions (90 days)
            transactions = await self.get_insider_activity_for_stock(
                ticker=ticker,
                as_of_date=as_of_date,
                lookback_days=90
            )
            
            if not transactions:
                continue
            
            # Filter to qualified C-Level insiders
            qualified_txns = await self.filter_qualified_insiders(transactions)
            
            if not qualified_txns:
                continue
            
            # Check value threshold
            value_qualified = await self.check_value_threshold(
                qualified_txns,
                market_cap=market_cap
            )
            
            if not value_qualified:
                continue
            
            # Check volume threshold (≥3 transactions in 90d)
            volume_check = await self.check_volume_threshold(value_qualified)
            
            if not volume_check:
                continue
            
            # Detect insider cluster
            cluster = await self.detect_insider_cluster(value_qualified)
            
            if not cluster:
                continue
            
            # Check timing alignment if quarter end provided
            timing_aligned = True
            if quarter_end_date:
                cluster_date = self._parse_date(cluster["cluster_start_date"])
                timing_aligned = await self.check_timing_alignment(
                    insider_cluster_date=cluster_date,
                    institutional_quarter_end=quarter_end_date
                )
            
            if not timing_aligned:
                continue
            
            # Stock qualifies!
            qualified_stocks.append({
                **stock,
                "insider_activity": {
                    "total_transactions": len(transactions),
                    "qualified_transactions": len(value_qualified),
                    "cluster": cluster,
                    "timing_aligned": timing_aligned
                }
            })
        
        return qualified_stocks


# Singleton instance
_insider_filter = None


def get_insider_filter() -> InsiderFilter:
    """Get or create insider filter instance"""
    global _insider_filter
    if _insider_filter is None:
        _insider_filter = InsiderFilter()
    return _insider_filter

