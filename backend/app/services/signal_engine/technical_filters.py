"""
Technical Confirmation Filters - FR-3.1.C.9.2
Apply technical filters to Primary Candidate List
"""

from typing import List, Dict, Any, Optional
from datetime import date, timedelta
from app.services.alphavantage_service import get_alphavantage_service
from app.services.market_data_cache import get_cache_service


class TechnicalFilters:
    """
    Technical confirmation filters for signal validation
    
    A trade is executed if and only if a candidate meets ALL of these
    technical conditions on the signal date or subsequent days:
    
    1. Price Breakout: Close > 10-day High
    2. Trend Filter: Close > 50-day Simple Moving Average (SMA)
    3. Momentum Filter: Relative Strength Index (RSI 14-period) > 45
    """
    
    DEFAULT_BREAKOUT_DAYS = 10
    DEFAULT_SMA_PERIOD = 50
    DEFAULT_RSI_PERIOD = 14
    DEFAULT_RSI_THRESHOLD = 45
    
    def __init__(self):
        """Initialize technical filters"""
        self.market_data_service = get_alphavantage_service()
        self.cache_service = get_cache_service()
    
    async def get_market_data_for_ticker(
        self,
        ticker: str,
        signal_date: date,
        lookback_days: int = 200  # Need enough for 50-day SMA + buffer
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Get market data for ticker with caching
        
        Args:
            ticker: Stock ticker
            signal_date: Signal date
            lookback_days: Days to look back
        
        Returns:
            List of OHLCV bars with technical indicators
        """
        start_date = signal_date - timedelta(days=lookback_days)
        
        # Try cache first
        cached_bars = await self.cache_service.get_daily_bars(
            symbol=ticker,
            start_date=start_date,
            end_date=signal_date
        )
        
        if cached_bars:
            return cached_bars
        
        # Fetch from API
        try:
            bars = await self.market_data_service.get_daily_adjusted_range(
                symbol=ticker,
                start_date=start_date,
                end_date=signal_date
            )
            
            if not bars:
                return None
            
            # Calculate technical indicators
            bars_with_indicators = await self.market_data_service.calculate_technical_indicators(
                bars=bars,
                sma_period=self.DEFAULT_SMA_PERIOD,
                rsi_period=self.DEFAULT_RSI_PERIOD
            )
            
            # Cache for future use
            await self.cache_service.set_daily_bars(
                symbol=ticker,
                start_date=start_date,
                end_date=signal_date,
                bars=bars_with_indicators
            )
            
            return bars_with_indicators
        
        except Exception as e:
            print(f"Error fetching market data for {ticker}: {e}")
            return None
    
    async def check_price_breakout(
        self,
        bars: List[Dict[str, Any]],
        signal_date: date,
        breakout_days: int = DEFAULT_BREAKOUT_DAYS
    ) -> Dict[str, Any]:
        """
        Check if Close > 10-day High
        
        Args:
            bars: OHLCV bars
            signal_date: Signal date
            breakout_days: Number of days for high calculation
        
        Returns:
            Dict with breakout check result
        """
        if not bars or len(bars) < breakout_days + 1:
            return {
                "passes": False,
                "reason": "Insufficient data for breakout calculation"
            }
        
        # Find bar for signal date
        signal_bar = None
        signal_bar_index = None
        
        for i, bar in enumerate(bars):
            if bar.get("date") == signal_date.isoformat():
                signal_bar = bar
                signal_bar_index = i
                break
        
        if not signal_bar:
            return {
                "passes": False,
                "reason": "No bar found for signal date"
            }
        
        # Get close price on signal date
        close_price = signal_bar.get("close") or signal_bar.get("adjusted_close", 0)
        
        # Calculate 10-day high (excluding signal date itself)
        if signal_bar_index < breakout_days:
            return {
                "passes": False,
                "reason": f"Need at least {breakout_days} days of prior data"
            }
        
        # Look at previous N days
        prior_bars = bars[signal_bar_index - breakout_days:signal_bar_index]
        ten_day_high = max(bar.get("high", 0) for bar in prior_bars)
        
        passes = close_price > ten_day_high
        
        return {
            "passes": passes,
            "close_price": close_price,
            "ten_day_high": ten_day_high,
            "breakout_margin": (close_price - ten_day_high) / ten_day_high if ten_day_high > 0 else 0
        }
    
    async def check_trend_filter(
        self,
        bars: List[Dict[str, Any]],
        signal_date: date,
        sma_period: int = DEFAULT_SMA_PERIOD
    ) -> Dict[str, Any]:
        """
        Check if Close > 50-day SMA
        
        Args:
            bars: OHLCV bars with SMA calculated
            signal_date: Signal date
            sma_period: SMA period
        
        Returns:
            Dict with trend check result
        """
        if not bars:
            return {
                "passes": False,
                "reason": "No market data available"
            }
        
        # Find bar for signal date
        signal_bar = None
        for bar in bars:
            if bar.get("date") == signal_date.isoformat():
                signal_bar = bar
                break
        
        if not signal_bar:
            return {
                "passes": False,
                "reason": "No bar found for signal date"
            }
        
        close_price = signal_bar.get("close") or signal_bar.get("adjusted_close", 0)
        sma = signal_bar.get(f"sma_{sma_period}")
        
        if sma is None or sma == 0:
            return {
                "passes": False,
                "reason": f"SMA_{sma_period} not calculated or insufficient data"
            }
        
        passes = close_price > sma
        
        return {
            "passes": passes,
            "close_price": close_price,
            f"sma_{sma_period}": sma,
            "distance_from_sma_pct": ((close_price - sma) / sma) * 100 if sma > 0 else 0
        }
    
    async def check_momentum_filter(
        self,
        bars: List[Dict[str, Any]],
        signal_date: date,
        rsi_period: int = DEFAULT_RSI_PERIOD,
        rsi_threshold: float = DEFAULT_RSI_THRESHOLD
    ) -> Dict[str, Any]:
        """
        Check if RSI(14) > 45
        
        Args:
            bars: OHLCV bars with RSI calculated
            signal_date: Signal date
            rsi_period: RSI period
            rsi_threshold: RSI threshold
        
        Returns:
            Dict with momentum check result
        """
        if not bars:
            return {
                "passes": False,
                "reason": "No market data available"
            }
        
        # Find bar for signal date
        signal_bar = None
        for bar in bars:
            if bar.get("date") == signal_date.isoformat():
                signal_bar = bar
                break
        
        if not signal_bar:
            return {
                "passes": False,
                "reason": "No bar found for signal date"
            }
        
        rsi = signal_bar.get(f"rsi_{rsi_period}")
        
        if rsi is None:
            return {
                "passes": False,
                "reason": f"RSI_{rsi_period} not calculated or insufficient data"
            }
        
        passes = rsi > rsi_threshold
        
        return {
            "passes": passes,
            f"rsi_{rsi_period}": rsi,
            "rsi_threshold": rsi_threshold,
            "rsi_margin": rsi - rsi_threshold
        }
    
    async def check_technical_confirmation(
        self,
        ticker: str,
        signal_date: date,
        lookback_days: int = 200
    ) -> Dict[str, Any]:
        """
        Check if a candidate passes technical confirmation (alias for apply_all_filters)
        
        Per SRS FR-3.1.C.9.2, a trade is executed if and only if a candidate meets:
        1. Price Breakout: Close > 10-day High
        2. Trend Filter: Close > 50-day SMA
        3. Momentum Filter: RSI(14) > 45
        
        Args:
            ticker: Stock ticker
            signal_date: Signal date (date)
            lookback_days: Days to look back for data (default 200)
        
        Returns:
            Dict with confirmation result and individual filter checks
        """
        return await self.apply_all_filters(ticker, signal_date)
    
    async def apply_all_filters(
        self,
        ticker: str,
        signal_date: date
    ) -> Dict[str, Any]:
        """
        Apply all three technical filters to a candidate
        
        Args:
            ticker: Stock ticker
            signal_date: Signal date
        
        Returns:
            Dict with filter results (ALL must pass)
        """
        # Get market data
        bars = await self.get_market_data_for_ticker(ticker, signal_date)
        
        if not bars:
            return {
                "passes_all": False,
                "reason": "Unable to fetch market data",
                "breakout_check": None,
                "trend_check": None,
                "momentum_check": None
            }
        
        # Apply each filter
        breakout_check = await self.check_price_breakout(bars, signal_date)
        trend_check = await self.check_trend_filter(bars, signal_date)
        momentum_check = await self.check_momentum_filter(bars, signal_date)
        
        # All must pass
        passes_all = all([
            breakout_check.get("passes", False),
            trend_check.get("passes", False),
            momentum_check.get("passes", False)
        ])
        
        return {
            "passes_all": passes_all,
            "breakout_check": breakout_check,
            "trend_check": trend_check,
            "momentum_check": momentum_check
        }
    
    async def filter_candidates(
        self,
        primary_candidate_list: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Filter Primary Candidate List by technical confirmation
        
        Args:
            primary_candidate_list: List of candidates from signal aggregation
        
        Returns:
            List of candidates that pass ALL technical filters
        """
        confirmed_candidates = []
        
        for candidate in primary_candidate_list:
            ticker = candidate.get("ticker")
            signal_date_str = candidate.get("signal_date")
            
            if not ticker or not signal_date_str:
                continue
            
            # Parse signal date
            from datetime import datetime
            signal_date = datetime.fromisoformat(signal_date_str).date()
            
            # Apply technical filters
            technical_check = await self.apply_all_filters(ticker, signal_date)
            
            if technical_check.get("passes_all", False):
                # Add technical check results to candidate
                candidate["technical_confirmation"] = technical_check
                candidate["confirmed"] = True
                confirmed_candidates.append(candidate)
            else:
                # Optionally keep for logging but mark as not confirmed
                candidate["technical_confirmation"] = technical_check
                candidate["confirmed"] = False
        
        return confirmed_candidates


# Singleton instance
_technical_filters = None


def get_technical_filters() -> TechnicalFilters:
    """Get or create technical filters instance"""
    global _technical_filters
    if _technical_filters is None:
        _technical_filters = TechnicalFilters()
    return _technical_filters

