"""
Portfolio service for business logic
"""

from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.portfolio import Portfolio
from app.schemas.portfolio import PortfolioCreate, PortfolioUpdate


class PortfolioService:
    """Service class for portfolio operations"""
    
    @staticmethod
    async def get_by_id(
        db: AsyncSession,
        portfolio_id: int,
        user_id: int
    ) -> Optional[Portfolio]:
        """Get portfolio by ID for a specific user"""
        result = await db.execute(
            select(Portfolio).where(
                Portfolio.id == portfolio_id,
                Portfolio.user_id == user_id
            )
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_all_by_user(
        db: AsyncSession,
        user_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[Portfolio]:
        """Get all portfolios for a user"""
        result = await db.execute(
            select(Portfolio)
            .where(Portfolio.user_id == user_id)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())
    
    @staticmethod
    async def create(
        db: AsyncSession,
        portfolio_in: PortfolioCreate,
        user_id: int
    ) -> Portfolio:
        """Create new portfolio"""
        db_portfolio = Portfolio(
            **portfolio_in.model_dump(),
            user_id=user_id
        )
        db.add(db_portfolio)
        await db.commit()
        await db.refresh(db_portfolio)
        return db_portfolio
    
    @staticmethod
    async def update(
        db: AsyncSession,
        portfolio: Portfolio,
        portfolio_in: PortfolioUpdate
    ) -> Portfolio:
        """Update portfolio"""
        update_data = portfolio_in.model_dump(exclude_unset=True)
        
        for field, value in update_data.items():
            setattr(portfolio, field, value)
        
        db.add(portfolio)
        await db.commit()
        await db.refresh(portfolio)
        return portfolio
    
    @staticmethod
    async def delete(db: AsyncSession, portfolio: Portfolio) -> None:
        """Delete portfolio"""
        await db.delete(portfolio)
        await db.commit()

