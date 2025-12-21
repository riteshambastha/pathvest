/**
 * Walk-Forward Cluster Matrix (FR-3.1.E.5.3)
 * 
 * Validates if the strategy maintains performance on unseen data.
 * Shows Walk-Forward Efficiency (WFE) scores across re-optimization periods.
 * 
 * Color coding:
 * - Green: WFE 0.6 - 1.2 (Good/Robust)
 * - Blue: WFE > 1.2 (High Performance)
 * - Red: WFE < 0.6 (Poor/Overfitted)
 */

import React, { useMemo } from 'react';
import Plot from 'react-plotly.js';

interface WalkForwardPeriod {
  periodIndex: number;
  trainStart: string;
  trainEnd: string;
  testStart: string;
  testEnd: string;
  trainSharpe: number;
  testSharpe: number;
  wfe: number;
}

interface WalkForwardMatrixProps {
  periods: WalkForwardPeriod[];
  avgWfe: number;
  medianWfe: number;
  robustPeriodsCount: number;
  totalPeriods: number;
  clusterMatrix: number[][];
}

export const WalkForwardMatrix: React.FC<WalkForwardMatrixProps> = ({
  periods,
  avgWfe,
  medianWfe,
  robustPeriodsCount,
  totalPeriods,
  clusterMatrix,
}) => {
  // Color scale for WFE values
  const getWfeColor = (wfe: number): string => {
    if (wfe >= 1.2) return '#3B82F6'; // Blue - High performance
    if (wfe >= 0.6) return '#10B981'; // Green - Good/Robust
    return '#EF4444'; // Red - Poor/Overfitted
  };

  const getWfeLabel = (wfe: number): string => {
    if (wfe >= 1.2) return 'High';
    if (wfe >= 0.6) return 'Robust';
    return 'Poor';
  };

  // Create bar chart data for periods
  const barData = useMemo(() => {
    return [
      {
        x: periods.map(p => `P${p.periodIndex + 1}`),
        y: periods.map(p => p.wfe),
        type: 'bar' as const,
        marker: {
          color: periods.map(p => getWfeColor(p.wfe)),
        },
        text: periods.map(p => p.wfe.toFixed(2)),
        textposition: 'outside' as const,
        hovertemplate: periods.map(p => 
          `<b>Period ${p.periodIndex + 1}</b><br>` +
          `Train: ${p.trainStart} to ${p.trainEnd}<br>` +
          `Test: ${p.testStart} to ${p.testEnd}<br>` +
          `Train Sharpe: ${p.trainSharpe.toFixed(2)}<br>` +
          `Test Sharpe: ${p.testSharpe.toFixed(2)}<br>` +
          `<b>WFE: ${p.wfe.toFixed(2)}</b>` +
          `<extra></extra>`
        ),
      },
      // Reference lines
      {
        x: periods.map(p => `P${p.periodIndex + 1}`),
        y: periods.map(() => 1.0),
        type: 'scatter' as const,
        mode: 'lines',
        line: { color: '#6B7280', width: 2, dash: 'dash' },
        name: 'WFE = 1.0 (Ideal)',
        hoverinfo: 'skip' as const,
      },
      {
        x: periods.map(p => `P${p.periodIndex + 1}`),
        y: periods.map(() => 0.6),
        type: 'scatter' as const,
        mode: 'lines',
        line: { color: '#EF4444', width: 1, dash: 'dot' },
        name: 'WFE = 0.6 (Min Robust)',
        hoverinfo: 'skip' as const,
      },
    ];
  }, [periods]);

  const layout = {
    title: {
      text: 'Walk-Forward Efficiency by Period',
      font: { size: 18, color: '#1F2937' },
    },
    xaxis: {
      title: 'Walk-Forward Period',
      showgrid: false,
    },
    yaxis: {
      title: 'Walk-Forward Efficiency (WFE)',
      showgrid: true,
      gridcolor: 'rgba(0,0,0,0.1)',
      range: [0, Math.max(1.5, ...periods.map(p => p.wfe * 1.2))],
    },
    showlegend: true,
    legend: {
      x: 1,
      y: 1,
      xanchor: 'right' as const,
    },
    margin: { t: 60, r: 40, b: 60, l: 60 },
    paper_bgcolor: 'white',
    plot_bgcolor: 'white',
  };

  // Overall assessment
  const assessment = useMemo(() => {
    const robustPct = (robustPeriodsCount / totalPeriods) * 100;
    if (robustPct >= 80 && avgWfe >= 0.8) {
      return { label: 'Excellent', color: 'text-green-600', bg: 'bg-green-50', icon: '✅' };
    }
    if (robustPct >= 60 && avgWfe >= 0.6) {
      return { label: 'Good', color: 'text-blue-600', bg: 'bg-blue-50', icon: '👍' };
    }
    if (robustPct >= 40) {
      return { label: 'Moderate', color: 'text-yellow-600', bg: 'bg-yellow-50', icon: '⚠️' };
    }
    return { label: 'Poor (Likely Overfit)', color: 'text-red-600', bg: 'bg-red-50', icon: '❌' };
  }, [robustPeriodsCount, totalPeriods, avgWfe]);

  return (
    <div className="bg-white rounded-lg shadow-lg p-6">
      {/* Header with Stats */}
      <div className="grid grid-cols-5 gap-4 mb-6">
        <div className="bg-gradient-to-br from-indigo-50 to-blue-50 rounded-lg p-4 text-center">
          <p className="text-sm text-gray-600">Total Periods</p>
          <p className="text-2xl font-bold text-indigo-600">{totalPeriods}</p>
        </div>
        <div className="bg-gradient-to-br from-green-50 to-emerald-50 rounded-lg p-4 text-center">
          <p className="text-sm text-gray-600">Robust Periods</p>
          <p className="text-2xl font-bold text-emerald-600">
            {robustPeriodsCount}/{totalPeriods}
          </p>
          <p className="text-xs text-gray-500">
            ({((robustPeriodsCount / totalPeriods) * 100).toFixed(0)}%)
          </p>
        </div>
        <div className="bg-gradient-to-br from-purple-50 to-violet-50 rounded-lg p-4 text-center">
          <p className="text-sm text-gray-600">Average WFE</p>
          <p className="text-2xl font-bold text-violet-600">{avgWfe.toFixed(2)}</p>
        </div>
        <div className="bg-gradient-to-br from-amber-50 to-yellow-50 rounded-lg p-4 text-center">
          <p className="text-sm text-gray-600">Median WFE</p>
          <p className="text-2xl font-bold text-amber-600">{medianWfe.toFixed(2)}</p>
        </div>
        <div className={`${assessment.bg} rounded-lg p-4 text-center`}>
          <p className="text-sm text-gray-600">Assessment</p>
          <p className={`text-lg font-bold ${assessment.color}`}>
            {assessment.icon} {assessment.label}
          </p>
        </div>
      </div>

      {/* WFE Bar Chart */}
      <Plot
        data={barData as any}
        layout={layout}
        config={{ responsive: true, displayModeBar: false }}
        style={{ width: '100%', height: '400px' }}
      />

      {/* Period Details Table */}
      <div className="mt-6 overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Period</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Train Period</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Test Period</th>
              <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Train Sharpe</th>
              <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Test Sharpe</th>
              <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">WFE</th>
              <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Status</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {periods.map((period) => (
              <tr key={period.periodIndex} className="hover:bg-gray-50">
                <td className="px-4 py-3 text-sm font-medium text-gray-900">
                  P{period.periodIndex + 1}
                </td>
                <td className="px-4 py-3 text-sm text-gray-500">
                  {period.trainStart} → {period.trainEnd}
                </td>
                <td className="px-4 py-3 text-sm text-gray-500">
                  {period.testStart} → {period.testEnd}
                </td>
                <td className="px-4 py-3 text-sm text-center text-gray-700">
                  {period.trainSharpe.toFixed(2)}
                </td>
                <td className="px-4 py-3 text-sm text-center text-gray-700">
                  {period.testSharpe.toFixed(2)}
                </td>
                <td className="px-4 py-3 text-sm text-center font-semibold"
                    style={{ color: getWfeColor(period.wfe) }}>
                  {period.wfe.toFixed(2)}
                </td>
                <td className="px-4 py-3 text-center">
                  <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                    period.wfe >= 0.6 ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                  }`}>
                    {getWfeLabel(period.wfe)}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Interpretation Guide */}
      <div className="mt-6 p-4 bg-gray-50 rounded-lg">
        <h4 className="font-semibold text-gray-800 mb-2">📊 Walk-Forward Efficiency (WFE) Interpretation</h4>
        <div className="grid grid-cols-3 gap-4 text-sm">
          <div className="flex items-center space-x-2">
            <div className="w-4 h-4 rounded" style={{ backgroundColor: '#3B82F6' }}></div>
            <span className="text-gray-600">WFE &gt; 1.2: <strong>High Performance</strong> (OOS exceeds In-Sample)</span>
          </div>
          <div className="flex items-center space-x-2">
            <div className="w-4 h-4 rounded" style={{ backgroundColor: '#10B981' }}></div>
            <span className="text-gray-600">WFE 0.6-1.2: <strong>Robust</strong> (Acceptable degradation)</span>
          </div>
          <div className="flex items-center space-x-2">
            <div className="w-4 h-4 rounded" style={{ backgroundColor: '#EF4444' }}></div>
            <span className="text-gray-600">WFE &lt; 0.6: <strong>Poor</strong> (Likely overfit)</span>
          </div>
        </div>
        <p className="mt-3 text-sm text-gray-600">
          <strong>WFE = Test Sharpe / Train Sharpe.</strong> A ratio near 1.0 indicates the strategy 
          performs similarly on unseen data as it did during optimization.
        </p>
      </div>
    </div>
  );
};

export default WalkForwardMatrix;

