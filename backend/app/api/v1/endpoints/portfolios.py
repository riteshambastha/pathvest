"""
Portfolio endpoints
"""

from typing import Annotated, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.auth import get_current_user
from app.db.session import get_db
from app.schemas.portfolio import Portfolio, PortfolioCreate, PortfolioUpdate
from app.schemas.user import User as UserSchema
from app.services.portfolio_service import PortfolioService

router = APIRouter()


@router.get("/", response_model=List[Portfolio])
async def get_portfolios(
    current_user: Annotated[UserSchema, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    """Get all portfolios for current user"""
    portfolios = await PortfolioService.get_all_by_user(
        db,
        user_id=current_user.id,
        skip=skip,
        limit=limit
    )
    return portfolios


@router.post("/", response_model=Portfolio, status_code=status.HTTP_201_CREATED)
async def create_portfolio(
    portfolio_in: PortfolioCreate,
    current_user: Annotated[UserSchema, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db)
):
    """Create new portfolio"""
    portfolio = await PortfolioService.create(
        db,
        portfolio_in=portfolio_in,
        user_id=current_user.id
    )
    return portfolio


@router.get("/{portfolio_id}", response_model=Portfolio)
async def get_portfolio(
    portfolio_id: int,
    current_user: Annotated[UserSchema, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db)
):
    """Get portfolio by ID"""
    portfolio = await PortfolioService.get_by_id(
        db,
        portfolio_id=portfolio_id,
        user_id=current_user.id
    )
    
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found"
        )
    
    return portfolio


@router.put("/{portfolio_id}", response_model=Portfolio)
async def update_portfolio(
    portfolio_id: int,
    portfolio_in: PortfolioUpdate,
    current_user: Annotated[UserSchema, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db)
):
    """Update portfolio"""
    portfolio = await PortfolioService.get_by_id(
        db,
        portfolio_id=portfolio_id,
        user_id=current_user.id
    )
    
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found"
        )
    
    portfolio = await PortfolioService.update(db, portfolio, portfolio_in)
    return portfolio


@router.delete("/{portfolio_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_portfolio(
    portfolio_id: int,
    current_user: Annotated[UserSchema, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db)
):
    """Delete portfolio"""
    portfolio = await PortfolioService.get_by_id(
        db,
        portfolio_id=portfolio_id,
        user_id=current_user.id
    )
    
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found"
        )
    
    await PortfolioService.delete(db, portfolio)
    return None

