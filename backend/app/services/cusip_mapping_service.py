"""
CUSIP to Ticker Mapping Service
Handles CUSIP to ticker conversions with PIT (Point-in-Time) accuracy
"""

import httpx
import asyncio
from typing import Optional, Dict, List, Any
from datetime import date, datetime
from app.core.config import settings
from app.services.postgres_service import get_postgres_service


class CUSIPMappingService:
    """Service for CUSIP to ticker mapping with PIT accuracy"""
    
    OPENFIGI_URL = "https://api.openfigi.com/v3/mapping"
    
    def __init__(self):
        """Initialize CUSIP mapping service"""
        self.openfigi_api_key = settings.OPENFIGI_API_KEY
        self.postgres_service = get_postgres_service()
        self._cache: Dict[str, Dict[str, str]] = {}
    
    async def get_ticker_for_cusip(
        self,
        cusip: str,
        as_of_date: Optional[date] = None
    ) -> Optional[str]:
        """
        Get ticker for a CUSIP as of a specific date
        
        Args:
            cusip: 9-character CUSIP
            as_of_date: Date for PIT accuracy (defaults to today)
        
        Returns:
            Ticker symbol or None if not found
        """
        if not cusip or len(cusip) != 9:
            return None
        
        as_of_date = as_of_date or date.today()
        
        # Try PostgreSQL cache first
        ticker = await self.postgres_service.get_ticker_for_cusip(cusip, as_of_date)
        if ticker:
            return ticker
        
        # Try OpenFIGI API
        ticker = await self._fetch_from_openfigi(cusip)
        if ticker:
            # Cache the mapping in PostgreSQL
            await self.postgres_service.insert_cusip_ticker_mapping(
                cusip=cusip,
                ticker=ticker,
                effective_date=as_of_date
            )
            return ticker
        
        return None
    
    async def _fetch_from_openfigi(self, cusip: str) -> Optional[str]:
        """Fetch ticker from OpenFIGI API"""
        if not self.openfigi_api_key:
            print("OpenFIGI API key not configured")
            return None
        
        headers = {
            "Content-Type": "application/json"
        }
        
        if self.openfigi_api_key:
            headers["X-OPENFIGI-APIKEY"] = self.openfigi_api_key
        
        payload = [
            {
                "idType": "ID_CUSIP",
                "idValue": cusip,
                "exchCode": "US"
            }
        ]
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    self.OPENFIGI_URL,
                    json=payload,
                    headers=headers
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if data and len(data) > 0 and "data" in data[0]:
                        results = data[0]["data"]
                        
                        # Find the best match (prefer US common stock)
                        for result in results:
                            if result.get("marketSector") == "Equity" and result.get("ticker"):
                                return result["ticker"]
                        
                        # If no equity found, return first ticker
                        if results and results[0].get("ticker"):
                            return results[0]["ticker"]
                
                elif response.status_code == 429:
                    print("OpenFIGI rate limit reached")
                    # Wait and retry once
                    await asyncio.sleep(1)
                    return await self._fetch_from_openfigi(cusip)
        
        except Exception as e:
            print(f"Error fetching from OpenFIGI for CUSIP {cusip}: {e}")
        
        return None
    
    async def bulk_map_cusips(
        self,
        cusips: List[str],
        as_of_date: Optional[date] = None
    ) -> Dict[str, Optional[str]]:
        """
        Map multiple CUSIPs to tickers
        
        Args:
            cusips: List of 9-character CUSIPs
            as_of_date: Date for PIT accuracy
        
        Returns:
            Dict mapping CUSIP to ticker
        """
        results = {}
        
        # Process in batches to respect rate limits
        batch_size = 10
        
        for i in range(0, len(cusips), batch_size):
            batch = cusips[i:i + batch_size]
            
            # Process batch
            tasks = [
                self.get_ticker_for_cusip(cusip, as_of_date)
                for cusip in batch
            ]
            
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for cusip, ticker in zip(batch, batch_results):
                if isinstance(ticker, Exception):
                    print(f"Error mapping CUSIP {cusip}: {ticker}")
                    results[cusip] = None
                else:
                    results[cusip] = ticker
            
            # Rate limiting pause
            if i + batch_size < len(cusips):
                await asyncio.sleep(0.5)
        
        return results
    
    async def get_cusip_for_ticker(
        self,
        ticker: str,
        as_of_date: Optional[date] = None
    ) -> Optional[str]:
        """
        Reverse lookup: Get CUSIP for a ticker
        
        Args:
            ticker: Stock ticker symbol
            as_of_date: Date for PIT accuracy
        
        Returns:
            CUSIP or None if not found
        """
        as_of_date = as_of_date or date.today()
        
        # Query PostgreSQL
        if self.postgres_service.is_available():
            query = """
                SELECT cusip
                FROM sec_cusip_ticker_mapping
                WHERE ticker = :ticker
                    AND effective_date <= :as_of_date
                    AND (end_date IS NULL OR end_date > :as_of_date)
                ORDER BY effective_date DESC
                LIMIT 1
            """
            
            params = {
                "ticker": ticker,
                "as_of_date": as_of_date
            }
            
            results = await self.postgres_service.execute_query(query, params)
            
            if results:
                return results[0].get("cusip")
        
        # Try OpenFIGI reverse lookup
        return await self._fetch_cusip_from_openfigi(ticker)
    
    async def _fetch_cusip_from_openfigi(self, ticker: str) -> Optional[str]:
        """Fetch CUSIP from OpenFIGI using ticker"""
        if not self.openfigi_api_key:
            return None
        
        headers = {
            "Content-Type": "application/json",
            "X-OPENFIGI-APIKEY": self.openfigi_api_key
        }
        
        payload = [
            {
                "idType": "TICKER",
                "idValue": ticker,
                "exchCode": "US"
            }
        ]
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    self.OPENFIGI_URL,
                    json=payload,
                    headers=headers
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if data and len(data) > 0 and "data" in data[0]:
                        results = data[0]["data"]
                        
                        # Find the best match
                        for result in results:
                            if result.get("marketSector") == "Equity" and result.get("cusip"):
                                return result["cusip"]
        
        except Exception as e:
            print(f"Error fetching CUSIP from OpenFIGI for ticker {ticker}: {e}")
        
        return None
    
    async def validate_cusip(self, cusip: str) -> bool:
        """
        Validate CUSIP format and check digit
        
        Args:
            cusip: 9-character CUSIP
        
        Returns:
            True if valid, False otherwise
        """
        if not cusip or len(cusip) != 9:
            return False
        
        # Check if alphanumeric
        if not cusip[:8].isalnum():
            return False
        
        # Validate check digit (Luhn algorithm variant)
        try:
            total = 0
            for i, char in enumerate(cusip[:8]):
                if char.isdigit():
                    value = int(char)
                else:
                    # A=10, B=11, ..., Z=35
                    value = ord(char.upper()) - ord('A') + 10
                
                if i % 2 == 1:
                    value *= 2
                
                total += (value // 10) + (value % 10)
            
            check_digit = (10 - (total % 10)) % 10
            return str(check_digit) == cusip[8]
        
        except Exception:
            return False


# Singleton instance
_cusip_mapping_service = None


def get_cusip_mapping_service() -> CUSIPMappingService:
    """Get or create CUSIP mapping service instance"""
    global _cusip_mapping_service
    if _cusip_mapping_service is None:
        _cusip_mapping_service = CUSIPMappingService()
    return _cusip_mapping_service

