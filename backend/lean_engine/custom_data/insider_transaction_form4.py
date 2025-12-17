"""
Custom LEAN Data Class for Form 4 Insider Transactions
Integrates SEC Form 4 data from BigQuery into LEAN backtesting engine
"""

from AlgorithmImports import *
from datetime import datetime
import json
from typing import List, Optional


class InsiderTransactionForm4(PythonData):
    """
    Custom data class for Form 4 insider transactions in LEAN
    
    This class allows LEAN to consume Form 4 insider trading data
    with Point-in-Time accuracy (data available at filing_date)
    """
    
    def __init__(self):
        """Initialize Form 4 transaction data"""
        super().__init__()
        
        # Transaction metadata
        self.ticker = None
        self.filing_date = None
        self.transaction_date = None
        
        # Insider information
        self.reporting_owner_name = None
        self.is_officer = False
        self.officer_title = None
        self.is_director = False
        self.is_ten_percent_owner = False
        
        # Transaction details
        self.transaction_code = None  # P, S, A, etc.
        self.shares = 0
        self.price_per_share = 0
        self.transaction_value = 0
        self.acquired_disposed_code = None  # A or D
        
        # Flags
        self.is_10b51_plan = False
        self.is_c_level = False
    
    def GetSource(self, config: SubscriptionDataConfig, date: datetime, isLiveMode: bool) -> SubscriptionDataSource:
        """
        Return the source URL/location for Form 4 data
        
        Args:
            config: Subscription configuration
            date: Current date in backtest
            isLiveMode: Whether running in live mode
        
        Returns:
            SubscriptionDataSource with file location
        """
        if isLiveMode:
            # In live mode, query BigQuery API
            source = f"https://api.pathvest.com/sec/form4?date={date.strftime('%Y-%m-%d')}"
            return SubscriptionDataSource(source, SubscriptionTransportMedium.Rest)
        else:
            # In backtest mode, use local JSON files
            source = f"../data/sec_form4_transactions/{date.strftime('%Y-%m-%d')}.json"
            return SubscriptionDataSource(source, SubscriptionTransportMedium.LocalFile)
    
    def Reader(
        self,
        config: SubscriptionDataConfig,
        line: str,
        date: datetime,
        isLiveMode: bool
    ) -> 'InsiderTransactionForm4':
        """
        Parse the data line into an InsiderTransactionForm4 object
        
        Args:
            config: Subscription configuration
            line: JSON string with transaction data
            date: Current date in backtest
            isLiveMode: Whether running in live mode
        
        Returns:
            InsiderTransactionForm4 instance or None if parsing fails
        """
        try:
            transaction = InsiderTransactionForm4()
            transaction.Symbol = config.Symbol
            
            # Parse JSON data
            data = json.loads(line)
            
            # Set transaction metadata
            transaction.ticker = data.get('ticker')
            transaction.filing_date = self._parse_date(data.get('filing_date'))
            transaction.transaction_date = self._parse_date(data.get('transaction_date'))
            
            # Set insider information
            transaction.reporting_owner_name = data.get('reporting_owner_name')
            transaction.is_officer = data.get('is_officer', False)
            transaction.officer_title = data.get('officer_title')
            transaction.is_director = data.get('is_director', False)
            transaction.is_ten_percent_owner = data.get('is_ten_percent_owner', False)
            
            # Set transaction details
            transaction.transaction_code = data.get('transaction_code')
            transaction.shares = data.get('shares', 0)
            transaction.price_per_share = data.get('price_per_share', 0)
            transaction.transaction_value = transaction.shares * transaction.price_per_share
            transaction.acquired_disposed_code = data.get('acquired_disposed_code')
            
            # Set flags
            transaction.is_10b51_plan = data.get('is_10b51_plan', False)
            transaction.is_c_level = transaction._check_c_level(transaction.officer_title)
            
            # Set LEAN timestamp to filing_date (PIT accuracy)
            transaction.Time = transaction.filing_date
            
            # Set value (transaction value for sorting)
            transaction.Value = transaction.transaction_value
            
            return transaction
        
        except Exception as e:
            print(f"Error parsing Form 4 transaction: {e}")
            return None
    
    def _parse_date(self, date_str: str) -> datetime:
        """Parse date string to datetime"""
        if isinstance(date_str, datetime):
            return date_str
        
        try:
            return datetime.strptime(date_str, '%Y-%m-%d')
        except:
            return datetime.now()
    
    def _check_c_level(self, title: Optional[str]) -> bool:
        """Check if officer title is C-Level"""
        if not title:
            return False
        
        c_level_keywords = [
            'CEO', 'CFO', 'COO', 'CTO', 'CIO',
            'Chief Executive', 'Chief Financial', 'Chief Operating',
            'Chief Technology', 'Chief Information',
            'President', 'Chairman'
        ]
        
        title_upper = title.upper()
        return any(keyword.upper() in title_upper for keyword in c_level_keywords)
    
    def is_purchase(self) -> bool:
        """Check if this is a purchase transaction"""
        return self.transaction_code in ['P', 'A', 'M'] and self.acquired_disposed_code == 'A'
    
    def is_sale(self) -> bool:
        """Check if this is a sale transaction"""
        return self.transaction_code in ['S', 'D', 'F'] and self.acquired_disposed_code == 'D'
    
    def is_qualified_insider(self) -> bool:
        """Check if insider meets qualification criteria"""
        return (
            self.is_c_level and
            self.is_officer and
            not self.is_10b51_plan
        )


