"""
Filing Pydantic schemas
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class FilingBase(BaseModel):
    """Base filing schema"""
    accession_no: str = Field(..., min_length=1, max_length=50)
    form_type: str = Field(..., min_length=1, max_length=20)
    filed_at: datetime
    period_of_report: Optional[str] = None
    link_to_txt: Optional[str] = None
    link_to_html: Optional[str] = None
    link_to_filing_details: Optional[str] = None
    total_holdings: Optional[int] = None
    total_value: Optional[float] = None


class FilingCreate(FilingBase):
    """Schema for creating a new filing"""
    institution_id: int
    raw_response: Optional[str] = None


class FilingUpdate(BaseModel):
    """Schema for updating filing"""
    total_holdings: Optional[int] = None
    total_value: Optional[float] = None


class Filing(FilingBase):
    """Schema for filing response"""
    id: int
    institution_id: int
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


class FilingWithInstitution(Filing):
    """Filing with institution details"""
    institution_name: str
    institution_cik: str
