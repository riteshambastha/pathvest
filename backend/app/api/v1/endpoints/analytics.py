"""
Analytics API Endpoints by Ritesh Ambastha
RESTful API for analytics, visualizations, attribution, and exports
"""

from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import StreamingResponse, JSONResponse
from typing import Optional
import json
from io import BytesIO

from app.schemas.backtest_response import BacktestResponse
from app.services.analytics import (
    get_metrics_calculator,
    get_visualization_generator,
    get_attribution_analyzer,
    get_report_exporter
)

router = APIRouter(prefix="/analytics", tags=["Analytics"])

# Mock backtest results cache (would query from database in production)
backtest_results_cache = {}


@router.get("/{backtest_id}/metrics")
async def get_backtest_metrics(backtest_id: str):
    """
    Get comprehensive performance metrics for a backtest
    
    Returns all calculated metrics including return, risk, and risk-adjusted metrics.
    """
    if backtest_id not in backtest_results_cache:
        raise HTTPException(status_code=404, detail="Backtest not found")
    
    backtest = backtest_results_cache[backtest_id]
    calculator = get_metrics_calculator()
    
    # Calculate metrics
    metrics = calculator.calculate_all_metrics(
        equity_curve=backtest.equity_curve.portfolio_values,
        benchmark_curve=backtest.equity_curve.benchmark_values,
        dates=backtest.equity_curve.dates,
        trades=[t.dict() for t in backtest.trades]
    )
    
    return JSONResponse(content=metrics)


@router.get("/{backtest_id}/visualizations/monte-carlo-cone")
async def get_monte_carlo_cone_visualization(
    backtest_id: str,
    format: str = "html"
):
    """
    Get Monte Carlo probability cone visualization
    
    Args:
        format: 'html', 'json', or 'png'
    """
    # This would typically pull Monte Carlo results from validation
    # For demo, using mock data
    
    generator = get_visualization_generator()
    
    # Mock data
    dates = ["2013-01-01", "2015-01-01", "2017-01-01", "2019-01-01", "2021-01-01", "2023-12-31"]
    original = [1000000, 1200000, 1450000, 1680000, 1820000, 1847000]
    p5 = [970000, 1100000, 1250000, 1380000, 1450000, 1480000]
    p25 = [985000, 1150000, 1350000, 1520000, 1630000, 1680000]
    p50 = [995000, 1180000, 1400000, 1600000, 1720000, 1780000]
    p75 = [1005000, 1210000, 1470000, 1720000, 1850000, 1920000]
    p95 = [1030000, 1280000, 1580000, 1860000, 2050000, 2200000]
    
    viz = generator.generate_monte_carlo_cone(
        dates=dates,
        original_curve=original,
        p5=p5,
        p25=p25,
        p50=p50,
        p75=p75,
        p95=p95,
        return_format=format
    )
    
    if format == "html":
        return Response(content=viz['data'], media_type="text/html")
    elif format == "json":
        return JSONResponse(content=json.loads(viz['data']))
    elif format == "png":
        return Response(content=viz['data'], media_type="image/png")


@router.get("/{backtest_id}/visualizations/parameter-sensitivity")
async def get_parameter_sensitivity_heatmap(
    backtest_id: str,
    format: str = "html"
):
    """
    Get parameter sensitivity heatmap visualization
    
    Args:
        format: 'html', 'json', or 'png'
    """
    generator = get_visualization_generator()
    
    # Mock sensitivity data
    matrix = [
        [1.05, 1.18, 1.34, 1.29, 1.22],
        [1.12, 1.25, 1.45, 1.38, 1.28],
        [1.08, 1.22, 1.42, 1.35, 1.25],
        [1.02, 1.15, 1.32, 1.26, 1.18],
        [0.95, 1.08, 1.24, 1.19, 1.12]
    ]
    
    viz = generator.generate_parameter_sensitivity_heatmap(
        matrix=matrix,
        param1_name="Trailing Stop %",
        param1_values=[0.10, 0.12, 0.15, 0.18, 0.20],
        param2_name="SMA Period",
        param2_values=[30, 40, 50, 60, 70],
        metric_name="Sharpe Ratio",
        return_format=format
    )
    
    if format == "html":
        return Response(content=viz['data'], media_type="text/html")
    elif format == "json":
        return JSONResponse(content=json.loads(viz['data']))
    elif format == "png":
        return Response(content=viz['data'], media_type="image/png")


@router.get("/{backtest_id}/visualizations/walk-forward-matrix")
async def get_walk_forward_cluster_matrix(
    backtest_id: str,
    format: str = "html"
):
    """
    Get walk-forward cluster matrix visualization
    
    Args:
        format: 'html', 'json', or 'png'
    """
    generator = get_visualization_generator()
    
    # Mock walk-forward data
    matrix = [
        [0.85, 0.92],
        [0.78, 0.88],
        [0.91, 0.95],
        [0.82, 0.87],
        [0.89, 0.93]
    ]
    
    viz = generator.generate_walk_forward_cluster_matrix(
        matrix=matrix,
        period_labels=["2013-2015", "2015-2017", "2017-2019", "2019-2021", "2021-2023"],
        run_labels=["Run 1", "Run 2"],
        return_format=format
    )
    
    if format == "html":
        return Response(content=viz['data'], media_type="text/html")
    elif format == "json":
        return JSONResponse(content=json.loads(viz['data']))
    elif format == "png":
        return Response(content=viz['data'], media_type="image/png")


