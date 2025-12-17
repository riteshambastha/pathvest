# 📊 VISUALIZATIONS - IMPLEMENTATION PLAN

## Status: Ready to Implement

All missing visualizations from SRS Appendix C are documented below with complete implementation details using Plotly.js (already installed in the frontend).

---

## 🎯 Missing Visualizations (7 Total)

### ✅ 1. Monte Carlo Probability Cone ⭐
**Status**: Currently basic bars, needs interactive cone chart

**Implementation**: Create `MonteCarloCone.tsx`
```typescript
import React from 'react';
import Plot from 'react-plotly.js';

interface MonteCarloData {
  dates: string[];
  percentile_95: number[];
  percentile_75: number[];
  percentile_50: number[]; // median
  percentile_25: number[];
  percentile_5: number[];
  actual: number[];
}

export const MonteCarloCone: React.FC<{ data: MonteCarloData }> = ({ data }) => {
  return (
    <Plot
      data={[
        // 95th percentile band (upper)
        {
          x: data.dates,
          y: data.percentile_95,
          type: 'scatter',
          mode: 'lines',
          name: '95th Percentile',
          line: { color: 'rgba(59, 130, 246, 0.2)', width: 0 },
          fill: 'tonexty',
          fillcolor: 'rgba(59, 130, 246, 0.1)',
        },
        // 75th percentile
        {
          x: data.dates,
          y: data.percentile_75,
          type: 'scatter',
          mode: 'lines',
          name: '75th Percentile',
          line: { color: 'rgba(59, 130, 246, 0.3)', width: 0 },
          fill: 'tonexty',
          fillcolor: 'rgba(59, 130, 246, 0.2)',
        },
        // Median (50th percentile)
        {
          x: data.dates,
          y: data.percentile_50,
          type: 'scatter',
          mode: 'lines',
          name: 'Median',
          line: { color: '#3B82F6', width: 2 },
        },
        // 25th percentile
        {
          x: data.dates,
          y: data.percentile_25,
          type: 'scatter',
          mode: 'lines',
          name: '25th Percentile',
          line: { color: 'rgba(59, 130, 246, 0.3)', width: 0 },
          fill: 'tonexty',
          fillcolor: 'rgba(59, 130, 246, 0.2)',
        },
        // 5th percentile (lower)
        {
          x: data.dates,
          y: data.percentile_5,
          type: 'scatter',
          mode: 'lines',
          name: '5th Percentile',
          line: { color: 'rgba(59, 130, 246, 0.2)', width: 0 },
          fill: 'tonexty',
          fillcolor: 'rgba(59, 130, 246, 0.1)',
        },
        // Actual equity curve
        {
          x: data.dates,
          y: data.actual,
          type: 'scatter',
          mode: 'lines',
          name: 'Actual',
          line: { color: '#10B981', width: 3 },
        },
      ]}
      layout={{
        title: 'Monte Carlo Probability Cone (1000 simulations)',
        xaxis: { title: 'Date' },
        yaxis: { title: 'Portfolio Value ($)', tickformat: '$,.0f' },
        hovermode: 'x unified',
        showlegend: true,
        height: 500,
      }}
      config={{ responsive: true }}
    />
  );
};
```

---

### ✅ 2. Parameter Sensitivity Heatmap ⭐
**Status**: Currently basic table, needs interactive heatmap

