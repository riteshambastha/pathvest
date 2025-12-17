"""
Holding Pydantic schemas
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class HoldingBase(BaseModel):
    """Base holding schema"""
    name_of_issuer: str = Field(..., min_length=1, max_length=255)
    cusip: str = Field(..., min_length=1, max_length=20)
    ticker: Optional[str] = Field(None, max_length=20)
    value: float = Field(..., gt=0)  # in thousands
    shares_or_prn_amt: Optional[int] = None
    shares_or_prn_amt_type: Optional[str] = Field(None, max_length=10)
    investment_discretion: Optional[str] = Field(None, max_length=20)
    voting_authority_sole: Optional[int] = None
    voting_authority_shared: Optional[int] = None
    voting_authority_none: Optional[int] = None


class HoldingCreate(HoldingBase):
    """Schema for creating a new holding"""
    filing_id: int


class Holding(HoldingBase):
    """Schema for holding response"""
    id: int
    filing_id: int
    created_at: datetime
    
    model_config = {"from_attributes": True}


class HoldingWithPercentage(Holding):
    """Holding with calculated percentage of portfolio"""
    percentage: float
    value_usd: float  # actual dollar value
