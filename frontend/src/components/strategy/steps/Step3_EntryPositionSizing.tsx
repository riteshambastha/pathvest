import React, { useState } from 'react';
import { StrategyConfig } from '../StrategyWizard';
import HelpPanel from '../../common/HelpPanel';
import { stepHelpContent } from '../helpContent';

interface StepProps {
  config: StrategyConfig;
  updateConfig: (updates: Partial<StrategyConfig>) => void;
  nextStep: () => void;
  prevStep: () => void;
}

const Step3_EntryPositionSizing: React.FC<StepProps> = ({ config, updateConfig, nextStep, prevStep }) => {
  const [isHelpOpen, setIsHelpOpen] = useState(false);
  const positionSizing = config.position_sizing || {
    method: 'equal_weight',
    max_position_size: 0.05,
    min_position_size: 0.03,
    max_positions: 20,
    min_positions: 5,
  };

  const updatePositionSizing = (updates: any) => {
    updateConfig({
      position_sizing: {
        ...positionSizing,
        ...updates,
      },
    });
  };

  const handleNext = () => {
    // Validation
    if (!positionSizing.method) {
      alert('Please select a position sizing method');
      return;
    }
    nextStep();
  };

  return (
    <div className="space-y-6">
      {/* Header with Help Button */}
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Entry & Position Sizing</h2>
          <p className="mt-1 text-sm text-gray-600">
            Define how to size positions and allocate capital across stocks
          </p>
        </div>
        <button
          onClick={() => setIsHelpOpen(true)}
          className="flex items-center space-x-2 px-4 py-2 bg-blue-50 text-blue-700 rounded-lg hover:bg-blue-100 transition border border-blue-200 group"
          title="Open help documentation"
        >
          <svg className="h-5 w-5 group-hover:scale-110 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span className="font-medium">Help</span>
        </button>
      </div>

      {/* Position Sizing Method */}
      <div className="bg-white p-5 rounded-lg border border-gray-200">
        <label className="block text-sm font-semibold text-gray-900 mb-4">
          Position Sizing Method
        </label>
        
        <div className="space-y-3">
          <label className="flex items-start cursor-pointer group">
            <input
              type="radio"
              name="sizing_method"
              value="equal_weight"
              checked={positionSizing.method === 'equal_weight'}
              onChange={() => updatePositionSizing({ method: 'equal_weight' })}
              className="mt-1 h-4 w-4 text-blue-600 focus:ring-blue-500"
            />
            <div className="ml-3">
              <div className="text-sm font-medium text-gray-900">
                Equal Weight
              </div>
              <div className="text-xs text-gray-600 mt-0.5">
                Allocate equal capital to each position (e.g., 5% each if 20 stocks)
              </div>
            </div>
          </label>

          <label className="flex items-start cursor-pointer group">
            <input
              type="radio"
              name="sizing_method"
              value="fixed_size"
              checked={positionSizing.method === 'fixed_size'}
              onChange={() => updatePositionSizing({ method: 'fixed_size' })}
              className="mt-1 h-4 w-4 text-blue-600 focus:ring-blue-500"
            />
            <div className="ml-3">
              <div className="text-sm font-medium text-gray-900">
                Fixed Size (5%)
              </div>
              <div className="text-xs text-gray-600 mt-0.5">
                Each position is exactly 5% of portfolio (per SRS specification)
              </div>
            </div>
          </label>

          <label className="flex items-start cursor-pointer group">
            <input
              type="radio"
              name="sizing_method"
              value="conviction_weighted"
              checked={positionSizing.method === 'conviction_weighted'}
              onChange={() => updatePositionSizing({ method: 'conviction_weighted' })}
              className="mt-1 h-4 w-4 text-blue-600 focus:ring-blue-500"
            />
            <div className="ml-3">
              <div className="text-sm font-medium text-gray-900">
                Conviction Weighted
              </div>
              <div className="text-xs text-gray-600 mt-0.5">
                Allocate more to high-conviction signals (based on ranking algorithm)
              </div>
            </div>
          </label>
        </div>
      </div>

      {/* Position Size Constraints */}
      <div className="bg-white p-5 rounded-lg border border-gray-200">
        <h3 className="text-sm font-semibold text-gray-900 mb-4">Position Size Constraints</h3>
        
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-2">
              Max Position Size
            </label>
            <div className="relative">
              <input
                type="number"
                min="0.01"
                max="0.25"
                step="0.01"
                value={positionSizing.max_position_size * 100}
                onChange={(e) =>
                  updatePositionSizing({ max_position_size: parseFloat(e.target.value) / 100 })
                }
                className="w-full px-3 py-2 pr-8 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
              />
              <span className="absolute right-3 top-2 text-gray-500 text-sm">%</span>
            </div>
            <p className="mt-1 text-xs text-gray-500">Maximum capital per stock (default: 5%)</p>
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-700 mb-2">
              Min Position Size
            </label>
            <div className="relative">
              <input
                type="number"
                min="0.01"
                max="0.10"
                step="0.01"
                value={positionSizing.min_position_size * 100}
                onChange={(e) =>
                  updatePositionSizing({ min_position_size: parseFloat(e.target.value) / 100 })
                }
                className="w-full px-3 py-2 pr-8 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
              />
              <span className="absolute right-3 top-2 text-gray-500 text-sm">%</span>
            </div>
            <p className="mt-1 text-xs text-gray-500">Minimum capital per stock (default: 3%)</p>
          </div>
        </div>
      </div>

      {/* Portfolio Constraints */}
      <div className="bg-white p-5 rounded-lg border border-gray-200">
        <h3 className="text-sm font-semibold text-gray-900 mb-4">Portfolio Constraints</h3>
        
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-2">
              Max Positions
            </label>
            <input
              type="number"
              min="1"
              max="50"
              value={positionSizing.max_positions}
              onChange={(e) =>
                updatePositionSizing({ max_positions: parseInt(e.target.value) })
              }
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
            />
            <p className="mt-1 text-xs text-gray-500">Maximum number of stocks (default: 20)</p>
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-700 mb-2">
              Min Positions
            </label>
            <input
              type="number"
              min="1"
              max="20"
              value={positionSizing.min_positions}
              onChange={(e) =>
                updatePositionSizing({ min_positions: parseInt(e.target.value) })
              }
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
            />
            <p className="mt-1 text-xs text-gray-500">Minimum number of stocks (default: 5)</p>
          </div>
        </div>
      </div>

      {/* Cash Management */}
      <div className="bg-blue-50 p-4 rounded-lg border border-blue-200">
        <div className="flex items-start">
          <svg className="h-5 w-5 text-blue-400 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <div className="ml-3">
            <h4 className="text-sm font-medium text-blue-900">Cash Drag Management</h4>
            <p className="mt-1 text-xs text-blue-700">
              If fewer than {positionSizing.min_positions} candidates meet criteria, remaining capital stays in cash.
              This prevents forced entries into low-quality signals.
            </p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <div className="flex justify-between pt-6 border-t border-gray-200">
        <button
          onClick={prevStep}
          className="px-6 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50 transition"
        >
          ← Back
        </button>
        <button
          onClick={handleNext}
          className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition"
        >
          Continue →
        </button>
      </div>

      {/* Help Panel */}
      <HelpPanel
        isOpen={isHelpOpen}
        onClose={() => setIsHelpOpen(false)}
        content={stepHelpContent[3]}
      />
    </div>
  );
};

export default Step3_EntryPositionSizing;
