"""
Filing database model
"""

from datetime import datetime, date
from sqlalchemy import String, Integer, DateTime, Date, Text, ForeignKey, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List
from app.db.base import Base


class Filing(Base):
    """Filing model for storing SEC 13F-HR filings"""
    
    __tablename__ = "filings"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    institution_id: Mapped[int] = mapped_column(ForeignKey("institutions.id"), nullable=False, index=True)
    accession_no: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    form_type: Mapped[str] = mapped_column(String(20), nullable=False)
    filed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    filing_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)  # Date-only version for queries
    period_of_report: Mapped[str] = mapped_column(String(20), nullable=True)
    
    # Filing URLs
    link_to_txt: Mapped[str] = mapped_column(Text, nullable=True)
    link_to_html: Mapped[str] = mapped_column(Text, nullable=True)
    link_to_filing_details: Mapped[str] = mapped_column(Text, nullable=True)
    
    # Summary data
    total_holdings: Mapped[int] = mapped_column(Integer, nullable=True)
    total_value: Mapped[float] = mapped_column(Float, nullable=True)  # in thousands
    
    # Metadata
    raw_response: Mapped[str] = mapped_column(Text, nullable=True)  # Store original API response
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )
    
    # Relationships
    institution: Mapped["Institution"] = relationship(back_populates="filings")
    holdings: Mapped[List["Holding"]] = relationship(back_populates="filing", cascade="all, delete-orphan")
