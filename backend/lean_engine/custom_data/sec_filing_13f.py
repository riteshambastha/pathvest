"""
Custom LEAN Data Class for 13F Filings
Integrates SEC 13F data from BigQuery into LEAN backtesting engine
"""

from AlgorithmImports import *
from datetime import datetime, timedelta
import json
from typing import Dict, List, Any, Optional


class SecFiling13F(PythonData):
    """
    Custom data class for 13F filings in LEAN
    
    This class allows LEAN to consume 13F filing data from BigQuery
    with Point-in-Time accuracy (data available at filing_date, not period_end_date)
    """
    
    def __init__(self):
        """Initialize 13F filing data"""
        super().__init__()
        
        # Filing metadata
        self.cik = None
        self.institution_name = None
        self.filing_date = None
        self.period_end_date = None
        self.total_value = 0  # in thousands
        self.holdings_count = 0
        
        # Holdings list (parsed from data)
        self.holdings = []
        
        # Signals attached to this filing
        self.signals = []
    
    def GetSource(self, config: SubscriptionDataConfig, date: datetime, isLiveMode: bool) -> SubscriptionDataSource:
        """
        Return the source URL/location for this data
        
        In production, this would query BigQuery for filings on this date.
        For backtesting, we'll use pre-exported JSON files.
        
        Args:
            config: Subscription configuration
            date: Current date in backtest
            isLiveMode: Whether running in live mode
        
        Returns:
            SubscriptionDataSource with file location
        """
        if isLiveMode:
            # In live mode, query BigQuery API
            source = f"https://api.pathvest.com/sec/13f?date={date.strftime('%Y-%m-%d')}"
            return SubscriptionDataSource(source, SubscriptionTransportMedium.Rest)
        else:
            # In backtest mode, use local JSON files exported from BigQuery
            # Format: YYYY-MM-DD.json
            source = f"../data/sec_filings_13f/{date.strftime('%Y-%m-%d')}.json"
            return SubscriptionDataSource(source, SubscriptionTransportMedium.LocalFile)
    
    def Reader(
        self, 
        config: SubscriptionDataConfig, 
        line: str, 
        date: datetime, 
        isLiveMode: bool
    ) -> 'SecFiling13F':
        """
        Parse the data line into a SecFiling13F object
        
        Args:
            config: Subscription configuration
            line: JSON string with filing data
            date: Current date in backtest
            isLiveMode: Whether running in live mode
        
        Returns:
            SecFiling13F instance or None if parsing fails
        """
        try:
            filing = SecFiling13F()
            filing.Symbol = config.Symbol
            
            # Parse JSON data
            data = json.loads(line)
            
            # Set filing metadata
            filing.cik = data.get('cik')
            filing.institution_name = data.get('institution_name')
            filing.filing_date = self._parse_date(data.get('filing_date'))
            filing.period_end_date = self._parse_date(data.get('period_end_date'))
            filing.total_value = data.get('total_value', 0)
            filing.holdings_count = data.get('holdings_count', 0)
            
            # Parse holdings
            filing.holdings = data.get('holdings', [])
            
            # Parse signals (if attached)
            filing.signals = data.get('signals', [])
            
            # Set LEAN timestamp to filing_date (PIT accuracy)
            filing.Time = filing.filing_date
            
            # Set value (for sorting/filtering in LEAN)
            filing.Value = filing.total_value
            
            return filing
        
        except Exception as e:
            # Log error and return None to skip this data point
            print(f"Error parsing 13F filing: {e}")
            return None
    
    def _parse_date(self, date_str: str) -> datetime:
        """Parse date string to datetime"""
        if isinstance(date_str, datetime):
            return date_str
        
        try:
            return datetime.strptime(date_str, '%Y-%m-%d')
        except:
            return datetime.now()
    
    def get_holding_by_ticker(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Get holding for a specific ticker"""
        for holding in self.holdings:
            if holding.get('ticker') == ticker:
                return holding
        return None
    
    def get_holdings_with_signals(self) -> List[Dict[str, Any]]:
        """Get only holdings that have signals attached"""
        signal_tickers = set(signal.get('ticker') for signal in self.signals)
        return [h for h in self.holdings if h.get('ticker') in signal_tickers]
    
    def has_signal_for_ticker(self, ticker: str) -> bool:
        """Check if this filing has a signal for the given ticker"""
        return any(signal.get('ticker') == ticker for signal in self.signals)
    
    def get_signals_for_ticker(self, ticker: str) -> List[Dict[str, Any]]:
        """Get all signals for a specific ticker"""
        return [s for s in self.signals if s.get('ticker') == ticker]


class SecFilingCollection:
    """
    Helper class to manage collection of 13F filings
    Used by the strategy to track multiple institutions over time
    """
    
    def __init__(self):
        """Initialize filing collection"""
        self.filings_by_date = {}  # date -> List[SecFiling13F]
        self.filings_by_cik = {}   # cik -> List[SecFiling13F]
    
    def add_filing(self, filing: SecFiling13F):
        """Add a filing to the collection"""
        date_key = filing.filing_date.strftime('%Y-%m-%d')
        
        if date_key not in self.filings_by_date:
            self.filings_by_date[date_key] = []
        self.filings_by_date[date_key].append(filing)
        
        if filing.cik not in self.filings_by_cik:
            self.filings_by_cik[filing.cik] = []
        self.filings_by_cik[filing.cik].append(filing)
    
    def get_filings_on_date(self, date: datetime) -> List[SecFiling13F]:
        """Get all filings on a specific date"""
        date_key = date.strftime('%Y-%m-%d')
        return self.filings_by_date.get(date_key, [])
    
    def get_latest_filing_for_institution(self, cik: str) -> Optional[SecFiling13F]:
        """Get most recent filing for an institution"""
        filings = self.filings_by_cik.get(cik, [])
        if filings:
            return sorted(filings, key=lambda f: f.filing_date, reverse=True)[0]
        return None
    
    def get_tickers_with_signals(self, date: datetime) -> List[str]:
        """Get all tickers with signals on a specific date"""
        filings = self.get_filings_on_date(date)
        tickers = set()
        
        for filing in filings:
            for signal in filing.signals:
                tickers.add(signal.get('ticker'))
        
        return list(tickers)

