"""
Institution database model
"""

from datetime import datetime
from sqlalchemy import String, Integer, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List
from app.db.base import Base


class Institution(Base):
    """Institution model for tracking companies/hedge funds"""
    
    __tablename__ = "institutions"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    cik: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    is_popular: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )
    
    # Relationships
    filings: Mapped[List["Filing"]] = relationship(back_populates="institution", cascade="all, delete-orphan")
