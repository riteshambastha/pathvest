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

const Step4_EntryScheduling: React.FC<StepProps> = ({ config, updateConfig, nextStep, prevStep }) => {
  const [isHelpOpen, setIsHelpOpen] = useState(false);
  const entryRules = config.entry_rules || {
    timing: 'immediate',
    execution_delay: 1,
    entry_window_days: 5,
    technical_confirmation: true,
    use_limit_orders: false,
    max_slippage_pct: 0.01,
  };

  const updateEntryRules = (updates: any) => {
    updateConfig({
      entry_rules: {
        ...entryRules,
        ...updates,
      },
    });
  };

  return (
    <div className="space-y-6">
      {/* Header with Help Button */}
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Entry Scheduling</h2>
          <p className="mt-1 text-sm text-gray-600">
            Define when and how to enter positions after signals are generated
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

      {/* Entry Timing */}
      <div className="bg-white p-5 rounded-lg border border-gray-200">
        <label className="block text-sm font-semibold text-gray-900 mb-4">
          Entry Timing
        </label>
        
        <div className="space-y-3">
          <label className="flex items-start cursor-pointer group">
            <input
              type="radio"
              name="timing"
              value="immediate"
              checked={entryRules.timing === 'immediate'}
              onChange={() => updateEntryRules({ timing: 'immediate' })}
              className="mt-1 h-4 w-4 text-blue-600 focus:ring-blue-500"
            />
            <div className="ml-3">
              <div className="text-sm font-medium text-gray-900">
                Immediate (Next Day Open)
              </div>
              <div className="text-xs text-gray-600 mt-0.5">
                Enter at market open on T+1 (next trading day after signal)
              </div>
            </div>
          </label>

          <label className="flex items-start cursor-pointer group">
            <input
              type="radio"
              name="timing"
              value="end_of_day"
              checked={entryRules.timing === 'end_of_day'}
              onChange={() => updateEntryRules({ timing: 'end_of_day' })}
              className="mt-1 h-4 w-4 text-blue-600 focus:ring-blue-500"
            />
            <div className="ml-3">
              <div className="text-sm font-medium text-gray-900">
                End of Day
              </div>
              <div className="text-xs text-gray-600 mt-0.5">
                Enter at market close on signal day
              </div>
            </div>
          </label>

          <label className="flex items-start cursor-pointer group">
            <input
              type="radio"
              name="timing"
              value="delayed"
              checked={entryRules.timing === 'delayed'}
              onChange={() => updateEntryRules({ timing: 'delayed' })}
              className="mt-1 h-4 w-4 text-blue-600 focus:ring-blue-500"
            />
            <div className="ml-3">
              <div className="text-sm font-medium text-gray-900">
                Delayed Entry
              </div>
              <div className="text-xs text-gray-600 mt-0.5">
                Wait for technical confirmation or better price
              </div>
            </div>
          </label>
        </div>
      </div>

      {/* Execution Parameters */}
      <div className="bg-white p-5 rounded-lg border border-gray-200">
        <h3 className="text-sm font-semibold text-gray-900 mb-4">Execution Parameters</h3>
        
        <div className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-2">
              Execution Delay (T+)
            </label>
            <select
              value={entryRules.execution_delay}
              onChange={(e) => updateEntryRules({ execution_delay: parseInt(e.target.value) })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
            >
              <option value={0}>T+0 (Same day - Instant)</option>
              <option value={1}>T+1 (Next trading day - Realistic)</option>
              <option value={2}>T+2 (2 days delay)</option>
              <option value={3}>T+3 (3 days delay)</option>
            </select>
            <p className="mt-1 text-xs text-gray-500">
              Realistic delay between signal and execution (T+1 recommended for accuracy)
            </p>
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-700 mb-2">
              Entry Window (Max Days)
            </label>
            <input
              type="number"
              min="1"
              max="30"
              value={entryRules.entry_window_days}
              onChange={(e) => updateEntryRules({ entry_window_days: parseInt(e.target.value) })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
            />
            <p className="mt-1 text-xs text-gray-500">
              Maximum days to wait for entry after signal (default: 5 days)
            </p>
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-700 mb-2">
              Max Slippage Tolerance
            </label>
            <div className="relative">
              <input
                type="number"
                min="0"
                max="5"
                step="0.1"
                value={entryRules.max_slippage_pct * 100}
                onChange={(e) =>
                  updateEntryRules({ max_slippage_pct: parseFloat(e.target.value) / 100 })
                }
                className="w-full px-3 py-2 pr-8 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
              />
              <span className="absolute right-3 top-2 text-gray-500 text-sm">%</span>
            </div>
            <p className="mt-1 text-xs text-gray-500">
              Maximum price slippage allowed (default: 1%)
            </p>
          </div>
        </div>
      </div>

      {/* Order Type */}
      <div className="bg-white p-5 rounded-lg border border-gray-200">
        <h3 className="text-sm font-semibold text-gray-900 mb-4">Order Type</h3>
        
        <div className="space-y-3">
          <label className="flex items-center cursor-pointer">
            <input
              type="checkbox"
              checked={entryRules.use_limit_orders}
              onChange={(e) => updateEntryRules({ use_limit_orders: e.target.checked })}
              className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
            />
            <span className="ml-3 text-sm text-gray-700">Use Limit Orders (instead of Market Orders)</span>
          </label>
          
          <label className="flex items-center cursor-pointer">
            <input
              type="checkbox"
              checked={entryRules.technical_confirmation}
              onChange={(e) => updateEntryRules({ technical_confirmation: e.target.checked })}
              className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
            />
            <span className="ml-3 text-sm text-gray-700">Require Technical Confirmation</span>
          </label>
        </div>
      </div>

      {/* Technical Confirmation Settings */}
      {entryRules.technical_confirmation && (
        <div className="bg-amber-50 p-4 rounded-lg border border-amber-200">
          <h4 className="text-sm font-semibold text-amber-900 mb-2">Technical Confirmation</h4>
          <div className="space-y-2 text-xs text-amber-800">
            <div className="flex items-center">
              <svg className="h-4 w-4 text-amber-600 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              Price Breakout: Stock hits 20-day high
            </div>
            <div className="flex items-center">
              <svg className="h-4 w-4 text-amber-600 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              SMA Filter: Price above 50-day or 200-day moving average
            </div>
            <div className="flex items-center">
              <svg className="h-4 w-4 text-amber-600 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              RSI Filter: RSI between 30 and 70 (not overbought/oversold)
            </div>
          </div>
        </div>
      )}

      {/* Info Box */}
      <div className="bg-blue-50 p-4 rounded-lg border border-blue-200">
        <div className="flex items-start">
          <svg className="h-5 w-5 text-blue-400 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <div className="ml-3">
            <h4 className="text-sm font-medium text-blue-900">Recommended Settings</h4>
            <p className="mt-1 text-xs text-blue-700">
              For realistic backtesting, use T+1 execution delay and enable technical confirmation.
              This prevents look-ahead bias and ensures signals are actionable in real trading.
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
          onClick={nextStep}
          className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition"
        >
          Continue →
        </button>
      </div>

      {/* Help Panel */}
      <HelpPanel
        isOpen={isHelpOpen}
        onClose={() => setIsHelpOpen(false)}
        content={stepHelpContent[4]}
      />
    </div>
  );
};

export default Step4_EntryScheduling;