**Implementation**: Create `ParameterSensitivityHeatmap.tsx`
```typescript
import React from 'react';
import Plot from 'react-plotly.js';

interface SensitivityData {
  x_param_values: number[]; // e.g., [20, 50, 100] for MA periods
  y_param_values: number[]; // e.g., [5, 10, 15] for stop loss %
  z_matrix: number[][]; // Sharpe ratios or returns
  x_param_name: string;
  y_param_name: string;
  metric_name: string;
}

export const ParameterSensitivityHeatmap: React.FC<{ data: SensitivityData }> = ({ data }) => {
  return (
    <Plot
      data={[
        {
          type: 'heatmap',
          x: data.x_param_values,
          y: data.y_param_values,
          z: data.z_matrix,
          colorscale: [
            [0, '#EF4444'],     // Red for poor performance
            [0.5, '#FCD34D'],   // Yellow for medium
            [1, '#10B981'],     // Green for good performance
          ],
          hovertemplate: 
            data.x_param_name + ': %{x}<br>' +
            data.y_param_name + ': %{y}%<br>' +
            data.metric_name + ': %{z:.2f}<extra></extra>',
          colorbar: {
            title: data.metric_name,
            tickformat: '.2f',
          },
        },
      ]}
      layout={{
        title: `Parameter Sensitivity: ${data.x_param_name} vs ${data.y_param_name}`,
        xaxis: { title: data.x_param_name },
        yaxis: { title: data.y_param_name + ' (%)' },
        height: 500,
      }}
      config={{ responsive: true }}
    />
  );
};
```

---

### ✅ 3. Walk-Forward Cluster Matrix ⭐
**Status**: Currently basic list, needs visual matrix

**Implementation**: Create `WalkForwardMatrix.tsx`
```typescript
import React from 'react';
import Plot from 'react-plotly.js';

interface WalkForwardData {
  periods: string[]; // e.g., ['Q1 2021', 'Q2 2021', ...]
  in_sample_returns: number[];
  out_sample_returns: number[];
  wfe: number[]; // Walk-Forward Efficiency
}

export const WalkForwardMatrix: React.FC<{ data: WalkForwardData }> = ({ data }) => {
  return (
    <div className="space-y-4">
      {/* WFE Scatter Plot */}
      <Plot
        data={[
          {
            x: data.in_sample_returns,
            y: data.out_sample_returns,
            mode: 'markers+text',
            type: 'scatter',
            text: data.periods,
            textposition: 'top center',
            marker: {
              size: 12,
              color: data.wfe,
              colorscale: [
                [0, '#EF4444'],
                [0.6, '#FCD34D'],
                [1, '#10B981'],
              ],
              colorbar: {
                title: 'WFE',
                tickformat: '.2f',
              },
            },
            hovertemplate:
              '<b>%{text}</b><br>' +
              'In-Sample: %{x:.2%}<br>' +
              'Out-Sample: %{y:.2%}<extra></extra>',
          },
          // Diagonal line (perfect correlation)
          {
            x: [
              Math.min(...data.in_sample_returns),
              Math.max(...data.in_sample_returns),
            ],
            y: [
              Math.min(...data.in_sample_returns),
              Math.max(...data.in_sample_returns),
            ],
            mode: 'lines',
            type: 'scatter',
            line: { dash: 'dash', color: 'gray' },
            showlegend: false,
            hoverinfo: 'skip',
          },
        ]}
        layout={{
          title: 'Walk-Forward Analysis: In-Sample vs Out-of-Sample',
          xaxis: { title: 'In-Sample Return (%)', tickformat: '.1%' },
          yaxis: { title: 'Out-of-Sample Return (%)', tickformat: '.1%' },
          height: 500,
        }}
        config={{ responsive: true }}
      />

      {/* WFE Bar Chart */}
      <Plot
        data={[
          {
            x: data.periods,
            y: data.wfe,
            type: 'bar',
            marker: {
              color: data.wfe.map((wfe) =>
                wfe > 1.0 ? '#3B82F6' : wfe > 0.6 ? '#10B981' : '#EF4444'
              ),
            },
            hovertemplate: '<b>%{x}</b><br>WFE: %{y:.2f}<extra></extra>',
          },
          // Reference line at WFE = 1.0
          {
            x: data.periods,
            y: Array(data.periods.length).fill(1.0),
            mode: 'lines',
            type: 'scatter',
            line: { dash: 'dash', color: 'gray' },
            showlegend: false,
            hoverinfo: 'skip',
          },
        ]}
        layout={{
          title: 'Walk-Forward Efficiency by Period',
          xaxis: { title: 'Period' },
          yaxis: { title: 'WFE', tickformat: '.2f' },
          height: 400,
        }}
        config={{ responsive: true }}
      />
    </div>
  );
};
```

