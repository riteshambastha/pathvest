"""
Insider Transaction database model (Form 4 data)
"""

from datetime import datetime, date
from sqlalchemy import String, Integer, DateTime, Float, Boolean, Date, BigInteger
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class InsiderTransaction(Base):
    """Insider Transaction model for storing Form 4 data"""
    
    __tablename__ = "insider_transactions"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    
    # Filing metadata
    accession_number: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    filing_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    
    # Issuer (company) information
    issuer_cik: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    issuer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    ticker: Mapped[str] = mapped_column(String(20), nullable=True, index=True)
    
    # Reporting owner (insider) information
    reporting_owner_name: Mapped[str] = mapped_column(String(255), nullable=False)
    reporting_owner_cik: Mapped[str] = mapped_column(String(20), nullable=True)
    
    # Relationship flags
    is_director: Mapped[bool] = mapped_column(Boolean, default=False)
    is_officer: Mapped[bool] = mapped_column(Boolean, default=False)
    officer_title: Mapped[str] = mapped_column(String(255), nullable=True, index=True)
    is_ten_percent_owner: Mapped[bool] = mapped_column(Boolean, default=False)
    is_other: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Transaction details
    transaction_code: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    transaction_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    deemed_execution_date: Mapped[date] = mapped_column(Date, nullable=True)
    
    shares: Mapped[float] = mapped_column(Float, nullable=False)
    price_per_share: Mapped[float] = mapped_column(Float, nullable=True)
    acquired_disposed_code: Mapped[str] = mapped_column(String(1), nullable=True)  # 'A' or 'D'
    
    # Ownership information
    ownership_nature: Mapped[str] = mapped_column(String(20), default="direct")  # 'direct' or 'indirect'
    
    # 10b5-1 plan flag
    is_10b51_plan: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    source_url: Mapped[str] = mapped_column(String(500), nullable=True)
    
    # Calculated fields
    transaction_value: Mapped[float] = mapped_column(Float, nullable=True)  # shares * price_per_share
    
    def __repr__(self):
        return f"<InsiderTransaction {self.ticker} {self.reporting_owner_name} {self.transaction_code} {self.transaction_date}>"

