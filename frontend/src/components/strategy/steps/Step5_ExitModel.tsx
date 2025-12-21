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

const Step5_ExitModel: React.FC<StepProps> = ({ config, updateConfig, nextStep, prevStep }) => {
  const [isHelpOpen, setIsHelpOpen] = useState(false);
  const exitRules = config.exit_rules || {
    thesis_drift_enabled: true,
    insider_reversal_enabled: true,
    trailing_stop_enabled: true,
    trailing_stop_pct: 0.15,
    take_profit_enabled: false,
    take_profit_pct: 0.30,
    dead_money_enabled: true,
    dead_money_quarters: 4,
    dead_money_threshold: 0.0,
    time_stop_enabled: false,
    max_holding_days: 365,
  };

  const updateExitRules = (updates: any) => {
    updateConfig({
      exit_rules: {
        ...exitRules,
        ...updates,
      },
    });
  };

  return (
    <div className="space-y-6">
      {/* Header with Help Button */}
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Exit Model</h2>
          <p className="mt-1 text-sm text-gray-600">
            Configure when and how to exit positions (4 modules per SRS specification)
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

      {/* Module 1: Thesis Drift */}
      <div className="bg-white p-5 rounded-lg border border-gray-200">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-gray-900">
            Module 1: Thesis Drift Detection
          </h3>
          <label className="flex items-center cursor-pointer">
            <input
              type="checkbox"
              checked={exitRules.thesis_drift_enabled}
              onChange={(e) => updateExitRules({ thesis_drift_enabled: e.target.checked })}
              className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
            />
            <span className="ml-2 text-sm text-gray-700">Enabled</span>
          </label>
        </div>
        <p className="text-xs text-gray-600">
          Exit if institutional thesis is invalidated (13F shows position reduction or elimination)
        </p>
        {exitRules.thesis_drift_enabled && (
          <div className="mt-3 p-3 bg-gray-50 rounded text-xs text-gray-700">
            ✓ Monitors quarterly 13F filings<br />
            ✓ Exits if institution reduces position by &gt;50%<br />
            ✓ Exits if institution eliminates position entirely
          </div>
        )}
      </div>

      {/* Module 2: Insider Reversal */}
      <div className="bg-white p-5 rounded-lg border border-gray-200">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-gray-900">
            Module 2: Insider Reversal
          </h3>
          <label className="flex items-center cursor-pointer">
            <input
              type="checkbox"
              checked={exitRules.insider_reversal_enabled}
              onChange={(e) => updateExitRules({ insider_reversal_enabled: e.target.checked })}
              className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
            />
            <span className="ml-2 text-sm text-gray-700">Enabled</span>
          </label>
        </div>
        <p className="text-xs text-gray-600">
          Exit if C-level insiders start selling (Form 4 transactions)
        </p>
        {exitRules.insider_reversal_enabled && (
          <div className="mt-3 p-3 bg-gray-50 rounded text-xs text-gray-700">
            ✓ Monitors Form 4 insider transactions<br />
            ✓ Exits if CEO/CFO sells &gt;25% of holdings<br />
            ✓ Cluster detection: 2+ insiders selling within 30 days
          </div>
        )}
      </div>

      {/* Module 3: Stop Loss / Take Profit */}
      <div className="bg-white p-5 rounded-lg border border-gray-200">
        <h3 className="text-sm font-semibold text-gray-900 mb-4">
          Module 3: Stop Loss & Take Profit
        </h3>
        
        {/* Trailing Stop */}
        <div className="mb-4">
          <div className="flex items-center justify-between mb-2">
            <label className="text-xs font-medium text-gray-700">
              Trailing Stop Loss
            </label>
            <label className="flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={exitRules.trailing_stop_enabled}
                onChange={(e) => updateExitRules({ trailing_stop_enabled: e.target.checked })}
                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
              />
              <span className="ml-2 text-sm text-gray-700">Enabled</span>
            </label>
          </div>
          {exitRules.trailing_stop_enabled && (
            <div className="relative">
              <input
                type="number"
                min="5"
                max="50"
                step="1"
                value={(exitRules.trailing_stop_pct ?? 0.15) * 100}
                onChange={(e) =>
                  updateExitRules({ trailing_stop_pct: parseFloat(e.target.value) / 100 })
                }
                className="w-full px-3 py-2 pr-8 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
              />
              <span className="absolute right-3 top-2 text-gray-500 text-sm">%</span>
            </div>
          )}
          <p className="mt-1 text-xs text-gray-500">
            Exit if price drops X% from peak (default: 15%)
          </p>
        </div>

        {/* Take Profit */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <label className="text-xs font-medium text-gray-700">
              Take Profit Target
            </label>
            <label className="flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={exitRules.take_profit_enabled}
                onChange={(e) => updateExitRules({ take_profit_enabled: e.target.checked })}
                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
              />
              <span className="ml-2 text-sm text-gray-700">Enabled</span>
            </label>
          </div>
          {exitRules.take_profit_enabled && (
            <div className="relative">
              <input
                type="number"
                min="10"
                max="100"
                step="5"
                value={(exitRules.take_profit_pct ?? 0.3) * 100}
                onChange={(e) =>
                  updateExitRules({ take_profit_pct: parseFloat(e.target.value) / 100 })
                }
                className="w-full px-3 py-2 pr-8 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
              />
              <span className="absolute right-3 top-2 text-gray-500 text-sm">%</span>
            </div>
          )}
          <p className="mt-1 text-xs text-gray-500">
            Exit if price gains X% from entry (default: 30%)
          </p>
        </div>
      </div>

      {/* Module 4: Dead Money Exit */}
      <div className="bg-white p-5 rounded-lg border border-gray-200">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-gray-900">
            Module 4: Dead Money Exit (Stale Positions)
          </h3>
          <label className="flex items-center cursor-pointer">
            <input
              type="checkbox"
              checked={exitRules.dead_money_enabled}
              onChange={(e) => updateExitRules({ dead_money_enabled: e.target.checked })}
              className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
            />
            <span className="ml-2 text-sm text-gray-700">Enabled</span>
          </label>
        </div>
        <p className="text-xs text-gray-600 mb-3">
          Exit positions that have been held too long without meaningful progress
        </p>
        {exitRules.dead_money_enabled && (
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-2">
                Holding Period (Quarters)
              </label>
              <input
                type="number"
                min="1"
                max="12"
                value={exitRules.dead_money_quarters}
                onChange={(e) => updateExitRules({ dead_money_quarters: parseInt(e.target.value) })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
              />
              <p className="mt-1 text-xs text-gray-500">Default: 4 quarters (1 year)</p>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-2">
                Min Return Threshold
              </label>
              <div className="relative">
                <input
                  type="number"
                  min="-20"
                  max="20"
                  step="1"
                  value={(exitRules.dead_money_threshold ?? 0.05) * 100}
                  onChange={(e) =>
                    updateExitRules({ dead_money_threshold: parseFloat(e.target.value) / 100 })
                  }
                  className="w-full px-3 py-2 pr-8 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                />
                <span className="absolute right-3 top-2 text-gray-500 text-sm">%</span>
              </div>
              <p className="mt-1 text-xs text-gray-500">Default: 0% (exit if flat/negative)</p>
            </div>
          </div>
        )}
      </div>

      {/* Time-Based Stop (Optional) */}
      <div className="bg-white p-5 rounded-lg border border-gray-200">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-gray-900">
            Optional: Maximum Holding Period
          </h3>
          <label className="flex items-center cursor-pointer">
            <input
              type="checkbox"
              checked={exitRules.time_stop_enabled}
              onChange={(e) => updateExitRules({ time_stop_enabled: e.target.checked })}
              className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
            />
            <span className="ml-2 text-sm text-gray-700">Enabled</span>
          </label>
        </div>
        {exitRules.time_stop_enabled && (
          <>
            <input
              type="number"
              min="30"
              max="730"
              step="30"
              value={exitRules.max_holding_days}
              onChange={(e) => updateExitRules({ max_holding_days: parseInt(e.target.value) })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
            />
            <p className="mt-1 text-xs text-gray-500">
              Force exit after X days regardless of performance (default: 365 days / 1 year)
            </p>
          </>
        )}
      </div>

      {/* Summary */}
      <div className="bg-blue-50 p-4 rounded-lg border border-blue-200">
        <h4 className="text-sm font-semibold text-blue-900 mb-2">Active Exit Modules</h4>
        <div className="space-y-1 text-xs text-blue-800">
          {exitRules.thesis_drift_enabled && (
            <div>✓ Thesis Drift Detection (Institutional invalidation)</div>
          )}
          {exitRules.insider_reversal_enabled && (
            <div>✓ Insider Reversal (Form 4 selling signals)</div>
          )}
          {exitRules.trailing_stop_enabled && (
            <div>✓ Trailing Stop Loss ({(exitRules.trailing_stop_pct ?? 0.15) * 100}% drawdown)</div>
          )}
          {exitRules.take_profit_enabled && (
            <div>✓ Take Profit ({(exitRules.take_profit_pct ?? 0.3) * 100}% gain target)</div>
          )}
          {exitRules.dead_money_enabled && (
            <div>✓ Dead Money Exit ({exitRules.dead_money_quarters}Q holding period)</div>
          )}
          {exitRules.time_stop_enabled && (
            <div>✓ Time Stop ({exitRules.max_holding_days} days max)</div>
          )}
          {!exitRules.thesis_drift_enabled &&
            !exitRules.insider_reversal_enabled &&
            !exitRules.trailing_stop_enabled &&
            !exitRules.dead_money_enabled && (
              <div className="text-amber-700">⚠️ No exit rules enabled - positions may be held indefinitely</div>
            )}
        </div>
      </div>

      {/* Help Panel */}
      <HelpPanel
        isOpen={isHelpOpen}
        onClose={() => setIsHelpOpen(false)}
        content={stepHelpContent[5]}
      />
    </div>
  );
};

export default Step5_ExitModel;
