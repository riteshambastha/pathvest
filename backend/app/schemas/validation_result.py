"""
Validation Result Schemas
"""

from typing import Any, Optional, List, Dict
from pydantic import BaseModel
from datetime import datetime
from enum import Enum


class ValidationLevel(str, Enum):
    """Validation severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ValidationIssue(BaseModel):
    """Single validation issue"""
    field: str
    level: ValidationLevel
    message: str
    value: Optional[Any] = None
    expected: Optional[Any] = None
    timestamp: datetime
    
    class Config:
        json_schema_extra = {
            "example": {
                "field": "cusip",
                "level": "error",
                "message": "CUSIP must be 9 characters",
                "value": "12345",
                "expected": "9 characters",
                "timestamp": "2023-12-15T10:30:00Z"
            }
        }


class ValidationReport(BaseModel):
    """Validation report summary"""
    total_issues: int
    by_level: Dict[str, int]
    is_valid: bool
    issues: List[ValidationIssue]
    
    class Config:
        json_schema_extra = {
            "example": {
                "total_issues": 2,
                "by_level": {
                    "info": 0,
                    "warning": 1,
                    "error": 1,
                    "critical": 0
                },
                "is_valid": False,
                "issues": [
                    {
                        "field": "cusip",
                        "level": "error",
                        "message": "CUSIP must be 9 characters",
                        "value": "12345",
                        "expected": "9 characters",
                        "timestamp": "2023-12-15T10:30:00Z"
                    },
                    {
                        "field": "ticker",
                        "level": "warning",
                        "message": "No ticker mapping found",
                        "value": None,
                        "expected": None,
                        "timestamp": "2023-12-15T10:30:00Z"
                    }
                ]
            }
        }


class FilingValidationRequest(BaseModel):
    """Request to validate a filing"""
    filing_id: str
    cik: str
    filing_date: str
    period_end_date: str
    accession_number: str
    total_value: Optional[float] = None
    holdings_count: Optional[int] = None


class HoldingValidationRequest(BaseModel):
    """Request to validate a holding"""
    cusip: str
    ticker: Optional[str] = None
    shares: Optional[int] = None
    value: Optional[float] = None
    market_price: Optional[float] = None


class InsiderTransactionValidationRequest(BaseModel):
    """Request to validate an insider transaction"""
    transaction_code: str
    transaction_date: str
    filing_date: str
    shares: float
    is_director: bool = False
    is_officer: bool = False
    is_ten_percent_owner: bool = False
    officer_title: Optional[str] = None

