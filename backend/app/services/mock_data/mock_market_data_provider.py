"""
Mock Market Data Provider for Development/Testing
Generates synthetic OHLCV data with realistic noise
"""

import random
import math
from typing import List, Dict, Any, Optional
from datetime import date, datetime, timedelta
import numpy as np


class MockMarketDataProvider:
    """Mock provider for market data (OHLCV)"""
    
    # Sample stocks with base parameters
    MOCK_STOCKS = {
        "MOCK": {"name": "Mock Corp", "base_price": 150.0, "volatility": 0.02, "trend": 0.0003},
        "TEST": {"name": "Test Inc", "base_price": 85.50, "volatility": 0.025, "trend": 0.0002},
        "DEMO": {"name": "Demo Technologies", "base_price": 220.75, "volatility": 0.03, "trend": 0.0005},
        "SMPL": {"name": "Sample Industries", "base_price": 42.30, "volatility": 0.018, "trend": 0.0001},
        "PLCH": {"name": "Placeholder Systems", "base_price": 178.25, "volatility": 0.022, "trend": 0.0004},
        "AAPL": {"name": "Mock Apple", "base_price": 175.0, "volatility": 0.02, "trend": 0.0004},
        "MSFT": {"name": "Mock Microsoft", "base_price": 380.0, "volatility": 0.018, "trend": 0.0003},
        "GOOGL": {"name": "Mock Google", "base_price": 140.0, "volatility": 0.025, "trend": 0.0003},
        "AMZN": {"name": "Mock Amazon", "base_price": 150.0, "volatility": 0.028, "trend": 0.0004},
        "META": {"name": "Mock Meta", "base_price": 350.0, "volatility": 0.03, "trend": 0.0002},
    }
    
    def __init__(self, seed: int = 42):
        """Initialize mock provider with seed for reproducibility"""
        random.seed(seed)
        np.random.seed(seed)
    
    def generate_daily_bars(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
        start_price: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate synthetic daily OHLCV bars using geometric Brownian motion
        
        Args:
            symbol: Stock ticker
            start_date: Start date
            end_date: End date
            start_price: Starting price (uses base price if None)
        
        Returns:
            List of daily bars with OHLCV data
        """
        if symbol not in self.MOCK_STOCKS:
            # Use generic parameters for unknown symbols
            stock_params = {
                "name": f"Mock {symbol}",
                "base_price": 100.0,
                "volatility": 0.02,
                "trend": 0.0002
            }
        else:
            stock_params = self.MOCK_STOCKS[symbol]
        
        # Calculate number of trading days (approximately 252 per year)
        num_days = (end_date - start_date).days
        trading_days = int(num_days * (252 / 365))
        
        if trading_days <= 0:
            return []
        
        # Initialize price
        price = start_price or stock_params["base_price"]
        volatility = stock_params["volatility"]
        trend = stock_params["trend"]
        
        bars = []
        current_date = start_date
        
        for i in range(trading_days):
            # Skip weekends (simplified)
            while current_date.weekday() >= 5:  # Saturday=5, Sunday=6
                current_date += timedelta(days=1)
            
            if current_date > end_date:
                break
            
            # Generate daily return using geometric Brownian motion
            # dS = S * (μ*dt + σ*dW)
            dt = 1  # 1 day
            random_shock = np.random.normal(0, 1)
            daily_return = trend * dt + volatility * random_shock * math.sqrt(dt)
            
            # Calculate new price
            new_price = price * (1 + daily_return)
            
            # Generate OHLC with intraday volatility
            intraday_vol = volatility * 0.5
            open_price = price * (1 + np.random.normal(0, intraday_vol * 0.3))
            close_price = new_price
            
            # High and low with realistic constraints
            high_price = max(open_price, close_price) * (1 + abs(np.random.normal(0, intraday_vol)))
            low_price = min(open_price, close_price) * (1 - abs(np.random.normal(0, intraday_vol)))
            
            # Generate volume (random walk around 1M shares)
            base_volume = 1_000_000
            volume = int(base_volume * (1 + np.random.normal(0, 0.5)))
            volume = max(100_000, volume)  # Minimum volume
            
            # Dividend (occasional, quarterly-ish)
            dividend = 0.0
            if i % 63 == 0 and random.random() > 0.7:  # ~quarterly, 30% chance
                dividend = round(new_price * 0.005, 2)  # 0.5% dividend
            
            # Split (rare)
            split_coefficient = 1.0
            if i % 500 == 0 and random.random() > 0.95:  # Very rare
                split_coefficient = 2.0
                new_price /= 2.0
                open_price /= 2.0
                close_price /= 2.0
                high_price /= 2.0
                low_price /= 2.0
            
            bar = {
                "date": current_date.isoformat(),
                "open": round(open_price, 2),
                "high": round(high_price, 2),
                "low": round(low_price, 2),
                "close": round(close_price, 2),
                "adjusted_close": round(close_price, 2),  # Would adjust for splits/dividends
                "volume": volume,
                "dividend_amount": dividend,
                "split_coefficient": split_coefficient
            }
            
            bars.append(bar)
            
            # Update price for next day
            price = new_price
            
            # Move to next trading day
            current_date += timedelta(days=1)
        
        return bars
    
    def generate_quote(self, symbol: str) -> Dict[str, Any]:
        """
        Generate a mock real-time quote
        
        Args:
            symbol: Stock ticker
        
        Returns:
            Quote data
        """
        if symbol not in self.MOCK_STOCKS:
            stock_params = {
                "name": f"Mock {symbol}",
                "base_price": 100.0,
                "volatility": 0.02
            }
        else:
            stock_params = self.MOCK_STOCKS[symbol]
        
        # Today's price with some noise
        price = stock_params["base_price"] * (1 + np.random.normal(0, stock_params["volatility"]))
        previous_close = stock_params["base_price"]
        
        change = price - previous_close
        change_percent = (change / previous_close) * 100
        
        # Generate OHLC for today
        open_price = previous_close * (1 + np.random.normal(0, stock_params["volatility"] * 0.5))
        high_price = max(open_price, price) * (1 + abs(np.random.normal(0, stock_params["volatility"] * 0.3)))
        low_price = min(open_price, price) * (1 - abs(np.random.normal(0, stock_params["volatility"] * 0.3)))
        
        volume = int(1_000_000 * (1 + np.random.normal(0, 0.5)))
        
        return {
            "symbol": symbol,
            "price": round(price, 2),
            "change": round(change, 2),
            "change_percent": f"{change_percent:.2f}%",
            "volume": max(100_000, volume),
            "latest_trading_day": date.today().isoformat(),
            "open": round(open_price, 2),
            "high": round(high_price, 2),
            "low": round(low_price, 2),
            "previous_close": round(previous_close, 2)
        }
    
    def generate_company_overview(self, symbol: str) -> Dict[str, Any]:
        """
        Generate mock company fundamental data
        
        Args:
            symbol: Stock ticker
        
        Returns:
            Company overview data
        """
        if symbol not in self.MOCK_STOCKS:
            stock_params = {
                "name": f"Mock {symbol}",
                "base_price": 100.0
            }
        else:
            stock_params = self.MOCK_STOCKS[symbol]
        
        price = stock_params["base_price"]
        
        # Generate realistic fundamental ratios
        shares_outstanding = random.randint(100_000_000, 5_000_000_000)
        market_cap = int(price * shares_outstanding)
        
        eps = price * random.uniform(0.03, 0.08)  # P/E of 12-33
        pe_ratio = price / eps if eps > 0 else None
        
        book_value = price * random.uniform(0.4, 0.8)
        
        return {
            "symbol": symbol,
            "name": stock_params["name"],
            "description": f"Mock company {stock_params['name']} for testing purposes.",
            "sector": random.choice(["Technology", "Healthcare", "Financial", "Consumer", "Industrial"]),
            "industry": random.choice(["Software", "Biotechnology", "Banking", "Retail", "Manufacturing"]),
            "market_cap": market_cap,
            "pe_ratio": round(pe_ratio, 2) if pe_ratio else None,
            "peg_ratio": round(random.uniform(0.8, 2.5), 2),
            "book_value": round(book_value, 2),
            "dividend_per_share": round(price * random.uniform(0.01, 0.03), 2),
            "dividend_yield": round(random.uniform(0.01, 0.04), 4),
            "eps": round(eps, 2),
            "revenue_per_share_ttm": round(price * random.uniform(0.3, 0.6), 2),
            "profit_margin": round(random.uniform(0.05, 0.25), 4),
            "52_week_high": round(price * random.uniform(1.05, 1.25), 2),
            "52_week_low": round(price * random.uniform(0.75, 0.95), 2),
            "50_day_ma": round(price * random.uniform(0.95, 1.05), 2),
            "200_day_ma": round(price * random.uniform(0.90, 1.10), 2),
            "shares_outstanding": shares_outstanding
        }
    
    def add_crash_period(
        self,
        bars: List[Dict[str, Any]],
        crash_start_index: int,
        crash_duration: int = 20,
        max_drawdown: float = 0.30
    ) -> List[Dict[str, Any]]:
        """
        Add a simulated market crash to existing bars
        
        Args:
            bars: List of existing bars
            crash_start_index: Index where crash begins
            crash_duration: Number of days for crash
            max_drawdown: Maximum drawdown (e.g., 0.30 for -30%)
        
        Returns:
            Modified bars with crash
        """
        if crash_start_index >= len(bars):
            return bars
        
        crash_end_index = min(crash_start_index + crash_duration, len(bars))
        
        start_price = bars[crash_start_index]["close"]
        low_price = start_price * (1 - max_drawdown)
        
        # Apply exponential decline during crash
        for i in range(crash_start_index, crash_end_index):
            progress = (i - crash_start_index) / crash_duration
            
            # Exponential decay with some noise
            decline_factor = 1 - (max_drawdown * (1 - math.exp(-3 * progress)))
            noise = np.random.normal(0, 0.01)
            
            adjustment_factor = decline_factor + noise
            
            bars[i]["open"] *= adjustment_factor
            bars[i]["high"] *= adjustment_factor
            bars[i]["low"] *= adjustment_factor
            bars[i]["close"] *= adjustment_factor
            bars[i]["adjusted_close"] *= adjustment_factor
            
            # Increase volume during crash
            bars[i]["volume"] = int(bars[i]["volume"] * random.uniform(1.5, 3.0))
        
        return bars


# Singleton instance
_mock_market_data_provider = None


def get_mock_market_data_provider() -> MockMarketDataProvider:
    """Get or create mock market data provider instance"""
    global _mock_market_data_provider
    if _mock_market_data_provider is None:
        _mock_market_data_provider = MockMarketDataProvider()
    return _mock_market_data_provider

