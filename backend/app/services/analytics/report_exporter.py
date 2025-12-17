"""
Report Exporter
Exports backtest and validation results to CSV, Excel, and PDF formats
"""

import pandas as pd
from typing import List, Dict, Any, Optional
from io import BytesIO
import base64
from datetime import datetime

from app.schemas.backtest_response import BacktestResponse
from app.schemas.validation_response import (
    WalkForwardResponse,
    MonteCarloResponse,
    ParameterSensitivityResponse,
    StressTestResponse
)


class ReportExporter:
    """
    Export backtest and validation results to various formats
    
    Supported formats:
    1. CSV: Trade logs, equity curves
    2. Excel: Multi-sheet workbooks with all data
    3. PDF: Formatted reports with charts (requires reportlab)
    """
    
    def __init__(self):
        """Initialize report exporter"""
        pass
    
    # ==================== CSV Export ====================
    
    def export_trades_to_csv(self, trades: List[Dict]) -> str:
        """
        Export trade log to CSV
        
        Args:
            trades: List of trade dictionaries
        
        Returns:
            CSV string
        """
        if not trades:
            return ""
        
        df = pd.DataFrame(trades)
        
        # Select and order columns
        columns = [
            'entry_date', 'exit_date', 'ticker', 'entry_price', 'exit_price',
            'shares', 'pnl', 'return_pct', 'holding_period_days',
            'exit_reason', 'signal_type', 'conviction_score', 'rank'
        ]
        
        # Filter to existing columns
        columns = [c for c in columns if c in df.columns]
        df = df[columns]
        
        return df.to_csv(index=False)
    
    def export_equity_curve_to_csv(
        self,
        dates: List[str],
        portfolio_values: List[float],
        benchmark_values: Optional[List[float]] = None
    ) -> str:
        """
        Export equity curve to CSV
        
        Args:
            dates: Date strings
            portfolio_values: Portfolio values
            benchmark_values: Benchmark values (optional)
        
        Returns:
            CSV string
        """
        data = {
            'date': dates,
            'portfolio_value': portfolio_values
        }
        
        if benchmark_values:
            data['benchmark_value'] = benchmark_values
        
        df = pd.DataFrame(data)
        return df.to_csv(index=False)
    
    # ==================== Excel Export ====================
    
    def export_backtest_to_excel(
        self,
        backtest_result: BacktestResponse,
        attribution: Optional[Dict] = None
    ) -> bytes:
        """
        Export complete backtest results to Excel workbook
        
        Args:
            backtest_result: Backtest response
            attribution: Optional attribution analysis
        
        Returns:
            Excel file bytes
        """
        output = BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Sheet 1: Summary metrics
            summary_df = self._create_summary_dataframe(backtest_result)
            summary_df.to_excel(writer, sheet_name='Summary', index=False)
            
            # Sheet 2: Trade log
            if backtest_result.trades:
                trades_df = pd.DataFrame([t.dict() for t in backtest_result.trades])
                trades_df.to_excel(writer, sheet_name='Trades', index=False)
            
            # Sheet 3: Equity curve
            equity_df = pd.DataFrame({
                'date': backtest_result.equity_curve.dates,
                'portfolio_value': backtest_result.equity_curve.portfolio_values,
                'benchmark_value': backtest_result.equity_curve.benchmark_values
            })
            equity_df.to_excel(writer, sheet_name='Equity Curve', index=False)
            
            # Sheet 4: Monthly returns (if available)
            if backtest_result.monthly_returns:
                monthly_df = self._create_monthly_returns_dataframe(backtest_result.monthly_returns)
                monthly_df.to_excel(writer, sheet_name='Monthly Returns', index=False)
            
            # Sheet 5: Attribution (if provided)
            if attribution:
                self._add_attribution_sheets(writer, attribution)
        
        output.seek(0)
        return output.read()
    
    def export_validation_to_excel(
        self,
        walk_forward: Optional[WalkForwardResponse] = None,
        monte_carlo: Optional[MonteCarloResponse] = None,
        sensitivity: Optional[ParameterSensitivityResponse] = None,
        stress_test: Optional[StressTestResponse] = None
    ) -> bytes:
        """
        Export validation results to Excel workbook
        
        Args:
            walk_forward: Walk-forward results
            monte_carlo: Monte Carlo results
            sensitivity: Sensitivity results
            stress_test: Stress test results
        
        Returns:
            Excel file bytes
        """
        output = BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Walk-forward results
            if walk_forward:
                wf_df = pd.DataFrame([p.dict() for p in walk_forward.periods])
                wf_df.to_excel(writer, sheet_name='Walk-Forward', index=False)
                
                # Summary
                wf_summary = pd.DataFrame([{
                    'avg_wfe': walk_forward.avg_wfe,
                    'median_wfe': walk_forward.median_wfe,
                    'robust_periods': walk_forward.robust_periods_count,
                    'total_periods': walk_forward.total_periods
                }])
                wf_summary.to_excel(writer, sheet_name='WF Summary', index=False)
            
            # Monte Carlo results
            if monte_carlo:
                mc_summary = pd.DataFrame([{
                    'num_simulations': monte_carlo.num_simulations,
                    'original_sharpe': monte_carlo.original_sharpe,
                    'sharpe_mean': monte_carlo.sharpe_mean,
                    'sharpe_std': monte_carlo.sharpe_std,
                    'original_cagr': monte_carlo.original_cagr,
                    'cagr_mean': monte_carlo.cagr_mean,
                    'cagr_std': monte_carlo.cagr_std
                }])
                mc_summary.to_excel(writer, sheet_name='Monte Carlo', index=False)
                
                # Percentiles
                mc_percentiles = pd.DataFrame({
                    'metric': ['Sharpe', 'CAGR', 'Max DD'],
                    'p5': [
                        monte_carlo.sharpe_percentiles.get('5'),
                        monte_carlo.cagr_percentiles.get('5'),
                        monte_carlo.max_drawdown_percentiles.get('5')
                    ],
                    'p50': [
                        monte_carlo.sharpe_percentiles.get('50'),
                        monte_carlo.cagr_percentiles.get('50'),
                        monte_carlo.max_drawdown_percentiles.get('50')
                    ],
                    'p95': [
                        monte_carlo.sharpe_percentiles.get('95'),
                        monte_carlo.cagr_percentiles.get('95'),
                        monte_carlo.max_drawdown_percentiles.get('95')
                    ]
                })
                mc_percentiles.to_excel(writer, sheet_name='MC Percentiles', index=False)
            
            # Parameter sensitivity
            if sensitivity:
                # Heatmap as flattened table
                sens_data = []
                for i, param1_val in enumerate(sensitivity.parameter1_values):
                    for j, param2_val in enumerate(sensitivity.parameter2_values):
                        sens_data.append({
                            sensitivity.parameter1_name: param1_val,
                            sensitivity.parameter2_name: param2_val,
                            sensitivity.metric_name: sensitivity.heatmap_matrix[i][j]
                        })
                sens_df = pd.DataFrame(sens_data)
                sens_df.to_excel(writer, sheet_name='Parameter Sensitivity', index=False)
            
            # Stress test
            if stress_test:
                stress_df = pd.DataFrame([p.dict() for p in stress_test.periods])
                stress_df.to_excel(writer, sheet_name='Stress Test', index=False)
        
        output.seek(0)
        return output.read()
    
    # ==================== PDF Export (Basic) ====================
    
    def export_backtest_to_pdf(
        self,
        backtest_result: BacktestResponse
    ) -> bytes:
        """
        Export backtest summary to PDF
        
        Note: This is a simplified implementation. Full PDF generation
        with charts would require reportlab + matplotlib integration.
        
        Args:
            backtest_result: Backtest response
        
        Returns:
            PDF file bytes
        """
        # For now, return a text-based PDF summary
        # In production, would use reportlab for professional formatting
        
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.lib import colors
        
        output = BytesIO()
        doc = SimpleDocTemplate(output, pagesize=letter)
        story = []
        styles = getSampleStyleSheet()
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#3B82F6'),
            spaceAfter=30
        )
        story.append(Paragraph(f"Backtest Report: {backtest_result.strategy_name or 'Strategy'}", title_style))
        story.append(Spacer(1, 0.2 * inch))
        
        # Summary metrics
        story.append(Paragraph("Performance Summary", styles['Heading2']))
        summary_data = [
            ['Metric', 'Value'],
            ['Total Return', f"{backtest_result.summary.total_return * 100:.2f}%"],
            ['CAGR', f"{backtest_result.summary.cagr * 100:.2f}%"],
            ['Sharpe Ratio', f"{backtest_result.summary.sharpe_ratio:.2f}"],
            ['Sortino Ratio', f"{backtest_result.summary.sortino_ratio:.2f}"],
            ['Max Drawdown', f"{backtest_result.summary.max_drawdown * 100:.2f}%"],
            ['Volatility', f"{backtest_result.summary.volatility * 100:.2f}%"],
            ['Alpha', f"{backtest_result.summary.alpha * 100:.2f}%"],
            ['Beta', f"{backtest_result.summary.beta:.2f}"]
        ]
        
        summary_table = Table(summary_data, colWidths=[3 * inch, 2 * inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(summary_table)
        story.append(Spacer(1, 0.3 * inch))
        
        # Trade statistics
        story.append(Paragraph("Trade Statistics", styles['Heading2']))
        trade_data = [
            ['Metric', 'Value'],
            ['Win Rate (Daily)', f"{backtest_result.summary.win_rate_daily * 100:.1f}%"],
            ['Win Rate (Monthly)', f"{backtest_result.summary.win_rate_monthly * 100:.1f}%"],
            ['Best Day', f"{backtest_result.summary.best_day * 100:.2f}%"],
            ['Worst Day', f"{backtest_result.summary.worst_day * 100:.2f}%"]
        ]
        
        trade_table = Table(trade_data, colWidths=[3 * inch, 2 * inch])
        trade_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(trade_table)
        
        # Build PDF
        doc.build(story)
        output.seek(0)
        return output.read()
    
    # ==================== Helper Methods ====================
    
    def _create_summary_dataframe(self, backtest_result: BacktestResponse) -> pd.DataFrame:
        """Create summary metrics dataframe"""
        summary = backtest_result.summary
        
        data = {
            'Metric': [
                'Total Return', 'CAGR', 'Volatility', 'Sharpe Ratio',
                'Sortino Ratio', 'Max Drawdown', 'RoMaD', 'Alpha', 'Beta',
                'Information Ratio', 'VaR 95%', 'cVaR 95%',
                'Win Rate (Daily)', 'Win Rate (Monthly)', 'Win Rate (Yearly)',
                'Best Day', 'Worst Day', 'Benchmark Return', 'Benchmark CAGR'
            ],
            'Value': [
                f"{summary.total_return * 100:.2f}%",
                f"{summary.cagr * 100:.2f}%",
                f"{summary.volatility * 100:.2f}%",
                f"{summary.sharpe_ratio:.3f}",
                f"{summary.sortino_ratio:.3f}",
                f"{summary.max_drawdown * 100:.2f}%",
                f"{summary.romad:.3f}",
                f"{summary.alpha * 100:.2f}%",
                f"{summary.beta:.3f}",
                f"{summary.information_ratio:.3f}",
                f"{summary.var_95 * 100:.2f}%",
                f"{summary.cvar_95 * 100:.2f}%",
                f"{summary.win_rate_daily * 100:.1f}%",
                f"{summary.win_rate_monthly * 100:.1f}%",
                f"{summary.win_rate_yearly * 100:.1f}%",
                f"{summary.best_day * 100:.2f}%",
                f"{summary.worst_day * 100:.2f}%",
                f"{summary.benchmark_total_return * 100:.2f}%",
                f"{summary.benchmark_cagr * 100:.2f}%"
            ]
        }
        
        return pd.DataFrame(data)
    
    def _create_monthly_returns_dataframe(self, monthly_returns: List) -> pd.DataFrame:
        """Create monthly returns dataframe"""
        data = []
        for year_data in monthly_returns:
            row = {'Year': year_data.year}
            row.update(year_data.months)
            data.append(row)
        
        return pd.DataFrame(data)
    
    def _add_attribution_sheets(self, writer, attribution: Dict):
        """Add attribution analysis sheets to Excel writer"""
        # By signal type
        if 'by_signal_type' in attribution:
            signal_df = pd.DataFrame(attribution['by_signal_type']).T
            signal_df.to_excel(writer, sheet_name='By Signal Type')
        
        # By stock
        if 'by_stock' in attribution:
            stock_df = pd.DataFrame(attribution['by_stock'])
            stock_df.to_excel(writer, sheet_name='By Stock', index=False)
        
        # By holding period
        if 'by_holding_period' in attribution:
            holding_df = pd.DataFrame(attribution['by_holding_period'])
            holding_df.to_excel(writer, sheet_name='By Holding Period', index=False)


# Singleton instance
_exporter_instance = None


def get_report_exporter() -> ReportExporter:
    """Get singleton ReportExporter instance"""
    global _exporter_instance
    
    if _exporter_instance is None:
        _exporter_instance = ReportExporter()
    
    return _exporter_instance

