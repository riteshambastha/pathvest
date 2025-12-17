"""
Visualization Generator
Creates the 4 required visualizations for strategy validation (FR-3.1.E.5)
"""

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import numpy as np
from typing import List, Dict, Any, Optional
import base64
from io import BytesIO


class VisualizationGenerator:
    """
    Generate the 4 required visualizations (Appendix C):
    
    1. Monte Carlo Probability Cone
    2. Parameter Sensitivity Heatmap
    3. Walk-Forward Cluster Matrix
    4. Stress Testing Bar Chart
    """
    
    def __init__(self):
        """Initialize visualization generator"""
        self.theme_colors = {
            'primary': '#3B82F6',      # Blue
            'secondary': '#10B981',     # Green
            'danger': '#EF4444',        # Red
            'warning': '#F59E0B',       # Orange
            'neutral': '#6B7280'        # Gray
        }
    
    # ==================== 1. Monte Carlo Probability Cone ====================
    
    def generate_monte_carlo_cone(
        self,
        dates: List[str],
        original_curve: List[float],
        p5: List[float],
        p25: List[float],
        p50: List[float],
        p75: List[float],
        p95: List[float],
        title: str = "Monte Carlo Probability Cone",
        return_format: str = "html"
    ) -> Dict[str, Any]:
        """
        Generate Monte Carlo Probability Cone visualization
        
        Shows original equity curve with confidence intervals from simulations.
        Narrow cone = stable strategy, wide cone = luck-dependent.
        
        Args:
            dates: Date strings
            original_curve: Original backtest equity curve
            p5, p25, p50, p75, p95: Percentile curves from Monte Carlo
            title: Chart title
            return_format: 'html', 'json', or 'png'
        
        Returns:
            Dict with visualization data
        """
        fig = go.Figure()
        
        # Add 95% confidence band
        fig.add_trace(go.Scatter(
            x=dates,
            y=p95,
            mode='lines',
            name='95th Percentile',
            line=dict(width=0),
            showlegend=False,
            hoverinfo='skip'
        ))
        
        fig.add_trace(go.Scatter(
            x=dates,
            y=p5,
            mode='lines',
            name='95% Confidence',
            fill='tonexty',
            fillcolor='rgba(59, 130, 246, 0.1)',
            line=dict(width=0),
            showlegend=True,
            hoverinfo='skip'
        ))
        
        # Add 50% confidence band
        fig.add_trace(go.Scatter(
            x=dates,
            y=p75,
            mode='lines',
            name='75th Percentile',
            line=dict(width=0),
            showlegend=False,
            hoverinfo='skip'
        ))
        
        fig.add_trace(go.Scatter(
            x=dates,
            y=p25,
            mode='lines',
            name='50% Confidence',
            fill='tonexty',
            fillcolor='rgba(59, 130, 246, 0.2)',
            line=dict(width=0),
            showlegend=True,
            hoverinfo='skip'
        ))
        
        # Add median
        fig.add_trace(go.Scatter(
            x=dates,
            y=p50,
            mode='lines',
            name='Median',
            line=dict(color='rgba(107, 114, 128, 0.5)', width=1, dash='dash')
        ))
        
        # Add original backtest
        fig.add_trace(go.Scatter(
            x=dates,
            y=original_curve,
            mode='lines',
            name='Original Backtest',
            line=dict(color=self.theme_colors['primary'], width=3)
        ))
        
        fig.update_layout(
            title=title,
            xaxis_title="Date",
            yaxis_title="Portfolio Value ($)",
            hovermode='x unified',
            template='plotly_white',
            height=500
        )
        
        return self._format_output(fig, return_format)
    
    # ==================== 2. Parameter Sensitivity Heatmap ====================
    
    def generate_parameter_sensitivity_heatmap(
        self,
        matrix: List[List[float]],
        param1_name: str,
        param1_values: List[Any],
        param2_name: str,
        param2_values: List[Any],
        metric_name: str = "Sharpe Ratio",
        title: str = "Parameter Sensitivity Analysis",
        return_format: str = "html"
    ) -> Dict[str, Any]:
        """
        Generate Parameter Sensitivity Heatmap
        
        Shows strategy performance across 2D parameter grid.
        Goal: Identify "robustness islands" (broad green regions) vs overfitting (narrow peaks).
        
        Args:
            matrix: 2D array of metric values (param1 x param2)
            param1_name: Name of parameter 1 (Y-axis)
            param1_values: Values for parameter 1
            param2_name: Name of parameter 2 (X-axis)
            param2_values: Values for parameter 2
            metric_name: Name of metric being visualized
            title: Chart title
            return_format: 'html', 'json', or 'png'
        
        Returns:
            Dict with visualization data
        """
        # Convert values to strings for labels
        param1_labels = [str(v) for v in param1_values]
        param2_labels = [str(v) for v in param2_values]
        
        fig = go.Figure(data=go.Heatmap(
            z=matrix,
            x=param2_labels,
            y=param1_labels,
            colorscale=[
                [0, '#EF4444'],      # Red (poor)
                [0.3, '#F59E0B'],    # Orange
                [0.5, '#FCD34D'],    # Yellow
                [0.7, '#10B981'],    # Green
                [1, '#059669']       # Dark green (excellent)
            ],
            colorbar=dict(title=metric_name),
            hovertemplate=f'{param2_name}: %{{x}}<br>{param1_name}: %{{y}}<br>{metric_name}: %{{z:.3f}}<extra></extra>'
        ))
        
        # Add annotations for values
        annotations = []
        for i, param1_val in enumerate(param1_labels):
            for j, param2_val in enumerate(param2_labels):
                annotations.append(
                    dict(
                        x=param2_val,
                        y=param1_val,
                        text=f"{matrix[i][j]:.2f}",
                        showarrow=False,
                        font=dict(color='white' if matrix[i][j] > np.mean(matrix) else 'black', size=10)
                    )
                )
        
        fig.update_layout(
            title=title,
            xaxis_title=param2_name,
            yaxis_title=param1_name,
            annotations=annotations,
            template='plotly_white',
            height=500
        )
        
        return self._format_output(fig, return_format)
    
    # ==================== 3. Walk-Forward Cluster Matrix ====================
    
    def generate_walk_forward_cluster_matrix(
        self,
        matrix: List[List[float]],
        period_labels: Optional[List[str]] = None,
        run_labels: Optional[List[str]] = None,
        title: str = "Walk-Forward Cluster Matrix",
        return_format: str = "html"
    ) -> Dict[str, Any]:
        """
        Generate Walk-Forward Cluster Matrix
        
        Shows Walk-Forward Efficiency (WFE) across re-optimization periods.
        Green (0.6-1.2) = robust, Blue (>1.2) = high performance, Red (<0.6) = overfitted.
        
        Args:
            matrix: 2D array of WFE values (period x run)
            period_labels: Labels for periods (Y-axis)
            run_labels: Labels for runs (X-axis)
            title: Chart title
            return_format: 'html', 'json', or 'png'
        
        Returns:
            Dict with visualization data
        """
        # Generate labels if not provided
        if period_labels is None:
            period_labels = [f"Period {i+1}" for i in range(len(matrix))]
        
        if run_labels is None:
            run_labels = [f"Run {i+1}" for i in range(len(matrix[0]))] if matrix else []
        
        # Custom colorscale for WFE
        # Red: < 0.6 (overfitted)
        # Green: 0.6 - 1.2 (robust)
        # Blue: > 1.2 (excellent)
        fig = go.Figure(data=go.Heatmap(
            z=matrix,
            x=run_labels,
            y=period_labels,
            colorscale=[
                [0, '#EF4444'],      # Red (< 0.6, overfitted)
                [0.5, '#10B981'],    # Green (0.6-1.2, robust)
                [1, '#3B82F6']       # Blue (> 1.2, excellent)
            ],
            zmid=0.9,  # Center color scale around robust range
            colorbar=dict(title="WFE Score"),
            hovertemplate='Period: %{y}<br>Run: %{x}<br>WFE: %{z:.3f}<extra></extra>'
        ))
        
        # Add annotations
        annotations = []
        for i, period in enumerate(period_labels):
            for j, run in enumerate(run_labels):
                wfe = matrix[i][j]
                # Color code text
                text_color = 'white' if wfe < 0.8 or wfe > 1.1 else 'black'
                
                annotations.append(
                    dict(
                        x=run,
                        y=period,
                        text=f"{wfe:.2f}",
                        showarrow=False,
                        font=dict(color=text_color, size=10)
                    )
                )
        
        fig.update_layout(
            title=title,
            xaxis_title="Walk-Forward Run",
            yaxis_title="Optimization Period",
            annotations=annotations,
            template='plotly_white',
            height=500
        )
        
        return self._format_output(fig, return_format)
    
    # ==================== 4. Stress Testing Bar Chart ====================
    
    def generate_stress_test_bar_chart(
        self,
        period_names: List[str],
        strategy_drawdowns: List[float],
        benchmark_drawdowns: List[float],
        title: str = "Stress Testing: Strategy vs Benchmark",
        return_format: str = "html"
    ) -> Dict[str, Any]:
        """
        Generate Stress Testing Bar Chart
        
        Compares strategy drawdown vs benchmark during historical crisis periods.
        Goal: Strategy bars should be shorter (less negative) than benchmark bars.
        
        Args:
            period_names: Crisis period names
            strategy_drawdowns: Strategy max drawdowns (negative values)
            benchmark_drawdowns: Benchmark max drawdowns (negative values)
            title: Chart title
            return_format: 'html', 'json', or 'png'
        
        Returns:
            Dict with visualization data
        """
        fig = go.Figure()
        
        # Add strategy bars
        fig.add_trace(go.Bar(
            name='Strategy',
            x=period_names,
            y=strategy_drawdowns,
            marker_color=self.theme_colors['primary'],
            text=[f"{v:.1f}%" for v in strategy_drawdowns],
            textposition='outside'
        ))
        
        # Add benchmark bars
        fig.add_trace(go.Bar(
            name='Benchmark (S&P 500)',
            x=period_names,
            y=benchmark_drawdowns,
            marker_color=self.theme_colors['warning'],
            text=[f"{v:.1f}%" for v in benchmark_drawdowns],
            textposition='outside'
        ))
        
        fig.update_layout(
            title=title,
            xaxis_title="Crisis Period",
            yaxis_title="Maximum Drawdown (%)",
            barmode='group',
            template='plotly_white',
            height=500,
            yaxis=dict(
                ticksuffix='%',
                range=[min(min(strategy_drawdowns), min(benchmark_drawdowns)) * 1.1, 0]
            ),
            hovermode='x unified'
        )
        
        return self._format_output(fig, return_format)
    
    # ==================== Additional Visualizations ====================
    
    def generate_equity_curve(
        self,
        dates: List[str],
        portfolio_values: List[float],
        benchmark_values: Optional[List[float]] = None,
        title: str = "Equity Curve",
        return_format: str = "html"
    ) -> Dict[str, Any]:
        """Generate equity curve visualization"""
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=dates,
            y=portfolio_values,
            mode='lines',
            name='Strategy',
            line=dict(color=self.theme_colors['primary'], width=2)
        ))
        
        if benchmark_values:
            fig.add_trace(go.Scatter(
                x=dates,
                y=benchmark_values,
                mode='lines',
                name='Benchmark',
                line=dict(color=self.theme_colors['neutral'], width=2, dash='dash')
            ))
        
        fig.update_layout(
            title=title,
            xaxis_title="Date",
            yaxis_title="Portfolio Value ($)",
            hovermode='x unified',
            template='plotly_white',
            height=500
        )
        
        return self._format_output(fig, return_format)
    
    def generate_drawdown_chart(
        self,
        dates: List[str],
        equity_curve: List[float],
        title: str = "Drawdown",
        return_format: str = "html"
    ) -> Dict[str, Any]:
        """Generate drawdown chart"""
        # Calculate drawdown
        equity_array = np.array(equity_curve)
        running_max = np.maximum.accumulate(equity_array)
        drawdowns = (equity_array - running_max) / running_max * 100  # Convert to %
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=dates,
            y=drawdowns,
            mode='lines',
            name='Drawdown',
            fill='tozeroy',
            fillcolor='rgba(239, 68, 68, 0.2)',
            line=dict(color=self.theme_colors['danger'], width=2)
        ))
        
        fig.update_layout(
            title=title,
            xaxis_title="Date",
            yaxis_title="Drawdown (%)",
            hovermode='x unified',
            template='plotly_white',
            height=400,
            yaxis=dict(ticksuffix='%')
        )
        
        return self._format_output(fig, return_format)
    
    def generate_monthly_returns_heatmap(
        self,
        monthly_returns_matrix: List[List[float]],
        years: List[int],
        title: str = "Monthly Returns Heatmap",
        return_format: str = "html"
    ) -> Dict[str, Any]:
        """Generate monthly returns heatmap"""
        months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        
        fig = go.Figure(data=go.Heatmap(
            z=monthly_returns_matrix,
            x=months,
            y=[str(y) for y in years],
            colorscale='RdYlGn',
            zmid=0,
            colorbar=dict(title="Return (%)"),
            hovertemplate='%{y} %{x}<br>Return: %{z:.2f}%<extra></extra>'
        ))
        
        fig.update_layout(
            title=title,
            xaxis_title="Month",
            yaxis_title="Year",
            template='plotly_white',
            height=400
        )
        
        return self._format_output(fig, return_format)
    
    # ==================== Helper Methods ====================
    
    def _format_output(self, fig: go.Figure, return_format: str) -> Dict[str, Any]:
        """Format figure output based on requested format"""
        if return_format == "html":
            html = fig.to_html(include_plotlyjs='cdn', full_html=False)
            return {
                'format': 'html',
                'data': html
            }
        
        elif return_format == "json":
            return {
                'format': 'json',
                'data': fig.to_json()
            }
        
        elif return_format == "png":
            # Convert to PNG (requires kaleido)
            img_bytes = fig.to_image(format="png")
            img_base64 = base64.b64encode(img_bytes).decode()
            return {
                'format': 'png',
                'data': img_base64
            }
        
        else:
            raise ValueError(f"Unknown format: {return_format}")


# Singleton instance
_generator_instance = None


def get_visualization_generator() -> VisualizationGenerator:
    """Get singleton VisualizationGenerator instance"""
    global _generator_instance
    
    if _generator_instance is None:
        _generator_instance = VisualizationGenerator()
    
    return _generator_instance

