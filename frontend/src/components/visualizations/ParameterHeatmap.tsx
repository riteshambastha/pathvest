/**
 * Parameter Sensitivity Heatmap (FR-3.1.E.5.2)
 * 
 * Tests if the strategy is overfitted to specific parameters.
 * Visualizes a 2D grid of parameter combinations with performance metrics.
 * 
 * Goal: Identify a "Green Island" (broad region of profitability) 
 * rather than a single green peak surrounded by red (overfitting).
 */

import React, { useMemo } from 'react';
import Plot from 'react-plotly.js';

interface ParameterHeatmapProps {
  parameter1Name: string;
  parameter1Values: number[];
  parameter2Name: string;
  parameter2Values: number[];
  metricName: string;
  heatmapMatrix: number[][];
  bestParam1Value: number;
  bestParam2Value: number;
  bestMetricValue: number;
  robustRegionSize: number;
  totalCombinations: number;
}

export const ParameterHeatmap: React.FC<ParameterHeatmapProps> = ({
  parameter1Name,
  parameter1Values,
  parameter2Name,
  parameter2Values,
  metricName,
  heatmapMatrix,
  bestParam1Value,
  bestParam2Value,
  bestMetricValue,
  robustRegionSize,
  totalCombinations,
}) => {
  // Determine color scale based on metric type
  const colorScale = useMemo(() => {
    if (metricName.toLowerCase().includes('drawdown')) {
      // For drawdown, red is bad (more negative), green is good (less negative)
      return [
        [0, '#EF4444'],   // Red (worst)
        [0.5, '#FCD34D'], // Yellow (neutral)
        [1, '#10B981'],   // Green (best)
      ];
    }
    // For positive metrics (Sharpe, CAGR), green is good, red is bad
    return [
      [0, '#EF4444'],   // Red (worst)
      [0.5, '#FCD34D'], // Yellow (neutral)
      [1, '#10B981'],   // Green (best)
    ];
  }, [metricName]);

  // Format parameter labels
  const formatLabel = (value: number, name: string): string => {
    if (name.toLowerCase().includes('percent') || name.toLowerCase().includes('pct')) {
      return `${(value * 100).toFixed(0)}%`;
    }
    return value.toString();
  };

  const plotData = useMemo(() => {
    return [
      {
        z: heatmapMatrix,
        x: parameter2Values.map(v => formatLabel(v, parameter2Name)),
        y: parameter1Values.map(v => formatLabel(v, parameter1Name)),
        type: 'heatmap' as const,
        colorscale: colorScale,
        showscale: true,
        colorbar: {
          title: metricName,
          titleside: 'right' as const,
        },
        hovertemplate: 
          `${parameter1Name}: %{y}<br>` +
          `${parameter2Name}: %{x}<br>` +
          `${metricName}: %{z:.3f}<extra></extra>`,
      },
      // Mark best parameter combination
      {
        x: [formatLabel(bestParam2Value, parameter2Name)],
        y: [formatLabel(bestParam1Value, parameter1Name)],
        type: 'scatter' as const,
        mode: 'markers',
        marker: {
          size: 20,
          color: 'white',
          symbol: 'star',
          line: { color: '#1F2937', width: 2 },
        },
        name: 'Best Combination',
        showlegend: true,
      },
    ];
  }, [heatmapMatrix, parameter1Values, parameter2Values, colorScale, metricName, parameter1Name, parameter2Name, bestParam1Value, bestParam2Value]);

  const layout = {
    title: {
      text: `Parameter Sensitivity: ${metricName}`,
      font: { size: 18, color: '#1F2937' },
    },
    xaxis: {
      title: parameter2Name.replace(/_/g, ' ').replace(/\./g, ' → '),
      tickfont: { size: 11 },
    },
    yaxis: {
      title: parameter1Name.replace(/_/g, ' ').replace(/\./g, ' → '),
      tickfont: { size: 11 },
    },
    margin: { t: 60, r: 100, b: 80, l: 120 },
    paper_bgcolor: 'white',
    plot_bgcolor: 'white',
  };

  // Calculate robustness score
  const robustnessScore = useMemo(() => {
    const pct = (robustRegionSize / totalCombinations) * 100;
    if (pct >= 50) return { label: 'Excellent', color: 'text-green-600', bg: 'bg-green-50' };
    if (pct >= 30) return { label: 'Good', color: 'text-blue-600', bg: 'bg-blue-50' };
    if (pct >= 15) return { label: 'Moderate', color: 'text-yellow-600', bg: 'bg-yellow-50' };
    return { label: 'Poor (Potential Overfit)', color: 'text-red-600', bg: 'bg-red-50' };
  }, [robustRegionSize, totalCombinations]);

  return (
    <div className="bg-white rounded-lg shadow-lg p-6">
      {/* Header with Stats */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <div className="bg-gradient-to-br from-green-50 to-emerald-50 rounded-lg p-4 text-center">
          <p className="text-sm text-gray-600">Best {metricName}</p>
          <p className="text-2xl font-bold text-emerald-600">{bestMetricValue.toFixed(3)}</p>
        </div>
        <div className="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-lg p-4 text-center">
          <p className="text-sm text-gray-600">Best {parameter1Name.split('.').pop()}</p>
          <p className="text-2xl font-bold text-indigo-600">
            {formatLabel(bestParam1Value, parameter1Name)}
          </p>
        </div>
        <div className="bg-gradient-to-br from-purple-50 to-violet-50 rounded-lg p-4 text-center">
          <p className="text-sm text-gray-600">Best {parameter2Name.split('.').pop()}</p>
          <p className="text-2xl font-bold text-violet-600">
            {formatLabel(bestParam2Value, parameter2Name)}
          </p>
        </div>
        <div className={`${robustnessScore.bg} rounded-lg p-4 text-center`}>
          <p className="text-sm text-gray-600">Robustness</p>
          <p className={`text-lg font-bold ${robustnessScore.color}`}>
            {robustnessScore.label}
          </p>
          <p className="text-xs text-gray-500">
            {robustRegionSize}/{totalCombinations} ({((robustRegionSize / totalCombinations) * 100).toFixed(0)}%)
          </p>
        </div>
      </div>

      {/* Heatmap */}
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
          <li><span className="font-medium text-green-600">■ Green Region:</span> High performance zone - parameters that work well</li>
          <li><span className="font-medium text-yellow-600">■ Yellow Region:</span> Moderate performance - acceptable but not optimal</li>
          <li><span className="font-medium text-red-600">■ Red Region:</span> Poor performance - avoid these parameter combinations</li>
          <li><span className="font-medium">⭐ Star:</span> Best parameter combination found</li>
          <li className="mt-2 pt-2 border-t border-gray-200">
            <span className="font-semibold">Goal:</span> Look for a large "green island" (robust region). 
            A single green peak surrounded by red indicates potential overfitting.
          </li>
        </ul>
      </div>
    </div>
  );
};

export default ParameterHeatmap;

