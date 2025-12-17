"""
Portfolio Pydantic schemas
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class PortfolioBase(BaseModel):
    """Base portfolio schema"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    strategy_type: str = Field(..., min_length=1, max_length=100)
    initial_capital: float = Field(..., gt=0)


class PortfolioCreate(PortfolioBase):
    """Schema for creating a new portfolio"""
    pass


class PortfolioUpdate(BaseModel):
    """Schema for updating portfolio information"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    strategy_type: Optional[str] = Field(None, min_length=1, max_length=100)
    initial_capital: Optional[float] = Field(None, gt=0)
    current_value: Optional[float] = None
    total_return: Optional[float] = None


class Portfolio(PortfolioBase):
    """Schema for portfolio response"""
    id: int
    user_id: int
    current_value: Optional[float] = None
    total_return: Optional[float] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}