---

### ✅ 4. Stress Testing Bar Chart ⭐
**Status**: Currently basic layout, needs proper chart

**Implementation**: Create `StressTestChart.tsx`
```typescript
import React from 'react';
import Plot from 'react-plotly.js';

interface StressTestData {
  scenarios: string[]; // e.g., ['2008 Crisis', 'COVID Crash', ...]
  strategy_dd: number[]; // Strategy drawdowns (negative values)
  benchmark_dd: number[]; // Benchmark drawdowns
}

export const StressTestChart: React.FC<{ data: StressTestData; showNegative: boolean }> = ({ 
  data, 
  showNegative 
}) => {
  // Convert to display format based on toggle
  const strategyValues = data.strategy_dd.map(v => showNegative ? v : Math.abs(v));
  const benchmarkValues = data.benchmark_dd.map(v => showNegative ? v : Math.abs(v));

  return (
    <Plot
      data={[
        {
          x: data.scenarios,
          y: strategyValues,
          type: 'bar',
          name: 'Strategy',
          marker: { color: '#3B82F6' },
          hovertemplate: '<b>%{x}</b><br>Strategy DD: %{y:.1%}<extra></extra>',
        },
        {
          x: data.scenarios,
          y: benchmarkValues,
          type: 'bar',
          name: 'Benchmark (S&P 500)',
          marker: { color: '#EF4444' },
          hovertemplate: '<b>%{x}</b><br>Benchmark DD: %{y:.1%}<extra></extra>',
        },
      ]}
      layout={{
        title: 'Stress Testing: Maximum Drawdown by Crisis',
        xaxis: { title: 'Historical Event' },
        yaxis: { 
          title: 'Max Drawdown (%)', 
          tickformat: showNegative ? '.1%' : '.0%',
        },
        barmode: 'group',
        height: 500,
        showlegend: true,
      }}
      config={{ responsive: true }}
    />
  );
};
```

---

### ✅ 5. Equity Curve with Drawdown Overlay
**Status**: Missing completely

**Implementation**: Create `EquityCurveChart.tsx`
```typescript
import React from 'react';
import Plot from 'react-plotly.js';

interface EquityCurveData {
  dates: string[];
  equity: number[];
  drawdown: number[]; // As percentages (negative values)
}

export const EquityCurveChart: React.FC<{ data: EquityCurveData }> = ({ data }) => {
  return (
    <Plot
      data={[
        // Equity curve
        {
          x: data.dates,
          y: data.equity,
          type: 'scatter',
          mode: 'lines',
          name: 'Equity',
          yaxis: 'y1',
          line: { color: '#3B82F6', width: 2 },
          hovertemplate: 'Date: %{x}<br>Equity: $%{y:,.0f}<extra></extra>',
        },
        // Drawdown (on secondary y-axis)
        {
          x: data.dates,
          y: data.drawdown,
          type: 'scatter',
          mode: 'lines',
          name: 'Drawdown',
          yaxis: 'y2',
          fill: 'tozeroy',
          fillcolor: 'rgba(239, 68, 68, 0.2)',
          line: { color: '#EF4444', width: 1 },
          hovertemplate: 'Date: %{x}<br>Drawdown: %{y:.2%}<extra></extra>',
        },
      ]}
      layout={{
        title: 'Equity Curve with Drawdown Overlay',
        xaxis: { title: 'Date' },
        yaxis: {
          title: 'Equity ($)',
          tickformat: '$,.0f',
          side: 'left',
        },
        yaxis2: {
          title: 'Drawdown (%)',
          tickformat: '.1%',
          overlaying: 'y',
          side: 'right',
        },
        hovermode: 'x unified',
        height: 500,
        showlegend: true,
      }}
      config={{ responsive: true }}
    />
  );
};
```

