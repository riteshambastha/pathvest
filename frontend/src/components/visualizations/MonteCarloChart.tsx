/**
 * Monte Carlo Simulation Probability Cone (FR-3.1.E.5.1)
 * 
 * Visualizes the range of possible equity curves based on 
 * randomized trade shuffling with confidence intervals.
 * 
 * Components:
 * - Blue Line: Original Backtest Equity Curve
 * - Grey Lines: 100+ Simulated Runs
 * - Shaded Bands: 95% and 99% Confidence Intervals
 */

import React, { useMemo } from 'react';
import Plot from 'react-plotly.js';

interface MonteCarloChartProps {
  probabilityCone: {
    dates: string[];
    original: number[];
    p5: number[];
    p25: number[];
    p50: number[];
    p75: number[];
    p95: number[];
  };
  originalSharpe: number;
  sharpeMean: number;
  sharpeStd: number;
  numSimulations: number;
}

export const MonteCarloChart: React.FC<MonteCarloChartProps> = ({
  probabilityCone,
  originalSharpe,
  sharpeMean,
  sharpeStd,
  numSimulations,
}) => {
  const plotData = useMemo(() => {
    const { dates, original, p5, p25, p50, p75, p95 } = probabilityCone;

    return [
      // 95% Confidence Band (outermost)
      {
        x: [...dates, ...dates.slice().reverse()],
        y: [...p95, ...p5.slice().reverse()],
        fill: 'toself',
        fillcolor: 'rgba(99, 102, 241, 0.1)',
        line: { color: 'transparent' },
        name: '95% Confidence',
        showlegend: true,
        hoverinfo: 'skip',
      },
      // 50% Confidence Band (inner)
      {
        x: [...dates, ...dates.slice().reverse()],
        y: [...p75, ...p25.slice().reverse()],
        fill: 'toself',
        fillcolor: 'rgba(99, 102, 241, 0.25)',
        line: { color: 'transparent' },
        name: '50% Confidence',
        showlegend: true,
        hoverinfo: 'skip',
      },
      // Median simulation line
      {
        x: dates,
        y: p50,
        type: 'scatter' as const,
        mode: 'lines',
        line: { color: 'rgba(99, 102, 241, 0.6)', width: 2, dash: 'dot' },
        name: 'Median Simulation',
      },
      // Original backtest line
      {
        x: dates,
        y: original,
        type: 'scatter' as const,
        mode: 'lines',
        line: { color: '#3B82F6', width: 3 },
        name: 'Original Backtest',
      },
    ];
  }, [probabilityCone]);

  const layout = {
    title: {
      text: 'Monte Carlo Simulation: Probability Cone',
      font: { size: 18, color: '#1F2937' },
    },
    xaxis: {
      title: 'Date',
      showgrid: true,
      gridcolor: 'rgba(0,0,0,0.1)',
    },
    yaxis: {
      title: 'Portfolio Value ($)',
      showgrid: true,
      gridcolor: 'rgba(0,0,0,0.1)',
      tickformat: '$,.0f',
    },
    legend: {
      x: 0.01,
      y: 0.99,
      bgcolor: 'rgba(255,255,255,0.8)',
    },
    hovermode: 'x unified' as const,
    margin: { t: 50, r: 40, b: 50, l: 80 },
    paper_bgcolor: 'white',
    plot_bgcolor: 'white',
  };

  // Interpretation helper
  const coneWidth = useMemo(() => {
    if (sharpeStd === 0) return 'Unknown';
    const cv = sharpeStd / Math.abs(sharpeMean);
    if (cv < 0.2) return 'Narrow (Stable Strategy)';
    if (cv < 0.4) return 'Moderate';
    return 'Wide (High Luck Dependence)';
  }, [sharpeMean, sharpeStd]);

  return (
    <div className="bg-white rounded-lg shadow-lg p-6">
      {/* Header with Stats */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <div className="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-lg p-4 text-center">
          <p className="text-sm text-gray-600">Simulations Run</p>
          <p className="text-2xl font-bold text-indigo-600">{numSimulations.toLocaleString()}</p>
        </div>
        <div className="bg-gradient-to-br from-green-50 to-emerald-50 rounded-lg p-4 text-center">
          <p className="text-sm text-gray-600">Original Sharpe</p>
          <p className="text-2xl font-bold text-emerald-600">{originalSharpe.toFixed(2)}</p>
        </div>
        <div className="bg-gradient-to-br from-purple-50 to-violet-50 rounded-lg p-4 text-center">
          <p className="text-sm text-gray-600">Mean Sharpe (±σ)</p>
          <p className="text-2xl font-bold text-violet-600">
            {sharpeMean.toFixed(2)} ± {sharpeStd.toFixed(2)}
          </p>
        </div>
        <div className="bg-gradient-to-br from-amber-50 to-yellow-50 rounded-lg p-4 text-center">
          <p className="text-sm text-gray-600">Cone Width</p>
          <p className="text-lg font-bold text-amber-600">{coneWidth}</p>
        </div>
      </div>

      {/* Chart */}
      <Plot
        data={plotData as any}
        layout={layout}
        config={{ responsive: true, displayModeBar: false }}
        style={{ width: '100%', height: '450px' }}
      />

      {/* Interpretation Guide */}
      <div className="mt-4 p-4 bg-gray-50 rounded-lg">
        <h4 className="font-semibold text-gray-800 mb-2">📊 How to Interpret</h4>
        <ul className="text-sm text-gray-600 space-y-1">
          <li><span className="font-medium text-blue-600">■ Original Backtest:</span> Your actual strategy performance</li>
          <li><span className="font-medium text-indigo-400">■ Confidence Bands:</span> Range of possible outcomes (inner=50%, outer=95%)</li>
          <li><span className="font-medium">Narrow Cone:</span> Strategy is stable, less dependent on trade sequence</li>
          <li><span className="font-medium">Wide Cone:</span> Results may be luck-dependent, proceed with caution</li>
        </ul>
      </div>
    </div>
  );
};

export default MonteCarloChart;

