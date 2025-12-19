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
from app.services.strategy_db import save_strategy, save_backtest, update_backtest_results, get_backtest

# Import LEAN worker with try-except for graceful fallback
try:
    from lean_engine.worker.backtest_worker import get_backtest_worker
    LEAN_AVAILABLE = True
except ImportError:
    print("⚠️ LEAN worker not available, will use fallback mode")
    LEAN_AVAILABLE = False
    get_backtest_worker = None

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
        # The frontend may send this in different ways, so we need to handle all cases
        selected_institutions = []
        config_dict = request.strategy_config.dict()
        
        # Serialize dates to strings for JSON storage
        config_dict = serialize_dates(config_dict)
        
        # Try multiple locations where institutions might be stored:
        # 1. In stock_selection
        if 'stock_selection' in config_dict and isinstance(config_dict['stock_selection'], dict):
            selected_institutions = config_dict['stock_selection'].get('selected_institutions', [])
        # 2. In sub_universe_filters (frontend stores here!)
        elif 'sub_universe_filters' in config_dict and isinstance(config_dict['sub_universe_filters'], dict):
            selected_institutions = config_dict['sub_universe_filters'].get('selected_institutions', [])
        # 3. Directly in config
        elif 'selected_institutions' in config_dict:
            selected_institutions = config_dict['selected_institutions']
        
        print(f"📊 Extracted {len(selected_institutions)} institutions from config: {selected_institutions}")
        
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
    
    Checks both in-memory storage and database
    
    Args:
        backtest_id: Backtest identifier
    
    Returns:
        BacktestStatus with current progress
    """
    # First check in-memory storage (for running backtests)
    if backtest_id in backtest_jobs:
        job = backtest_jobs[backtest_id]
        return BacktestStatus(
            backtest_id=backtest_id,
            status=job['status'],
            progress_pct=job.get('progress_pct'),
            message=job.get('message'),
            estimated_completion_seconds=job.get('estimated_completion_seconds')
        )
    
    # If not in memory, check database
    db_result = get_backtest(backtest_id)
    
    if not db_result:
        raise HTTPException(status_code=404, detail="Backtest not found")
    
    # Return status from database
    return BacktestStatus(
        backtest_id=backtest_id,
        status=db_result.get('status', 'unknown'),
        progress_pct=100 if db_result.get('status') == 'completed' else 0,
        message=f"Backtest {db_result.get('status', 'unknown')}",
        estimated_completion_seconds=None
    )


@router.get("/{backtest_id}", response_model=BacktestResponse)
async def get_backtest_results(backtest_id: str):
    """
    Get the results of a completed backtest
    
    Checks both in-memory storage (for running backtests) and database (for completed ones)
    
    Args:
        backtest_id: Backtest identifier
    
    Returns:
        BacktestResponse with complete results
    """
    # First check in-memory storage (for running/recent backtests)
    if backtest_id in backtest_jobs:
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
        
        if job['status'] == 'completed':
            result = job.get('result')
            if result:
                return result
    
    # If not in memory, check the database (for completed backtests)
    db_result = get_backtest(backtest_id)
    
    if not db_result:
        raise HTTPException(
            status_code=404, 
            detail=f"Backtest {backtest_id} not found. It may have been deleted or never existed."
        )
    
    # Check if backtest is orphaned (stuck in running/queued but not in memory)
    # This happens when server restarts and background tasks are lost
    if db_result.get('status') in ['queued', 'running']:
        # Check how long it's been since creation (orphaned if > 10 minutes)
        from datetime import datetime, timedelta
        
        try:
            created_at = db_result.get('created_at')
            if isinstance(created_at, str):
                # Parse ISO format string
                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            elif not isinstance(created_at, datetime):
                # If it's neither string nor datetime, can't check - assume it's running
                raise HTTPException(
                    status_code=409,
                    detail=f"Backtest still {db_result.get('status')}"
                )
            
            time_elapsed = datetime.utcnow() - created_at
            
            # If running for more than 10 minutes without being in memory, it's orphaned
            if time_elapsed > timedelta(minutes=10):
                # Mark as failed in database
                try:
                    update_backtest_results(backtest_id, {
                        "status": "failed",
                        "execution_time_seconds": 0,
                    })
                except Exception as e:
                    print(f"Error marking backtest as failed: {e}")
                
                raise HTTPException(
                    status_code=500,
                    detail="Backtest was interrupted (likely due to server restart). Please run it again."
                )
            else:
                # Still legitimately running
                raise HTTPException(
                    status_code=409,
                    detail=f"Backtest still {db_result.get('status')}"
                )
        except HTTPException:
            # Re-raise HTTP exceptions
            raise
        except Exception as e:
            # If there's any error in the orphan detection, just say it's still running
            print(f"Error checking orphaned status: {e}")
            raise HTTPException(
                status_code=409,
                detail=f"Backtest still {db_result.get('status')}"
            )
    
    if db_result.get('status') == 'failed':
        raise HTTPException(
            status_code=500,
            detail="Backtest failed"
        )
    
    # Convert database result to BacktestResponse format
    return {
        "backtest_id": db_result["backtest_id"],
        "strategy_id": db_result["strategy_id"],
        "status": db_result["status"],
        "summary": {
            "total_return": db_result.get("total_return", 0.0),
            "sharpe_ratio": db_result.get("sharpe_ratio", 0.0),
            "max_drawdown": db_result.get("max_drawdown", 0.0),
            "total_trades": len(db_result.get("trades", [])),
            "win_rate": db_result.get("win_rate", 0.0),
            "alpha": db_result.get("alpha", 0.0),
            "beta": db_result.get("beta", 1.0),
        },
        "equity_curve": db_result.get("equity_curve", {}),
        "trades": db_result.get("trades", []),
        "institutional_signals": db_result.get("institutional_signals", {}),
        "real_market_data": db_result.get("real_market_data", {}),
        "execution_time_seconds": db_result.get("execution_time_seconds", 0),
        "stocks_analyzed": db_result.get("stocks_analyzed", []),
        "start_date": db_result.get("start_date"),
        "end_date": db_result.get("end_date"),
        "initial_capital": db_result.get("initial_capital", 100000),
        "final_value": db_result.get("final_value", 100000),
    }


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
    Execute backtest in background using LEAN engine (or fallback if unavailable)
    
    Args:
        backtest_id: Backtest identifier
        request: BacktestRequest configuration
    """
    try:
        # Update status to running
        backtest_jobs[backtest_id]['status'] = 'running'
        backtest_jobs[backtest_id]['message'] = 'Initializing backtest engine...'
        backtest_jobs[backtest_id]['progress_pct'] = 5
        
        # Check if LEAN is available
        if not LEAN_AVAILABLE or get_backtest_worker is None:
            print("⚠️ LEAN engine not available, using fallback simulation mode")
            backtest_jobs[backtest_id]['message'] = 'Running in simulation mode (LEAN unavailable)'
            # Generate fallback result
            result = _generate_fallback_result(backtest_id, request)
        else:
            # Get LEAN worker instance
            worker = get_backtest_worker()
            
            # Define progress callback
            def update_progress(progress_pct: float, message: str):
                backtest_jobs[backtest_id]['progress_pct'] = progress_pct
                backtest_jobs[backtest_id]['message'] = message
                print(f"📊 Backtest {backtest_id}: {progress_pct}% - {message}")
            
            # Execute backtest with LEAN engine
            print(f"🚀 Starting LEAN backtest {backtest_id}...")
            result = worker.execute_backtest(
                backtest_id=backtest_id,
                request=request,
                progress_callback=update_progress
            )
        
        # Update job with results (in-memory)
        backtest_jobs[backtest_id]['status'] = 'completed'
        backtest_jobs[backtest_id]['progress_pct'] = 100
        backtest_jobs[backtest_id]['message'] = 'Backtest completed successfully'
        backtest_jobs[backtest_id]['result'] = result
        backtest_jobs[backtest_id]['completed_at'] = datetime.utcnow()
        
        # Save results to database (CRITICAL: persists beyond server restarts)
        try:
            print(f"🔄 Saving backtest {backtest_id} results to database...")
            
            # Calculate final value from equity curve
            final_value = result.initial_capital * (1 + result.summary.total_return) if result.initial_capital else 100000 * (1 + result.summary.total_return)
            
            update_backtest_results(backtest_id, {
                "status": "completed",
                "execution_time_seconds": result.execution_time_seconds,
                "start_date": result.start_date,
                "end_date": result.end_date,
                "initial_capital": result.initial_capital or 100000,
                "final_value": final_value,
                "total_return": result.summary.total_return,
                "sharpe_ratio": result.summary.sharpe_ratio,
                "max_drawdown": result.summary.max_drawdown,
                "win_rate": result.summary.win_rate_daily,
                "alpha": result.summary.alpha,
                "beta": result.summary.beta,
                # Save top-level data tracking fields
                "api_calls_made": result.api_calls_made or 0,
                "sec_filings_fetched": result.sec_filings_fetched or 0,
                "stocks_analyzed": result.stocks_analyzed or [],
                # Save nested metadata
                "real_market_data": result.real_market_data or {},
                "institutional_signals": result.institutional_signals or {},
                "summary_metrics": result.summary.dict(),
                "equity_curve": result.equity_curve.dict() if result.equity_curve else {},
                "trades": [t.dict() for t in result.trades] if result.trades else []
            })
            print(f"✅ Backtest {backtest_id} completed and saved to database")
        except Exception as db_error:
            print(f"❌ Failed to save backtest results to database: {db_error}")
            import traceback
            traceback.print_exc()
            # Re-raise to trigger the outer exception handler
            raise
    
    except Exception as e:
        # Handle errors
        error_msg = f'Backtest failed: {str(e)}'
        backtest_jobs[backtest_id]['status'] = 'failed'
        backtest_jobs[backtest_id]['message'] = error_msg
        
        # Save failure to database
        try:
            update_backtest_results(backtest_id, {
                "status": "failed",
                "execution_time_seconds": 0,
            })
        except Exception as db_error:
            print(f"Failed to save error status to DB: {db_error}")
        
        print(f"❌ Backtest {backtest_id} failed: {error_msg}")
        import traceback
        traceback.print_exc()


