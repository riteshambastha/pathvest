"""
Backtest API Endpoints by Ritesh Ambastha
RESTful API for submitting and retrieving backtests
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from fastapi.responses import JSONResponse
from typing import List, Optional
import uuid
from datetime import datetime, date
import asyncio
import json

from app.schemas.backtest_request import BacktestRequest
from app.schemas.backtest_response import BacktestResponse, BacktestStatus
from app.db.session import get_db
from sqlalchemy.orm import Session
from app.services.strategy_db import save_strategy, save_backtest, update_backtest_results

# Import worker (to be created)
# from lean_engine.worker.backtest_worker import BacktestWorker

router = APIRouter(tags=["Backtest"])


# In-memory storage for development (would use Redis/DB in production)
backtest_jobs = {}


def serialize_dates(obj):
    """Recursively convert date/datetime objects to strings in a dict"""
    if isinstance(obj, dict):
        return {k: serialize_dates(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [serialize_dates(item) for item in obj]
    elif isinstance(obj, (date, datetime)):
        return obj.isoformat()
    return obj


@router.post("/run", response_model=BacktestStatus, status_code=202)
async def run_backtest(
    request: BacktestRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Submit a backtest for execution
    
    This endpoint validates the request and queues the backtest for async processing.
    Returns immediately with a backtest_id that can be used to poll for status/results.
    
    Args:
        request: BacktestRequest with complete strategy configuration
        background_tasks: FastAPI background tasks
        db: Database session
    
    Returns:
        BacktestStatus with backtest_id and initial status
    """
    try:
        # Generate unique backtest ID
        backtest_id = f"bt_{uuid.uuid4().hex[:12]}"
        
        # Validate date range
        start_date = request.strategy_config.backtest_period.start_date
        end_date = request.strategy_config.backtest_period.end_date
        
        if end_date <= start_date:
            raise HTTPException(
                status_code=400,
                detail="end_date must be after start_date"
            )
        
        # Validate initial capital
        if request.strategy_config.initial_capital <= 0:
            raise HTTPException(
                status_code=400,
                detail="initial_capital must be positive"
            )
        
        # Save strategy to database
        strategy_name = request.strategy_config.name or f"Strategy {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"
        
        # Extract selected institutions from the request
        # The frontend may send this in different ways, so we need to handle both cases
        selected_institutions = []
        config_dict = request.strategy_config.dict()
        
        # Serialize dates to strings for JSON storage
        config_dict = serialize_dates(config_dict)
        
        # Try to get from stock_selection if it exists
        if 'stock_selection' in config_dict and isinstance(config_dict['stock_selection'], dict):
            selected_institutions = config_dict['stock_selection'].get('selected_institutions', [])
        # Or directly from the config
        elif 'selected_institutions' in config_dict:
            selected_institutions = config_dict['selected_institutions']
        
        strategy_id = save_strategy(
            name=strategy_name,
            config=config_dict,
            selected_institutions=selected_institutions
        )
        
        # Save backtest to database
        save_backtest(
            backtest_id=backtest_id,
            strategy_id=strategy_id,
            config=config_dict
        )
        
        # Create job record
        job_record = {
            'backtest_id': backtest_id,
            'strategy_id': strategy_id,
            'status': 'queued',
            'progress_pct': 0,
            'message': 'Backtest queued for execution',
            'request': serialize_dates(request.dict()),  # Serialize dates here too
            'created_at': datetime.utcnow(),
            'result': None
        }
        
        backtest_jobs[backtest_id] = job_record
        
        # Queue backtest execution in background
        background_tasks.add_task(
            execute_backtest_task,
            backtest_id=backtest_id,
            request=request
        )
        
        return BacktestStatus(
            backtest_id=backtest_id,
            status='queued',
            progress_pct=0,
            message='Backtest queued for execution'
        )
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        # Log the error and return a proper error response
        print(f"Error in run_backtest: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/{backtest_id}/status", response_model=BacktestStatus)
async def get_backtest_status(backtest_id: str):
    """
    Get the status of a running backtest
    
    Args:
        backtest_id: Backtest identifier
    
    Returns:
        BacktestStatus with current progress
    """
    if backtest_id not in backtest_jobs:
        raise HTTPException(status_code=404, detail="Backtest not found")
    
    job = backtest_jobs[backtest_id]
    
    return BacktestStatus(
        backtest_id=backtest_id,
        status=job['status'],
        progress_pct=job.get('progress_pct'),
        message=job.get('message'),
        estimated_completion_seconds=job.get('estimated_completion_seconds')
    )


@router.get("/{backtest_id}", response_model=BacktestResponse)
async def get_backtest_results(backtest_id: str):
    """
    Get the results of a completed backtest
    
    Args:
        backtest_id: Backtest identifier
    
    Returns:
        BacktestResponse with complete results
    """
    if backtest_id not in backtest_jobs:
        raise HTTPException(status_code=404, detail="Backtest not found")
    
    job = backtest_jobs[backtest_id]
    
    if job['status'] == 'running':
        raise HTTPException(
            status_code=409,
            detail=f"Backtest still running ({job.get('progress_pct', 0):.1f}% complete)"
        )
    
    if job['status'] == 'failed':
        raise HTTPException(
            status_code=500,
            detail=f"Backtest failed: {job.get('message', 'Unknown error')}"
        )
    
    if job['status'] != 'completed':
        raise HTTPException(
            status_code=400,
            detail=f"Backtest in unexpected state: {job['status']}"
        )
    
    result = job.get('result')
    
    if not result:
        raise HTTPException(
            status_code=500,
            detail="Backtest completed but no results found"
        )
    
    return result


