"""
Validation API Endpoints
RESTful API for validation framework (walk-forward, Monte Carlo, sensitivity, stress test)
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Dict
import uuid
from datetime import datetime
import asyncio

from app.schemas.validation_request import (
    WalkForwardRequest,
    MonteCarloRequest,
    ParameterSensitivityRequest,
    StressTestRequest,
    ValidationSuite
)
from app.schemas.validation_response import (
    WalkForwardResponse,
    MonteCarloResponse,
    ParameterSensitivityResponse,
    StressTestResponse,
    ValidationSuiteResponse
)
from app.schemas.backtest_response import BacktestResponse, BacktestStatus

# Import validation services
from app.services.validation import (
    get_walk_forward_optimizer,
    get_monte_carlo_simulator,
    get_parameter_sensitivity_analyzer,
    get_stress_tester
)

router = APIRouter(prefix="/validation", tags=["Validation"])

# In-memory storage (would use Redis/DB in production)
validation_jobs = {}
# Mock backtest results storage (would query from database)
backtest_results_cache = {}


@router.post("/walk-forward", response_model=BacktestStatus, status_code=202)
async def run_walk_forward_optimization(
    request: WalkForwardRequest,
    background_tasks: BackgroundTasks
):
    """
    Run walk-forward optimization
    
    Tests strategy robustness by optimizing on train sets and validating on test sets.
    Returns Walk-Forward Efficiency (WFE) metrics and cluster matrix visualization data.
    """
    validation_id = f"wf_{uuid.uuid4().hex[:12]}"
    
    # Create job record
    job_record = {
        'validation_id': validation_id,
        'type': 'walk_forward',
        'status': 'queued',
        'progress_pct': 0,
        'message': 'Walk-forward optimization queued',
        'request': request.dict(),
        'created_at': datetime.utcnow(),
        'result': None
    }
    
    validation_jobs[validation_id] = job_record
    
    # Queue execution
    background_tasks.add_task(
        execute_walk_forward_task,
        validation_id=validation_id,
        request=request
    )
    
    return BacktestStatus(
        backtest_id=validation_id,
        status='queued',
        progress_pct=0,
        message='Walk-forward optimization queued'
    )


@router.post("/monte-carlo", response_model=BacktestStatus, status_code=202)
async def run_monte_carlo_simulation(
    request: MonteCarloRequest,
    background_tasks: BackgroundTasks
):
    """
    Run Monte Carlo simulation
    
    Shuffles trade sequences to generate probability distribution of returns.
    Returns confidence intervals and probability cone visualization data.
    """
    validation_id = f"mc_{uuid.uuid4().hex[:12]}"
    
    # Verify backtest exists
    if request.backtest_id not in backtest_results_cache:
        raise HTTPException(
            status_code=404,
            detail=f"Backtest {request.backtest_id} not found"
        )
    
    # Create job record
    job_record = {
        'validation_id': validation_id,
        'type': 'monte_carlo',
        'status': 'queued',
        'progress_pct': 0,
        'message': 'Monte Carlo simulation queued',
        'request': request.dict(),
        'created_at': datetime.utcnow(),
        'result': None
    }
    
    validation_jobs[validation_id] = job_record
    
    # Queue execution
    background_tasks.add_task(
        execute_monte_carlo_task,
        validation_id=validation_id,
        request=request
    )
    
    return BacktestStatus(
        backtest_id=validation_id,
        status='queued',
        progress_pct=0,
        message='Monte Carlo simulation queued'
    )


@router.post("/parameter-sensitivity", response_model=BacktestStatus, status_code=202)
async def run_parameter_sensitivity_analysis(
    request: ParameterSensitivityRequest,
    background_tasks: BackgroundTasks
):
    """
    Run parameter sensitivity analysis
    
    Tests strategy across 2D parameter grid to identify robustness islands.
    Returns heatmap data and robustness metrics.
    """
    validation_id = f"ps_{uuid.uuid4().hex[:12]}"
    
    # Create job record
    job_record = {
        'validation_id': validation_id,
        'type': 'parameter_sensitivity',
        'status': 'queued',
        'progress_pct': 0,
        'message': 'Parameter sensitivity analysis queued',
        'request': request.dict(),
        'created_at': datetime.utcnow(),
        'result': None
    }
    
    validation_jobs[validation_id] = job_record
    
    # Queue execution
    background_tasks.add_task(
        execute_sensitivity_task,
        validation_id=validation_id,
        request=request
    )
    
    return BacktestStatus(
        backtest_id=validation_id,
        status='queued',
        progress_pct=0,
        message='Parameter sensitivity analysis queued'
    )


@router.post("/stress-test", response_model=BacktestStatus, status_code=202)
async def run_stress_test(
    request: StressTestRequest,
    background_tasks: BackgroundTasks
):
    """
    Run stress testing analysis
    
    Evaluates strategy performance during historical crisis periods.
    Compares drawdown vs benchmark during crashes.
    """
    validation_id = f"st_{uuid.uuid4().hex[:12]}"
    
    # Verify backtest exists
    if request.backtest_id not in backtest_results_cache:
        raise HTTPException(
            status_code=404,
            detail=f"Backtest {request.backtest_id} not found"
        )
    
    # Create job record
    job_record = {
        'validation_id': validation_id,
        'type': 'stress_test',
        'status': 'queued',
        'progress_pct': 0,
        'message': 'Stress test queued',
        'request': request.dict(),
        'created_at': datetime.utcnow(),
        'result': None
    }
    
    validation_jobs[validation_id] = job_record
    
    # Queue execution
    background_tasks.add_task(
        execute_stress_test_task,
        validation_id=validation_id,
        request=request
    )
    
    return BacktestStatus(
        backtest_id=validation_id,
        status='queued',
        progress_pct=0,
        message='Stress test queued'
    )


@router.get("/{validation_id}/status", response_model=BacktestStatus)
async def get_validation_status(validation_id: str):
    """Get status of a validation job"""
    if validation_id not in validation_jobs:
        raise HTTPException(status_code=404, detail="Validation job not found")
    
    job = validation_jobs[validation_id]
    
    return BacktestStatus(
        backtest_id=validation_id,
        status=job['status'],
        progress_pct=job.get('progress_pct'),
        message=job.get('message')
    )


@router.get("/{validation_id}")
async def get_validation_results(validation_id: str):
    """Get results of a completed validation"""
    if validation_id not in validation_jobs:
        raise HTTPException(status_code=404, detail="Validation job not found")
    
    job = validation_jobs[validation_id]
    
    if job['status'] != 'completed':
        raise HTTPException(
            status_code=409,
            detail=f"Validation still {job['status']}"
        )
    
    return job.get('result')


# ==================== Background Tasks ====================

async def execute_walk_forward_task(validation_id: str, request: WalkForwardRequest):
    """Execute walk-forward optimization in background"""
    try:
        validation_jobs[validation_id]['status'] = 'running'
        
        optimizer = get_walk_forward_optimizer()
        
        def progress_callback(pct, msg):
            validation_jobs[validation_id]['progress_pct'] = pct
            validation_jobs[validation_id]['message'] = msg
        
        result = await optimizer.run_walk_forward_optimization(
            request=request,
            progress_callback=progress_callback
        )
        
        validation_jobs[validation_id]['status'] = 'completed'
        validation_jobs[validation_id]['result'] = result.dict()
    
    except Exception as e:
        validation_jobs[validation_id]['status'] = 'failed'
        validation_jobs[validation_id]['message'] = str(e)


async def execute_monte_carlo_task(validation_id: str, request: MonteCarloRequest):
    """Execute Monte Carlo simulation in background"""
    try:
        validation_jobs[validation_id]['status'] = 'running'
        
        simulator = get_monte_carlo_simulator()
        
        # Get original backtest results
        original_backtest = backtest_results_cache.get(request.backtest_id)
        
        def progress_callback(pct, msg):
            validation_jobs[validation_id]['progress_pct'] = pct
            validation_jobs[validation_id]['message'] = msg
        
        result = simulator.run_monte_carlo_simulation(
            original_backtest=original_backtest,
            config=request.monte_carlo_config,
            progress_callback=progress_callback
        )
        
        validation_jobs[validation_id]['status'] = 'completed'
        validation_jobs[validation_id]['result'] = result.dict()
    
    except Exception as e:
        validation_jobs[validation_id]['status'] = 'failed'
        validation_jobs[validation_id]['message'] = str(e)


async def execute_sensitivity_task(validation_id: str, request: ParameterSensitivityRequest):
    """Execute parameter sensitivity analysis in background"""
    try:
        validation_jobs[validation_id]['status'] = 'running'
        
        analyzer = get_parameter_sensitivity_analyzer()
        
        def progress_callback(pct, msg):
            validation_jobs[validation_id]['progress_pct'] = pct
            validation_jobs[validation_id]['message'] = msg
        
        result = await analyzer.run_sensitivity_analysis(
            request=request,
            progress_callback=progress_callback
        )
        
        validation_jobs[validation_id]['status'] = 'completed'
        validation_jobs[validation_id]['result'] = result.dict()
    
    except Exception as e:
        validation_jobs[validation_id]['status'] = 'failed'
        validation_jobs[validation_id]['message'] = str(e)


async def execute_stress_test_task(validation_id: str, request: StressTestRequest):
    """Execute stress test in background"""
    try:
        validation_jobs[validation_id]['status'] = 'running'
        
        tester = get_stress_tester()
        
        # Get original backtest results
        original_backtest = backtest_results_cache.get(request.backtest_id)
        
        def progress_callback(pct, msg):
            validation_jobs[validation_id]['progress_pct'] = pct
            validation_jobs[validation_id]['message'] = msg
        
        result = tester.run_stress_test(
            original_backtest=original_backtest,
            config=request.stress_test_config,
            progress_callback=progress_callback
        )
        
        validation_jobs[validation_id]['status'] = 'completed'
        validation_jobs[validation_id]['result'] = result.dict()
    
    except Exception as e:
        validation_jobs[validation_id]['status'] = 'failed'
        validation_jobs[validation_id]['message'] = str(e)

