"""
Strategy Management API Endpoints
"""

from fastapi import APIRouter, HTTPException
from app.services.strategy_db import get_all_strategies, get_strategy

router = APIRouter()


@router.get("")
async def list_strategies():
    """Get all strategies with their latest backtest (OPTIMIZED with caching)"""
    try:
        strategies = get_all_strategies()
        return {
            "strategies": strategies,
            "count": len(strategies),
            "cached": True  # Indicates institution names are cached
        }
    except Exception as e:
        print(f"❌ Error fetching strategies: {e}")
        return {"strategies": [], "count": 0, "error": str(e)}


@router.get("/{strategy_id}")
async def get_strategy_details(strategy_id: int):
    """Get detailed information about a specific strategy"""
    try:
        strategy = get_strategy(strategy_id)
        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")
        return strategy
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{strategy_id}/config")
async def get_strategy_config(strategy_id: int):
    """Get strategy configuration for reloading"""
    try:
        strategy = get_strategy(strategy_id)
        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")
        return {
            "strategy_id": strategy_id,
            "name": strategy["name"],
            "config": strategy["strategy_config"]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