@router.delete("/{backtest_id}")
async def cancel_backtest(backtest_id: str):
    """
    Cancel a running backtest or delete results
    
    Args:
        backtest_id: Backtest identifier
    
    Returns:
        Confirmation message
    """
    if backtest_id not in backtest_jobs:
        raise HTTPException(status_code=404, detail="Backtest not found")
    
    job = backtest_jobs[backtest_id]
    
    if job['status'] == 'running':
        # In production, would send cancel signal to worker
        job['status'] = 'cancelled'
        job['message'] = 'Backtest cancelled by user'
        
        return {
            'message': 'Backtest cancelled successfully',
            'backtest_id': backtest_id
        }
    else:
        # Delete completed/failed backtest
        del backtest_jobs[backtest_id]
        
        return {
            'message': 'Backtest deleted successfully',
            'backtest_id': backtest_id
        }


@router.get("/", response_model=List[BacktestStatus])
async def list_backtests(
    status: Optional[str] = None,
    limit: int = 50
):
    """
    List all backtests, optionally filtered by status
    
    Args:
        status: Filter by status (queued, running, completed, failed)
        limit: Maximum number of results
    
    Returns:
        List of BacktestStatus objects
    """
    jobs = list(backtest_jobs.values())
    
    # Filter by status if provided
    if status:
        jobs = [j for j in jobs if j['status'] == status]
    
    # Sort by creation time (newest first)
    jobs.sort(key=lambda x: x['created_at'], reverse=True)
    
    # Limit results
    jobs = jobs[:limit]
    
    # Convert to response format
    return [
        BacktestStatus(
            backtest_id=job['backtest_id'],
            status=job['status'],
            progress_pct=job.get('progress_pct'),
            message=job.get('message')
        )
        for job in jobs
    ]


# ==================== Background Task ====================

async def execute_backtest_task(backtest_id: str, request: BacktestRequest):
    """
    Execute backtest in background
    
    Args:
        backtest_id: Backtest identifier
        request: BacktestRequest configuration
    """
    try:
        # Update status to running
        backtest_jobs[backtest_id]['status'] = 'running'
        backtest_jobs[backtest_id]['message'] = 'Executing backtest...'
        backtest_jobs[backtest_id]['progress_pct'] = 10
        
        # TODO: Initialize LEAN worker
        # worker = BacktestWorker()
        
        # For now, simulate execution with mock data
        await asyncio.sleep(2)  # Simulate processing
        
        backtest_jobs[backtest_id]['progress_pct'] = 50
        backtest_jobs[backtest_id]['message'] = 'Processing trades...'
        
        await asyncio.sleep(2)
        
        backtest_jobs[backtest_id]['progress_pct'] = 80
        backtest_jobs[backtest_id]['message'] = 'Calculating metrics...'
        
        await asyncio.sleep(1)
        
        # Generate mock result (would be real LEAN output in production)
        result = _generate_mock_result(backtest_id, request)
        
        # Update job with results
        backtest_jobs[backtest_id]['status'] = 'completed'
        backtest_jobs[backtest_id]['progress_pct'] = 100
        backtest_jobs[backtest_id]['message'] = 'Backtest completed successfully'
        backtest_jobs[backtest_id]['result'] = result
        backtest_jobs[backtest_id]['completed_at'] = datetime.utcnow()
    
    except Exception as e:
        # Handle errors
        backtest_jobs[backtest_id]['status'] = 'failed'
        backtest_jobs[backtest_id]['message'] = f'Backtest failed: {str(e)}'


def _generate_mock_result(backtest_id: str, request: BacktestRequest) -> BacktestResponse:
    """
    Generate mock backtest result for testing
    
    In production, this would parse actual LEAN output.
    
    Args:
        backtest_id: Backtest identifier
        request: Original request
    
    Returns:
        BacktestResponse with mock data
    """
    from app.schemas.backtest_response import (
        BacktestSummary, EquityCurve, Trade
    )
    
    # Mock summary metrics
    summary = BacktestSummary(
        total_return=0.847,
        cagr=0.0623,
        volatility=0.182,
        sharpe_ratio=1.23,
        sortino_ratio=1.67,
        max_drawdown=-0.234,
        romad=0.266,
        alpha=0.032,
        beta=0.87,
        information_ratio=0.45,
        var_95=-0.023,
        cvar_95=-0.031,
        win_rate_daily=0.54,
        win_rate_monthly=0.61,
        win_rate_yearly=0.70,
        best_day=0.068,
        worst_day=-0.052,
        benchmark_total_return=0.612,
        benchmark_cagr=0.048
    )
    
    # Mock equity curve
    equity_curve = EquityCurve(
        dates=["2013-01-01", "2013-06-30", "2013-12-31"],
        portfolio_values=[1000000, 1120000, 1247000],
        benchmark_values=[1000000, 1085000, 1152000]
    )
    
    # Mock trades
    trades = [
        Trade(
            entry_date="2013-03-15",
            exit_date="2013-09-22",
            ticker="AAPL",
            entry_price=62.35,
            exit_price=71.20,
            shares=801.6,
            pnl=7091.16,
            return_pct=0.142,
            holding_period_days=191,
            exit_reason="trailing_stop",
            signal_type="doubling_down",
            conviction_score=72.5,
            rank=3
        )
    ]
    
    return BacktestResponse(
        backtest_id=backtest_id,
        status='completed',
        execution_time_seconds=5.3,
        summary=summary,
        equity_curve=equity_curve,
        trades=trades,
        strategy_name=request.strategy_config.name,
        start_date=str(request.strategy_config.backtest_period.start_date),
        end_date=str(request.strategy_config.backtest_period.end_date),
        initial_capital=request.strategy_config.initial_capital
    )

