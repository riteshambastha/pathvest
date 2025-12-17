"""
Holding database model
"""

from datetime import datetime
from sqlalchemy import String, Integer, DateTime, ForeignKey, Float, BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class Holding(Base):
    """Holding model for storing individual stock holdings from 13F-HR filings"""
    
    __tablename__ = "holdings"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    filing_id: Mapped[int] = mapped_column(ForeignKey("filings.id"), nullable=False, index=True)
    
    # Issuer information
    name_of_issuer: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    cusip: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    ticker: Mapped[str] = mapped_column(String(20), nullable=True, index=True)
    
    # Position details
    value: Mapped[float] = mapped_column(Float, nullable=False)  # in thousands
    shares_or_prn_amt: Mapped[int] = mapped_column(BigInteger, nullable=True)
    shares_or_prn_amt_type: Mapped[str] = mapped_column(String(10), nullable=True)  # SH or PRN
    
    # Investment details
    investment_discretion: Mapped[str] = mapped_column(String(20), nullable=True)  # SOLE, SHARED, etc.
    voting_authority_sole: Mapped[int] = mapped_column(BigInteger, nullable=True)
    voting_authority_shared: Mapped[int] = mapped_column(BigInteger, nullable=True)
    voting_authority_none: Mapped[int] = mapped_column(BigInteger, nullable=True)
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    filing: Mapped["Filing"] = relationship(back_populates="holdings")
