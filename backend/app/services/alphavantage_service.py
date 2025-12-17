"""
AlphaVantage Market Data Service
On-demand OHLCV retrieval with caching (no persistent storage per FR-3.1.B.1)
"""

import httpx
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, date, timedelta
import pandas as pd
from app.core.config import settings


class AlphaVantageService:
    """Service for AlphaVantage market data API"""
    
    BASE_URL = "https://www.alphavantage.co/query"
    
    # Rate limits for free tier
    REQUESTS_PER_MINUTE = 5
    REQUESTS_PER_DAY = 500
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize AlphaVantage service"""
        self.api_key = api_key or settings.ALPHAVANTAGE_API_KEY
        self._request_times: List[datetime] = []
        self._daily_request_count = 0
        self._daily_reset_time = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    async def _rate_limit_check(self):
        """Enforce rate limits for API calls"""
        now = datetime.now()
        
        # Reset daily counter if needed
        if now >= self._daily_reset_time + timedelta(days=1):
            self._daily_request_count = 0
            self._daily_reset_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Check daily limit
        if self._daily_request_count >= self.REQUESTS_PER_DAY:
            raise Exception("AlphaVantage daily API limit reached (500 requests)")
        
        # Remove requests older than 1 minute
        one_minute_ago = now - timedelta(minutes=1)
        self._request_times = [t for t in self._request_times if t > one_minute_ago]
        
        # Check per-minute limit
        if len(self._request_times) >= self.REQUESTS_PER_MINUTE:
            # Wait until we can make another request
            wait_until = self._request_times[0] + timedelta(minutes=1)
            wait_seconds = (wait_until - now).total_seconds()
            if wait_seconds > 0:
                print(f"Rate limit: waiting {wait_seconds:.1f}s before next request")
                await asyncio.sleep(wait_seconds)
        
        # Record this request
        self._request_times.append(now)
        self._daily_request_count += 1
    
    async def _make_request(self, params: Dict[str, str]) -> Dict[str, Any]:
        """Make API request with rate limiting"""
        if not self.api_key:
            raise Exception("AlphaVantage API key not configured")
        
        # Add API key to params
        params["apikey"] = self.api_key
        
        # Enforce rate limits
        await self._rate_limit_check()
        
        # Make request
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(self.BASE_URL, params=params)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                print(f"AlphaVantage HTTP error: {e}")
                raise Exception(f"AlphaVantage API error: {e.response.status_code}")
            except Exception as e:
                print(f"AlphaVantage request error: {e}")
                raise Exception(f"AlphaVantage request failed: {str(e)}")
    
    async def get_daily_adjusted(
        self,
        symbol: str,
        outputsize: str = "full"
    ) -> List[Dict[str, Any]]:
        """
        Get daily adjusted OHLCV data (split and dividend adjusted)
        
        Args:
            symbol: Stock ticker symbol
            outputsize: 'compact' (last 100 days) or 'full' (20+ years)
        
        Returns:
            List of daily bars with adjusted prices
            [{
                'date': '2023-01-15',
                'open': 150.25,
                'high': 152.30,
                'low': 149.80,
                'close': 151.50,
                'adjusted_close': 149.75,
                'volume': 1500000,
                'dividend_amount': 0.0,
                'split_coefficient': 1.0
            }, ...]
        """
        params = {
            "function": "TIME_SERIES_DAILY_ADJUSTED",
            "symbol": symbol,
            "outputsize": outputsize
        }
        
        data = await self._make_request(params)
        
        # Check for errors
        if "Error Message" in data:
            raise Exception(f"AlphaVantage error: {data['Error Message']}")
        
        if "Note" in data:
            raise Exception(f"AlphaVantage rate limit: {data['Note']}")
        
        if "Time Series (Daily)" not in data:
            raise Exception(f"Unexpected response format for {symbol}")
        
        # Parse time series data
        time_series = data["Time Series (Daily)"]
        
        bars = []
        for date_str, bar_data in time_series.items():
            bars.append({
                "date": date_str,
                "open": float(bar_data["1. open"]),
                "high": float(bar_data["2. high"]),
                "low": float(bar_data["3. low"]),
                "close": float(bar_data["4. close"]),
                "adjusted_close": float(bar_data["5. adjusted close"]),
                "volume": int(bar_data["6. volume"]),
                "dividend_amount": float(bar_data["7. dividend amount"]),
                "split_coefficient": float(bar_data["8. split coefficient"])
            })
        
        # Sort by date (oldest first)
        bars.sort(key=lambda x: x["date"])
        
        return bars
    
    async def get_daily_adjusted_range(
        self,
        symbol: str,
        start_date: date,
        end_date: date
    ) -> List[Dict[str, Any]]:
        """
        Get daily adjusted data for a specific date range
        
        Args:
            symbol: Stock ticker
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
        
        Returns:
            List of daily bars filtered to date range
        """
        # Get full data
        all_bars = await self.get_daily_adjusted(symbol, outputsize="full")
        
        # Filter to date range
        start_str = start_date.isoformat()
        end_str = end_date.isoformat()
        
        filtered = [
            bar for bar in all_bars
            if start_str <= bar["date"] <= end_str
        ]
        
        return filtered
    
    async def get_quote(self, symbol: str) -> Dict[str, Any]:
        """
        Get latest quote for a symbol
        
        Returns:
            {
                'symbol': 'AAPL',
                'price': 150.25,
                'change': 2.50,
                'change_percent': '1.69%',
                'volume': 45000000,
                'latest_trading_day': '2023-12-15',
                'open': 148.50,
                'high': 151.00,
                'low': 148.00
            }
        """
        params = {
            "function": "GLOBAL_QUOTE",
            "symbol": symbol
        }
        
        data = await self._make_request(params)
        
        if "Error Message" in data:
            raise Exception(f"AlphaVantage error: {data['Error Message']}")
        
        if "Global Quote" not in data:
            raise Exception(f"Unexpected response format for {symbol}")
        
        quote = data["Global Quote"]
        
        if not quote:
            raise Exception(f"No quote data available for {symbol}")
        
        return {
            "symbol": quote["01. symbol"],
            "price": float(quote["05. price"]),
            "change": float(quote["09. change"]),
            "change_percent": quote["10. change percent"],
            "volume": int(quote["06. volume"]),
            "latest_trading_day": quote["07. latest trading day"],
            "open": float(quote["02. open"]),
            "high": float(quote["03. high"]),
            "low": float(quote["04. low"]),
            "previous_close": float(quote["08. previous close"])
        }
    
    async def get_company_overview(self, symbol: str) -> Dict[str, Any]:
        """
        Get company fundamental data and overview
        
        Returns company information including market cap, PE ratio, sector, etc.
        """
        params = {
            "function": "OVERVIEW",
            "symbol": symbol
        }
        
        data = await self._make_request(params)
        
        if "Error Message" in data:
            raise Exception(f"AlphaVantage error: {data['Error Message']}")
        
        if not data or "Symbol" not in data:
            raise Exception(f"No overview data available for {symbol}")
        
        return {
            "symbol": data.get("Symbol"),
            "name": data.get("Name"),
            "description": data.get("Description"),
            "sector": data.get("Sector"),
            "industry": data.get("Industry"),
            "market_cap": int(data.get("MarketCapitalization", 0)) if data.get("MarketCapitalization") else None,
            "pe_ratio": float(data.get("PERatio", 0)) if data.get("PERatio") and data.get("PERatio") != "None" else None,
            "peg_ratio": float(data.get("PEGRatio", 0)) if data.get("PEGRatio") and data.get("PEGRatio") != "None" else None,
            "book_value": float(data.get("BookValue", 0)) if data.get("BookValue") and data.get("BookValue") != "None" else None,
            "dividend_per_share": float(data.get("DividendPerShare", 0)) if data.get("DividendPerShare") else None,
            "dividend_yield": float(data.get("DividendYield", 0)) if data.get("DividendYield") else None,
            "eps": float(data.get("EPS", 0)) if data.get("EPS") and data.get("EPS") != "None" else None,
            "revenue_per_share_ttm": float(data.get("RevenuePerShareTTM", 0)) if data.get("RevenuePerShareTTM") else None,
            "profit_margin": float(data.get("ProfitMargin", 0)) if data.get("ProfitMargin") else None,
            "52_week_high": float(data.get("52WeekHigh", 0)) if data.get("52WeekHigh") else None,
            "52_week_low": float(data.get("52WeekLow", 0)) if data.get("52WeekLow") else None,
            "50_day_ma": float(data.get("50DayMovingAverage", 0)) if data.get("50DayMovingAverage") else None,
            "200_day_ma": float(data.get("200DayMovingAverage", 0)) if data.get("200DayMovingAverage") else None,
            "shares_outstanding": int(data.get("SharesOutstanding", 0)) if data.get("SharesOutstanding") else None
        }
    
    async def batch_get_quotes(self, symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Get quotes for multiple symbols (with rate limiting)
        
        Args:
            symbols: List of ticker symbols
        
        Returns:
            Dict mapping symbol to quote data
        """
        results = {}
        
        for symbol in symbols:
            try:
                quote = await self.get_quote(symbol)
                results[symbol] = quote
            except Exception as e:
                print(f"Error fetching quote for {symbol}: {e}")
                results[symbol] = {"error": str(e)}
        
        return results
    
    async def calculate_technical_indicators(
        self,
        bars: List[Dict[str, Any]],
        sma_period: int = 50,
        rsi_period: int = 14
    ) -> List[Dict[str, Any]]:
        """
        Calculate technical indicators from OHLCV bars
        
        Args:
            bars: List of OHLCV bars from get_daily_adjusted()
            sma_period: Period for Simple Moving Average
            rsi_period: Period for RSI calculation
        
        Returns:
            Bars enriched with technical indicators
        """
        if not bars or len(bars) < max(sma_period, rsi_period + 1):
            return bars
        
        # Convert to DataFrame for easier calculation
        df = pd.DataFrame(bars)
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')
        
        # Calculate SMA
        df[f'sma_{sma_period}'] = df['adjusted_close'].rolling(window=sma_period).mean()
        
        # Calculate RSI
        delta = df['adjusted_close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=rsi_period).mean()
        rs = gain / loss
        df[f'rsi_{rsi_period}'] = 100 - (100 / (1 + rs))
        
        # Calculate 10-day high (for breakout detection)
        df['high_10d'] = df['high'].rolling(window=10).max()
        
        # Convert back to list of dicts
        df['date'] = df['date'].dt.strftime('%Y-%m-%d')
        return df.to_dict('records')


# Singleton instance
_alphavantage_service = None


def get_alphavantage_service() -> AlphaVantageService:
    """Get or create AlphaVantage service instance"""
    global _alphavantage_service
    if _alphavantage_service is None:
        _alphavantage_service = AlphaVantageService()
    return _alphavantage_service