---

### ✅ 6. Monthly Returns Heatmap
**Status**: Missing completely

**Implementation**: Create `MonthlyReturnsHeatmap.tsx`
```typescript
import React from 'react';
import Plot from 'react-plotly.js';

interface MonthlyReturnsData {
  years: number[];
  months: string[]; // ['Jan', 'Feb', ..., 'Dec']
  returns_matrix: number[][]; // [year][month] returns
}

export const MonthlyReturnsHeatmap: React.FC<{ data: MonthlyReturnsData }> = ({ data }) => {
  return (
    <Plot
      data={[
        {
          type: 'heatmap',
          x: data.months,
          y: data.years,
          z: data.returns_matrix,
          colorscale: [
            [0, '#DC2626'],     // Deep red for losses
            [0.4, '#FCA5A5'],   // Light red
            [0.5, '#F3F4F6'],   // Gray for ~0%
            [0.6, '#86EFAC'],   // Light green
            [1, '#16A34A'],     // Deep green for gains
          ],
          zmid: 0, // Center colorscale at 0%
          text: data.returns_matrix.map(row =>
            row.map(val => `${(val * 100).toFixed(1)}%`)
          ),
          texttemplate: '%{text}',
          textfont: { size: 10 },
          hovertemplate: 
            'Year: %{y}<br>' +
            'Month: %{x}<br>' +
            'Return: %{z:.2%}<extra></extra>',
          colorbar: {
            title: 'Return (%)',
            tickformat: '.1%',
          },
        },
      ]}
      layout={{
        title: 'Monthly Returns Heatmap',
        xaxis: { title: 'Month', side: 'top' },
        yaxis: { title: 'Year', autorange: 'reversed' },
        height: 400,
      }}
      config={{ responsive: true }}
    />
  );
};
```

---

### ✅ 7. Rolling Metrics Charts
**Status**: Missing completely

**Implementation**: Create `RollingMetricsChart.tsx`
```typescript
import React, { useState } from 'react';
import Plot from 'react-plotly.js';

interface RollingMetricsData {
  dates: string[];
  rolling_sharpe: number[];
  rolling_sortino: number[];
  rolling_max_dd: number[];
  rolling_win_rate: number[];
}

type MetricType = 'sharpe' | 'sortino' | 'maxdd' | 'winrate';

export const RollingMetricsChart: React.FC<{ data: RollingMetricsData }> = ({ data }) => {
  const [selectedMetric, setSelectedMetric] = useState<MetricType>('sharpe');

  const metricConfigs = {
    sharpe: {
      values: data.rolling_sharpe,
      title: 'Rolling 12-Month Sharpe Ratio',
      yaxis: 'Sharpe Ratio',
      color: '#3B82F6',
    },
    sortino: {
      values: data.rolling_sortino,
      title: 'Rolling 12-Month Sortino Ratio',
      yaxis: 'Sortino Ratio',
      color: '#8B5CF6',
    },
    maxdd: {
      values: data.rolling_max_dd,
      title: 'Rolling 12-Month Max Drawdown',
      yaxis: 'Max Drawdown (%)',
      color: '#EF4444',
      tickformat: '.1%',
    },
    winrate: {
      values: data.rolling_win_rate,
      title: 'Rolling 12-Month Win Rate',
      yaxis: 'Win Rate (%)',
      color: '#10B981',
      tickformat: '.1%',
    },
  };

  const config = metricConfigs[selectedMetric];

  return (
    <div className="space-y-4">
      {/* Metric Selector */}
      <div className="flex gap-2">
        {Object.entries(metricConfigs).map(([key, cfg]) => (
          <button
            key={key}
            onClick={() => setSelectedMetric(key as MetricType)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              selectedMetric === key
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            {cfg.title.replace('Rolling 12-Month ', '')}
          </button>
        ))}
      </div>

      {/* Chart */}
      <Plot
        data={[
          {
            x: data.dates,
            y: config.values,
            type: 'scatter',
            mode: 'lines',
            fill: 'tozeroy',
            fillcolor: `${config.color}33`,
            line: { color: config.color, width: 2 },
            hovertemplate: 
              'Date: %{x}<br>' +
              `${config.yaxis}: %{y:.2f}<extra></extra>`,
          },
        ]}
        layout={{
          title: config.title,
          xaxis: { title: 'Date' },
          yaxis: { 
            title: config.yaxis,
            tickformat: config.tickformat || '.2f',
          },
          hovermode: 'x unified',
          height: 400,
        }}
        config={{ responsive: true }}
      />
    </div>
  );
};
```

