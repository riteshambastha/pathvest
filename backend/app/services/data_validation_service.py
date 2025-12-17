"""
Data Validation Service for SEC Filings Data
Implements FR-3.1.B.4 validation checks
"""

from typing import Dict, List, Any, Optional
from datetime import date, datetime
from enum import Enum


class ValidationLevel(str, Enum):
    """Validation severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ValidationResult:
    """Result of a validation check"""
    
    def __init__(
        self,
        field: str,
        level: ValidationLevel,
        message: str,
        value: Any = None,
        expected: Any = None
    ):
        self.field = field
        self.level = level
        self.message = message
        self.value = value
        self.expected = expected
        self.timestamp = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "field": self.field,
            "level": self.level.value,
            "message": self.message,
            "value": self.value,
            "expected": self.expected,
            "timestamp": self.timestamp.isoformat()
        }


class DataValidationService:
    """Service for validating SEC filings data"""
    
    # Valid SEC Form 4 transaction codes
    VALID_TRANSACTION_CODES = {
        'P': 'Open Market Purchase',
        'S': 'Open Market Sale',
        'A': 'Award (Grant, etc.)',
        'D': 'Sale to issuer',
        'F': 'Payment of exercise price or tax',
        'G': 'Gift',
        'M': 'Exercise of options',
        'C': 'Conversion',
        'J': 'Other acquisition/disposition',
        'W': 'Acquisition/disposition by will or inheritance',
        'X': 'Exercise of out-of-the-money options',
        'I': 'Discretionary transaction',
        'L': 'Small acquisition',
        'U': 'Disposition pursuant to tender offer',
        'Z': 'Deposit into/withdrawal from plan'
    }
    
    # Valid C-Level titles for insider filter
    VALID_C_LEVEL_TITLES = [
        'CEO', 'CFO', 'COO', 'President', 'Chairman',
        'Chief Executive Officer', 'Chief Financial Officer',
        'Chief Operating Officer', 'Chief Technology Officer', 'CTO',
        'Chief Information Officer', 'CIO'
    ]
    
    @staticmethod
    def validate_cusip(cusip: str) -> List[ValidationResult]:
        """
        Validate CUSIP format
        
        Returns list of validation issues (empty if valid)
        """
        results = []
        
        if not cusip:
            results.append(ValidationResult(
                field="cusip",
                level=ValidationLevel.ERROR,
                message="CUSIP is required",
                value=cusip
            ))
            return results
        
        # Check length
        if len(cusip) != 9:
            results.append(ValidationResult(
                field="cusip",
                level=ValidationLevel.ERROR,
                message=f"CUSIP must be 9 characters, got {len(cusip)}",
                value=cusip,
                expected="9 characters"
            ))
        
        # Check alphanumeric
        if not cusip[:8].isalnum():
            results.append(ValidationResult(
                field="cusip",
                level=ValidationLevel.ERROR,
                message="CUSIP must be alphanumeric",
                value=cusip
            ))
        
        return results
    
    @staticmethod
    def validate_ticker(ticker: Optional[str], cusip: str) -> List[ValidationResult]:
        """
        Validate ticker mapping
        
        Args:
            ticker: Ticker symbol (can be None)
            cusip: Associated CUSIP
        
        Returns list of validation issues
        """
        results = []
        
        if not ticker:
            results.append(ValidationResult(
                field="ticker",
                level=ValidationLevel.WARNING,
                message=f"CUSIP {cusip} has no ticker mapping",
                value=None
            ))
        elif len(ticker) > 10:
            results.append(ValidationResult(
                field="ticker",
                level=ValidationLevel.WARNING,
                message=f"Ticker unusually long: {ticker}",
                value=ticker
            ))
        
        return results
    
    @staticmethod
    def validate_institutional_investor(
        cik: str,
        name: Optional[str]
    ) -> List[ValidationResult]:
        """
        Validate institutional investor data
        
        Args:
            cik: CIK identifier
            name: Institution name
        
        Returns list of validation issues
        """
        results = []
        
        # Validate CIK
        if not cik:
            results.append(ValidationResult(
                field="cik",
                level=ValidationLevel.CRITICAL,
                message="CIK is required",
                value=cik
            ))
        elif not cik.isdigit():
            results.append(ValidationResult(
                field="cik",
                level=ValidationLevel.ERROR,
                message="CIK must be numeric",
                value=cik
            ))
        
        # Validate name
        if not name or not name.strip():
            results.append(ValidationResult(
                field="name",
                level=ValidationLevel.ERROR,
                message="Institution name is required",
                value=name
            ))
        
        return results
    
    @staticmethod
    def validate_holding_transaction(
        shares: Optional[int],
        value: Optional[float],
        market_price: Optional[float] = None
    ) -> List[ValidationResult]:
        """
        Validate 13F holding transaction data
        
        Args:
            shares: Share count
            value: Position value in thousands
            market_price: Market close price on report date (for validation)
        
        Returns list of validation issues
        """
        results = []
        
        # Validate non-negative shares
        if shares is not None and shares < 0:
            results.append(ValidationResult(
                field="shares",
                level=ValidationLevel.ERROR,
                message="Shares cannot be negative",
                value=shares,
                expected=">= 0"
            ))
        
        # Validate non-negative value
        if value is not None and value < 0:
            results.append(ValidationResult(
                field="value",
                level=ValidationLevel.ERROR,
                message="Position value cannot be negative",
                value=value,
                expected=">= 0"
            ))
        
        # Validate implied price vs market price (50% deviation check)
        if all([shares, value, market_price]) and shares > 0:
            implied_price = (value * 1000) / shares  # value is in thousands
            
            if market_price > 0:
                deviation = abs(implied_price - market_price) / market_price
                
                if deviation > 0.50:  # 50% deviation threshold
                    results.append(ValidationResult(
                        field="value",
                        level=ValidationLevel.WARNING,
                        message=f"Implied price (${implied_price:.2f}) deviates {deviation*100:.1f}% from market price (${market_price:.2f})",
                        value=implied_price,
                        expected=market_price
                    ))
        
        return results
    
    @staticmethod
    def validate_insider_transaction(
        transaction_code: str,
        transaction_date: date,
        filing_date: date,
        shares: float,
        relationship: Dict[str, bool],
        officer_title: Optional[str] = None
    ) -> List[ValidationResult]:
        """
        Validate Form 4 insider transaction data
        
        Args:
            transaction_code: SEC transaction code
            transaction_date: Date of transaction
            filing_date: Date Form 4 was filed
            shares: Number of shares
            relationship: Dict with is_director, is_officer, is_ten_percent_owner flags
            officer_title: Officer title if applicable
        
        Returns list of validation issues
        """
        results = []
        
        # Validate transaction code
        if transaction_code not in DataValidationService.VALID_TRANSACTION_CODES:
            results.append(ValidationResult(
                field="transaction_code",
                level=ValidationLevel.ERROR,
                message=f"Invalid transaction code: {transaction_code}",
                value=transaction_code,
                expected=f"One of: {', '.join(DataValidationService.VALID_TRANSACTION_CODES.keys())}"
            ))
        
        # Validate transaction date is not in the future relative to filing date
        if transaction_date > filing_date:
            results.append(ValidationResult(
                field="transaction_date",
                level=ValidationLevel.ERROR,
                message=f"Transaction date ({transaction_date}) cannot be after filing date ({filing_date})",
                value=transaction_date,
                expected=f"<= {filing_date}"
            ))
        
        # Validate transaction date is not too far in the future (absolute)
        if transaction_date > date.today():
            results.append(ValidationResult(
                field="transaction_date",
                level=ValidationLevel.CRITICAL,
                message=f"Transaction date ({transaction_date}) is in the future",
                value=transaction_date,
                expected=f"<= {date.today()}"
            ))
        
        # Validate shares
        if shares <= 0:
            results.append(ValidationResult(
                field="shares",
                level=ValidationLevel.ERROR,
                message="Shares must be positive",
                value=shares,
                expected="> 0"
            ))
        
        # Validate relationship
        has_relationship = any([
            relationship.get('is_director', False),
            relationship.get('is_officer', False),
            relationship.get('is_ten_percent_owner', False)
        ])
        
        if not has_relationship:
            results.append(ValidationResult(
                field="relationship",
                level=ValidationLevel.WARNING,
                message="No relationship defined (director, officer, or 10% owner)",
                value=relationship
            ))
        
        # Validate officer title if is_officer is True
        if relationship.get('is_officer', False):
            if not officer_title:
                results.append(ValidationResult(
                    field="officer_title",
                    level=ValidationLevel.WARNING,
                    message="Officer relationship but no title specified",
                    value=None
                ))
            elif officer_title:
                # Check if C-Level for sub-universe filter
                is_c_level = any(
                    title.lower() in officer_title.lower()
                    for title in DataValidationService.VALID_C_LEVEL_TITLES
                )
                
                if not is_c_level:
                    results.append(ValidationResult(
                        field="officer_title",
                        level=ValidationLevel.INFO,
                        message=f"Officer title '{officer_title}' is not C-Level (may be filtered out)",
                        value=officer_title
                    ))
        
        return results
    
    @staticmethod
    def validate_filing_completeness(filing_data: Dict[str, Any]) -> List[ValidationResult]:
        """
        Validate that a filing has all required fields
        
        Args:
            filing_data: Dict containing filing information
        
        Returns list of validation issues
        """
        results = []
        
        required_fields = {
            'filing_id': 'Filing ID',
            'cik': 'CIK',
            'filing_date': 'Filing Date',
            'period_end_date': 'Period End Date',
            'accession_number': 'Accession Number'
        }
        
        for field, field_name in required_fields.items():
            if field not in filing_data or filing_data[field] is None:
                results.append(ValidationResult(
                    field=field,
                    level=ValidationLevel.CRITICAL,
                    message=f"{field_name} is required but missing",
                    value=None
                ))
        
        return results
    
    @staticmethod
    def generate_validation_report(
        results: List[ValidationResult]
    ) -> Dict[str, Any]:
        """
        Generate validation report summary
        
        Args:
            results: List of validation results
        
        Returns:
            Summary dict with counts by level and details
        """
        summary = {
            "total_issues": len(results),
            "by_level": {
                ValidationLevel.INFO.value: 0,
                ValidationLevel.WARNING.value: 0,
                ValidationLevel.ERROR.value: 0,
                ValidationLevel.CRITICAL.value: 0
            },
            "is_valid": True,
            "issues": [r.to_dict() for r in results]
        }
        
        for result in results:
            summary["by_level"][result.level.value] += 1
            
            # Mark as invalid if there are errors or critical issues
            if result.level in [ValidationLevel.ERROR, ValidationLevel.CRITICAL]:
                summary["is_valid"] = False
        
        return summary


# Singleton instance
_validation_service = None


def get_validation_service() -> DataValidationService:
    """Get or create validation service instance"""
    global _validation_service
    if _validation_service is None:
        _validation_service = DataValidationService()
    return _validation_service