class InsiderActivityTracker:
    """
    Helper class to track insider activity across time
    Used by the strategy to detect clusters and patterns
    """
    
    def __init__(self, window_days: int = 90):
        """
        Initialize insider activity tracker
        
        Args:
            window_days: Number of days to track (default: 90)
        """
        self.window_days = window_days
        self.transactions_by_ticker = {}  # ticker -> List[InsiderTransactionForm4]
    
    def add_transaction(self, transaction: InsiderTransactionForm4):
        """Add a transaction to the tracker"""
        ticker = transaction.ticker
        
        if ticker not in self.transactions_by_ticker:
            self.transactions_by_ticker[ticker] = []
        
        self.transactions_by_ticker[ticker].append(transaction)
        
        # Keep only recent transactions (within window)
        self._cleanup_old_transactions(ticker, transaction.Time)
    
    def _cleanup_old_transactions(self, ticker: str, current_date: datetime):
        """Remove transactions older than window"""
        cutoff_date = current_date - timedelta(days=self.window_days)
        
        self.transactions_by_ticker[ticker] = [
            txn for txn in self.transactions_by_ticker[ticker]
            if txn.Time >= cutoff_date
        ]
    
    def get_recent_purchases(self, ticker: str) -> List[InsiderTransactionForm4]:
        """Get recent purchase transactions for a ticker"""
        transactions = self.transactions_by_ticker.get(ticker, [])
        return [txn for txn in transactions if txn.is_purchase() and txn.is_qualified_insider()]
    
    def get_recent_sales(self, ticker: str) -> List[InsiderTransactionForm4]:
        """Get recent sale transactions for a ticker"""
        transactions = self.transactions_by_ticker.get(ticker, [])
        return [txn for txn in transactions if txn.is_sale()]
    
    def get_purchase_cluster_value(self, ticker: str, days: int = 30) -> float:
        """Get total purchase value within cluster window"""
        purchases = self.get_recent_purchases(ticker)
        
        if not purchases:
            return 0
        
        # Find most recent purchase
        latest_purchase = max(purchases, key=lambda p: p.Time)
        cluster_start = latest_purchase.Time - timedelta(days=days)
        
        # Sum purchases in cluster window
        cluster_value = sum(
            p.transaction_value
            for p in purchases
            if p.Time >= cluster_start
        )
        
        return cluster_value
    
    def get_unique_insiders_count(self, ticker: str, days: int = 30) -> int:
        """Get count of unique insiders buying within window"""
        purchases = self.get_recent_purchases(ticker)
        
        if not purchases:
            return 0
        
        # Find most recent purchase
        latest_purchase = max(purchases, key=lambda p: p.Time)
        cluster_start = latest_purchase.Time - timedelta(days=days)
        
        # Count unique insiders
        unique_insiders = set(
            p.reporting_owner_name
            for p in purchases
            if p.Time >= cluster_start
        )
        
        return len(unique_insiders)
    
    def has_insider_cluster(
        self,
        ticker: str,
        min_insiders: int = 2,
        min_value: float = 200_000,
        window_days: int = 30
    ) -> bool:
        """Check if ticker has an insider buying cluster"""
        unique_count = self.get_unique_insiders_count(ticker, window_days)
        cluster_value = self.get_purchase_cluster_value(ticker, window_days)
        
        return unique_count >= min_insiders and cluster_value >= min_value

