/**
 * Stress Testing Bar Chart (FR-3.1.E.5.4)
 * 
 * Benchmarks strategy drawdown against benchmark during known crisis events.
 * Side-by-side comparison shows how the strategy handles black swan events.
 * 
 * Default Crisis Events:
 * - Dot Com Bubble (2000-2002)
 * - 2008 Financial Crisis (2007-2009)
 * - COVID Crash (2020)
 * - Inflation Spike (2022)
 */

import React, { useMemo } from 'react';
import Plot from 'react-plotly.js';

interface StressPeriodResult {
  periodName: string;
  startDate: string;
  endDate: string;
  strategyMaxDrawdown: number;
  benchmarkMaxDrawdown: number;
  strategyVolatility: number;
  benchmarkVolatility: number;
  relativeDrawdown: number;
  strategySharpe?: number;
  benchmarkSharpe?: number;
}

interface StressTestChartProps {
  periods: StressPeriodResult[];
  avgRelativeDrawdown: number;
  worstStressPeriod: string;
  bestStressPeriod: string;
}

export const StressTestChart: React.FC<StressTestChartProps> = ({
  periods,
  avgRelativeDrawdown,
  worstStressPeriod,
  bestStressPeriod,
}) => {
  // Prepare chart data
  const plotData = useMemo(() => {
    return [
      {
        x: periods.map(p => p.periodName),
        y: periods.map(p => Math.abs(p.strategyMaxDrawdown) * 100),
        type: 'bar' as const,
        name: 'Strategy',
        marker: {
          color: '#3B82F6',
          pattern: {
            shape: '',
          },
        },
        text: periods.map(p => `${(Math.abs(p.strategyMaxDrawdown) * 100).toFixed(1)}%`),
        textposition: 'outside' as const,
        hovertemplate: periods.map(p => 
          `<b>${p.periodName}</b><br>` +
          `Period: ${p.startDate} to ${p.endDate}<br>` +
          `Strategy Drawdown: ${(Math.abs(p.strategyMaxDrawdown) * 100).toFixed(1)}%<br>` +
          `Strategy Volatility: ${(p.strategyVolatility * 100).toFixed(1)}%` +
          `<extra></extra>`
        ),
      },
      {
        x: periods.map(p => p.periodName),
        y: periods.map(p => Math.abs(p.benchmarkMaxDrawdown) * 100),
        type: 'bar' as const,
        name: 'S&P 500',
        marker: {
          color: '#F97316',
        },
        text: periods.map(p => `${(Math.abs(p.benchmarkMaxDrawdown) * 100).toFixed(1)}%`),
        textposition: 'outside' as const,
        hovertemplate: periods.map(p => 
          `<b>${p.periodName}</b><br>` +
          `Period: ${p.startDate} to ${p.endDate}<br>` +
          `Benchmark Drawdown: ${(Math.abs(p.benchmarkMaxDrawdown) * 100).toFixed(1)}%<br>` +
          `Benchmark Volatility: ${(p.benchmarkVolatility * 100).toFixed(1)}%` +
          `<extra></extra>`
        ),
      },
    ];
  }, [periods]);

  const layout = {
    title: {
      text: 'Stress Test: Strategy vs Benchmark During Crisis Periods',
      font: { size: 18, color: '#1F2937' },
    },
    xaxis: {
      title: 'Crisis Period',
      showgrid: false,
    },
    yaxis: {
      title: 'Maximum Drawdown (%)',
      showgrid: true,
      gridcolor: 'rgba(0,0,0,0.1)',
      autorange: 'reversed' as const, // Drawdowns are negative, show as positive going down
    },
    barmode: 'group' as const,
    bargap: 0.15,
    bargroupgap: 0.1,
    showlegend: true,
    legend: {
      x: 1,
      y: 1,
      xanchor: 'right' as const,
    },
    margin: { t: 60, r: 40, b: 80, l: 60 },
    paper_bgcolor: 'white',
    plot_bgcolor: 'white',
  };

  // Calculate overall assessment
  const assessment = useMemo(() => {
    // Count how many periods strategy outperformed benchmark
    const outperformed = periods.filter(
      p => Math.abs(p.strategyMaxDrawdown) < Math.abs(p.benchmarkMaxDrawdown)
    ).length;
    const pct = (outperformed / periods.length) * 100;
    
    if (pct >= 75 && avgRelativeDrawdown < 0.8) {
      return { label: 'Excellent Resilience', color: 'text-green-600', bg: 'bg-green-50', icon: '🛡️' };
    }
    if (pct >= 50) {
      return { label: 'Good Protection', color: 'text-blue-600', bg: 'bg-blue-50', icon: '✓' };
    }
    if (pct >= 25) {
      return { label: 'Mixed Results', color: 'text-yellow-600', bg: 'bg-yellow-50', icon: '⚠️' };
    }
    return { label: 'Weak Protection', color: 'text-red-600', bg: 'bg-red-50', icon: '⚡' };
  }, [periods, avgRelativeDrawdown]);

  return (
    <div className="bg-white rounded-lg shadow-lg p-6">
      {/* Header with Stats */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <div className="bg-gradient-to-br from-indigo-50 to-blue-50 rounded-lg p-4 text-center">
          <p className="text-sm text-gray-600">Crisis Periods Tested</p>
          <p className="text-2xl font-bold text-indigo-600">{periods.length}</p>
        </div>
        <div className="bg-gradient-to-br from-green-50 to-emerald-50 rounded-lg p-4 text-center">
          <p className="text-sm text-gray-600">Best Performance</p>
          <p className="text-lg font-bold text-emerald-600 truncate">{bestStressPeriod}</p>
        </div>
        <div className="bg-gradient-to-br from-red-50 to-rose-50 rounded-lg p-4 text-center">
          <p className="text-sm text-gray-600">Worst Performance</p>
          <p className="text-lg font-bold text-red-600 truncate">{worstStressPeriod}</p>
        </div>
        <div className={`${assessment.bg} rounded-lg p-4 text-center`}>
          <p className="text-sm text-gray-600">Overall Assessment</p>
          <p className={`text-lg font-bold ${assessment.color}`}>
            {assessment.icon} {assessment.label}
          </p>
        </div>
      </div>

      {/* Bar Chart */}
      <Plot
        data={plotData as any}
        layout={layout}
        config={{ responsive: true, displayModeBar: false }}
        style={{ width: '100%', height: '400px' }}
      />

      {/* Detailed Results Table */}
      <div className="mt-6 overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Crisis Event</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Period</th>
              <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Strategy DD</th>
              <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Benchmark DD</th>
              <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Relative</th>
              <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Result</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {periods.map((period, idx) => {
              const strategyBetter = Math.abs(period.strategyMaxDrawdown) < Math.abs(period.benchmarkMaxDrawdown);
              return (
                <tr key={idx} className="hover:bg-gray-50">
                  <td className="px-4 py-3 text-sm font-medium text-gray-900">
                    {period.periodName}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-500">
                    {period.startDate} → {period.endDate}
                  </td>
                  <td className="px-4 py-3 text-sm text-center font-semibold text-blue-600">
                    {(Math.abs(period.strategyMaxDrawdown) * 100).toFixed(1)}%
                  </td>
                  <td className="px-4 py-3 text-sm text-center font-semibold text-orange-600">
                    {(Math.abs(period.benchmarkMaxDrawdown) * 100).toFixed(1)}%
                  </td>
                  <td className="px-4 py-3 text-sm text-center text-gray-700">
                    {(period.relativeDrawdown * 100).toFixed(0)}%
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                      strategyBetter 
                        ? 'bg-green-100 text-green-800' 
                        : 'bg-red-100 text-red-800'
                    }`}>
                      {strategyBetter ? '✓ Protected' : '✗ Exposed'}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Interpretation Guide */}
      <div className="mt-6 p-4 bg-gray-50 rounded-lg">
        <h4 className="font-semibold text-gray-800 mb-2">📊 How to Interpret</h4>
        <ul className="text-sm text-gray-600 space-y-1">
          <li><span className="font-medium text-blue-600">■ Strategy (Blue):</span> Your strategy's max drawdown during crisis</li>
          <li><span className="font-medium text-orange-600">■ S&P 500 (Orange):</span> Benchmark's max drawdown for comparison</li>
          <li><strong>Relative Drawdown:</strong> Strategy DD ÷ Benchmark DD (lower is better)</li>
          <li className="mt-2">
            <strong>Goal:</strong> Strategy bars should be shorter than benchmark bars, indicating 
            better downside protection during market stress.
          </li>
        </ul>
      </div>
    </div>
  );
};

export default StressTestChart;

