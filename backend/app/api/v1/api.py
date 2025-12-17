"""
API v1 router
"""

from fastapi import APIRouter
from app.api.v1.endpoints import auth, portfolios, health, sec, backtest, validation, analytics

api_router = APIRouter()

api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(portfolios.router, prefix="/portfolios", tags=["portfolios"])
api_router.include_router(sec.router, prefix="/sec", tags=["sec-data"])
api_router.include_router(backtest.router, prefix="/backtest", tags=["backtest"])
api_router.include_router(validation.router, prefix="/validation", tags=["validation"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])