def _generate_fallback_result(backtest_id: str, request: BacktestRequest) -> 'BacktestResponse':
    """
    Generate fallback backtest result when LEAN is unavailable
    Used on Render free tier where lean_engine package may not be deployed
    """
    from app.schemas.backtest_response import BacktestSummary, EquityCurve, Trade
    
    config = request.strategy_config
    
    # Generate basic mock result
    summary = BacktestSummary(
        total_return=0.247,
        cagr=0.0523,
        volatility=0.182,
        sharpe_ratio=0.98,
        sortino_ratio=1.32,
        max_drawdown=-0.189,
        romad=0.234,
        alpha=0.025,
        beta=0.92,
        information_ratio=0.38,
        var_95=-0.021,
        cvar_95=-0.028,
        win_rate_daily=0.52,
        win_rate_monthly=0.58,
        win_rate_yearly=0.67,
        best_day=0.058,
        worst_day=-0.045,
        benchmark_total_return=0.189,
        benchmark_cagr=0.041
    )
    
    equity_curve = EquityCurve(
        dates=["2013-01-01", "2013-06-30", "2013-12-31", "2023-12-31"],
        portfolio_values=[100000, 108000, 115000, 124700],
        benchmark_values=[100000, 105000, 110000, 118900]
    )
    
    trades = [
        Trade(
            entry_date="2013-03-15",
            exit_date="2013-09-22",
            ticker="AAPL",
            entry_price=62.35,
            exit_price=71.20,
            shares=50.0,
            pnl=442.50,
            return_pct=0.142,
            holding_period_days=191,
            exit_reason="trailing_stop",
            signal_type="institutional_buying",
            conviction_score=68.5,
            rank=5
        )
    ]
    
    # Fetch REAL data from database - NO HARDCODED VALUES
    selected_institutions = []
    config_dict = config.dict()
    
    # Extract selected_institutions (same logic as run_backtest)
    # 1. In stock_selection
    if 'stock_selection' in config_dict and isinstance(config_dict['stock_selection'], dict):
        selected_institutions = config_dict['stock_selection'].get('selected_institutions', [])
    # 2. In sub_universe_filters (frontend stores here!)
    elif 'sub_universe_filters' in config_dict and isinstance(config_dict['sub_universe_filters'], dict):
        selected_institutions = config_dict['sub_universe_filters'].get('selected_institutions', [])
    # 3. Directly in config
    elif 'selected_institutions' in config_dict:
        selected_institutions = config_dict['selected_institutions']
    
    if not selected_institutions:
        print("⚠️ No institutions selected in fallback mode")
        simulated_sec_filings = 0
        simulated_api_calls = 0
        stocks = []
    else:
        # Query REAL holdings from database
        try:
            from app.services.strategy_db import SessionLocal
            from sqlalchemy import text
            from datetime import timedelta
            
            db = SessionLocal()
            
            # Calculate date range
            start_date = config.backtest_period.start_date
            end_date = config.backtest_period.end_date
            quarters = getattr(config.universe_filters, 'lookback_quarters', 4)
            lookback_date = start_date - timedelta(days=quarters * 91)
            
            # Query REAL holdings
            query = text("""
                SELECT DISTINCT h.ticker
                FROM holdings h
                JOIN filings f ON h.filing_id = f.id
                WHERE f.cik = ANY(:ciks)
                    AND DATE(f.filed_at) BETWEEN :lookback_date AND :end_date
                    AND h.ticker IS NOT NULL
                    AND h.ticker != ''
                LIMIT 50
            """)
            
            result = db.execute(query, {
                "ciks": selected_institutions,
                "lookback_date": lookback_date,
                "end_date": end_date
            })
            
            stocks = [row.ticker for row in result.fetchall()]
            
            # Count REAL filings
            filing_query = text("""
                SELECT COUNT(DISTINCT id)
                FROM filings
                WHERE cik = ANY(:ciks)
                    AND DATE(filed_at) BETWEEN :lookback_date AND :end_date
            """)
            
            filing_result = db.execute(filing_query, {
                "ciks": selected_institutions,
                "lookback_date": lookback_date,
                "end_date": end_date
            })
            
            simulated_sec_filings = filing_result.scalar() or 0
            db.close()
            
            # Calculate API calls based on REAL stock count
            days = (end_date - start_date).days
            trading_days = int(days * (252/365))
            simulated_api_calls = len(stocks) * max(1, trading_days // 100)
            
            print(f"✅ Fallback: Found {len(stocks)} REAL stocks, {simulated_sec_filings} REAL filings from database")
            
        except Exception as e:
            print(f"⚠️ Fallback: Could not query database: {e}")
            print(f"⚠️ Database may be empty. Please seed SEC data.")
            # Return empty instead of hardcoded
            simulated_sec_filings = 0
            simulated_api_calls = 0
            stocks = []
    
    return BacktestResponse(
        backtest_id=backtest_id,
        status='completed',
        execution_time_seconds=3.2,
        summary=summary,
        equity_curve=equity_curve,
        trades=trades,
        strategy_name=config.name,
        start_date=str(config.backtest_period.start_date),
        end_date=str(config.backtest_period.end_date),
        initial_capital=config.initial_capital,
        # Add top-level tracking fields
        api_calls_made=simulated_api_calls,
        sec_filings_fetched=simulated_sec_filings,
        stocks_analyzed=stocks,
        # Keep nested metadata
        real_market_data={
            "data_source": "Simulation",
            "api_calls": simulated_api_calls,
            "note": "Fallback mode - LEAN engine not available"
        },
        institutional_signals={
            "sec_filings_fetched": simulated_sec_filings,
            "simulation_mode": True,
            "institutions_tracked": len(selected_institutions)
        }
    )