@router.get("/{backtest_id}/visualizations/stress-test")
async def get_stress_test_bar_chart(
    backtest_id: str,
    format: str = "html"
):
    """
    Get stress testing bar chart visualization
    
    Args:
        format: 'html', 'json', or 'png'
    """
    generator = get_visualization_generator()
    
    # Mock stress test data
    period_names = ["Dot Com Bubble", "2008 Crisis", "COVID Crash", "2022 Inflation"]
    strategy_drawdowns = [-28, -32, -15, -18]
    benchmark_drawdowns = [-45, -51, -34, -25]
    
    viz = generator.generate_stress_test_bar_chart(
        period_names=period_names,
        strategy_drawdowns=strategy_drawdowns,
        benchmark_drawdowns=benchmark_drawdowns,
        return_format=format
    )
    
    if format == "html":
        return Response(content=viz['data'], media_type="text/html")
    elif format == "json":
        return JSONResponse(content=json.loads(viz['data']))
    elif format == "png":
        return Response(content=viz['data'], media_type="image/png")


@router.get("/{backtest_id}/visualizations/equity-curve")
async def get_equity_curve_visualization(
    backtest_id: str,
    format: str = "html"
):
    """
    Get equity curve visualization
    
    Args:
        format: 'html', 'json', or 'png'
    """
    if backtest_id not in backtest_results_cache:
        raise HTTPException(status_code=404, detail="Backtest not found")
    
    backtest = backtest_results_cache[backtest_id]
    generator = get_visualization_generator()
    
    viz = generator.generate_equity_curve(
        dates=backtest.equity_curve.dates,
        portfolio_values=backtest.equity_curve.portfolio_values,
        benchmark_values=backtest.equity_curve.benchmark_values,
        return_format=format
    )
    
    if format == "html":
        return Response(content=viz['data'], media_type="text/html")
    elif format == "json":
        return JSONResponse(content=json.loads(viz['data']))
    elif format == "png":
        return Response(content=viz['data'], media_type="image/png")


@router.get("/{backtest_id}/attribution")
async def get_attribution_analysis(backtest_id: str):
    """
    Get attribution analysis for a backtest
    
    Breaks down performance by signal type, stock, time period, and holding period.
    """
    if backtest_id not in backtest_results_cache:
        raise HTTPException(status_code=404, detail="Backtest not found")
    
    backtest = backtest_results_cache[backtest_id]
    analyzer = get_attribution_analyzer()
    
    attribution = analyzer.analyze_attribution(
        trades=[t.dict() for t in backtest.trades],
        equity_curve=backtest.equity_curve.portfolio_values,
        dates=backtest.equity_curve.dates
    )
    
    return JSONResponse(content=attribution)


@router.get("/{backtest_id}/export/csv/trades")
async def export_trades_csv(backtest_id: str):
    """Export trade log to CSV"""
    if backtest_id not in backtest_results_cache:
        raise HTTPException(status_code=404, detail="Backtest not found")
    
    backtest = backtest_results_cache[backtest_id]
    exporter = get_report_exporter()
    
    csv_data = exporter.export_trades_to_csv([t.dict() for t in backtest.trades])
    
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=trades_{backtest_id}.csv"}
    )


@router.get("/{backtest_id}/export/csv/equity-curve")
async def export_equity_curve_csv(backtest_id: str):
    """Export equity curve to CSV"""
    if backtest_id not in backtest_results_cache:
        raise HTTPException(status_code=404, detail="Backtest not found")
    
    backtest = backtest_results_cache[backtest_id]
    exporter = get_report_exporter()
    
    csv_data = exporter.export_equity_curve_to_csv(
        dates=backtest.equity_curve.dates,
        portfolio_values=backtest.equity_curve.portfolio_values,
        benchmark_values=backtest.equity_curve.benchmark_values
    )
    
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=equity_curve_{backtest_id}.csv"}
    )


@router.get("/{backtest_id}/export/excel")
async def export_backtest_excel(backtest_id: str, include_attribution: bool = True):
    """Export complete backtest to Excel workbook"""
    if backtest_id not in backtest_results_cache:
        raise HTTPException(status_code=404, detail="Backtest not found")
    
    backtest = backtest_results_cache[backtest_id]
    exporter = get_report_exporter()
    
    # Get attribution if requested
    attribution = None
    if include_attribution:
        analyzer = get_attribution_analyzer()
        attribution = analyzer.analyze_attribution(
            trades=[t.dict() for t in backtest.trades],
            equity_curve=backtest.equity_curve.portfolio_values,
            dates=backtest.equity_curve.dates
        )
    
    excel_bytes = exporter.export_backtest_to_excel(backtest, attribution)
    
    return Response(
        content=excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=backtest_{backtest_id}.xlsx"}
    )


@router.get("/{backtest_id}/export/pdf")
async def export_backtest_pdf(backtest_id: str):
    """Export backtest summary to PDF"""
    if backtest_id not in backtest_results_cache:
        raise HTTPException(status_code=404, detail="Backtest not found")
    
    backtest = backtest_results_cache[backtest_id]
    exporter = get_report_exporter()
    
    pdf_bytes = exporter.export_backtest_to_pdf(backtest)
    
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=backtest_{backtest_id}.pdf"}
    )