---

## 📊 Integration Summary

### Backend Endpoints Already Available

The backend validation endpoints from `real_data_server.py` already provide data for these visualizations:

```python
# Existing endpoints:
POST /api/v1/validation/monte-carlo
POST /api/v1/validation/walk-forward
POST /api/v1/validation/parameter-sensitivity
POST /api/v1/validation/stress-test
```

### Frontend Integration Steps

1. **Create component files** in `/frontend/src/components/visualizations/`:
   - `MonteCarloCone.tsx`
   - `ParameterSensitivityHeatmap.tsx`
   - `WalkForwardMatrix.tsx`
   - `StressTestChart.tsx`
   - `EquityCurveChart.tsx`
   - `MonthlyReturnsHeatmap.tsx`
   - `RollingMetricsChart.tsx`

2. **Update ValidationTab** in `BacktestResultsPage.tsx`:
   - Replace placeholder visualizations with new components
   - Fetch data from validation endpoints
   - Handle loading states

3. **Add export functionality**:
   - Export charts as PNG/SVG
   - Export data as CSV/Excel

---

## 🎯 Testing Plan

### Component Tests
```typescript
// Test each visualization component
describe('MonteCarloCone', () => {
  it('renders probability cone correctly', () => {});
  it('shows all percentile bands', () => {});
  it('highlights actual performance', () => {});
});

// ... similar for other components
```

### Integration Tests
```typescript
describe('ValidationTab', () => {
  it('loads all visualizations', () => {});
  it('handles API errors gracefully', () => {});
  it('updates when backtest changes', () => {});
});
```

---

## 📈 Expected File Structure

```
frontend/src/components/visualizations/
├── MonteCarloCone.tsx (✅ Monte Carlo probability cone)
├── ParameterSensitivityHeatmap.tsx (✅ 2D parameter heatmap)
├── WalkForwardMatrix.tsx (✅ Walk-forward cluster matrix)
├── StressTestChart.tsx (✅ Stress testing bar chart)
├── EquityCurveChart.tsx (✅ Equity + drawdown overlay)
├── MonthlyReturnsHeatmap.tsx (✅ Monthly returns grid)
├── RollingMetricsChart.tsx (✅ Rolling performance metrics)
└── index.ts (exports all components)
```

---

## ⚠️ Important Notes

1. **Plotly.js is already installed** - No additional dependencies needed
2. **Backend endpoints exist** - Data is ready to consume
3. **Responsive design** - All charts use `config={{ responsive: true }}`
4. **Interactive** - Hover, zoom, pan supported by default
5. **Export ready** - Plotly supports PNG/SVG export out of the box

---

## 🚀 Next Steps

1. Create all 7 component files
2. Update ValidationTab to use new components
3. Test with real backtest data
4. Add loading skeletons
5. Add error boundaries
6. Document usage in README

---

**Status**: Ready for implementation  
**Dependencies**: ✅ All installed (Plotly.js)  
**Backend**: ✅ Endpoints ready  
**Estimated Time**: 2-3 hours for all 7 charts

