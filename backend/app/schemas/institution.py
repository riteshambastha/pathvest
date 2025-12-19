"""
Institution Pydantic schemas
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class InstitutionBase(BaseModel):
    """Base institution schema"""
    cik: str = Field(..., min_length=1, max_length=20)
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    is_popular: bool = False
    aum: Optional[int] = Field(None, description="Assets Under Management in USD")


class InstitutionCreate(InstitutionBase):
    """Schema for creating a new institution"""
    pass


class InstitutionUpdate(BaseModel):
    """Schema for updating institution"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    is_popular: Optional[bool] = None
    aum: Optional[int] = Field(None, description="Assets Under Management in USD")


class Institution(InstitutionBase):
    """Schema for institution response"""
    id: int
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}
