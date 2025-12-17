"""
SEC-specific schemas for search queries and responses
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class SECSearchQuery(BaseModel):
    """Schema for SEC filing search query"""
    cik: Optional[str] = None
    form_type: str = "13F-HR"
    from_date: Optional[str] = None
    to_date: Optional[str] = None
    size: int = Field(default=10, ge=1, le=100)


class SECSearchResponse(BaseModel):
    """Schema for SEC search results"""
    total: Dict[str, Any]
    filings: List[Dict[str, Any]]
    cached: bool = False  # Indicates if results came from cache


class FilingAnalytics(BaseModel):
    """Schema for filing analytics and metrics"""
    accession_no: str
    company_name: str
    filed_at: datetime
    total_holdings: int
    total_aum: float  # in thousands
    total_aum_usd: float  # in actual dollars
    top_holdings: List[Dict[str, Any]]
    concentration_top_3: float
    concentration_top_10: float
    concentration_top_20: float

