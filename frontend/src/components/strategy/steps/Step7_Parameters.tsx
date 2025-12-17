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

const Step7_Parameters: React.FC<StepProps> = ({ config, updateConfig, nextStep, prevStep }) => {
  const [isHelpOpen, setIsHelpOpen] = useState(false);
  const transactionCosts = config.transaction_costs || {
    commission_per_trade: 0.0,
    commission_pct: 0.001,
    slippage_pct: 0.001,
    min_commission: 1.0,
  };

  const updateTransactionCosts = (updates: any) => {
    updateConfig({
      transaction_costs: {
        ...transactionCosts,
        ...updates,
      },
    });
  };

  return (
    <div className="space-y-6">
      {/* Header with Help Button */}
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Advanced Parameters</h2>
          <p className="mt-1 text-sm text-gray-600">
            Fine-tune transaction costs, technical indicators, and other advanced settings
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

      {/* Transaction Costs */}
      <div className="bg-white p-5 rounded-lg border border-gray-200">
        <h3 className="text-sm font-semibold text-gray-900 mb-4">Transaction Costs</h3>
        
        <div className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-2">
              Commission Model
            </label>
            <select
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
              onChange={(e) => {
                if (e.target.value === 'zero') {
                  updateTransactionCosts({ commission_per_trade: 0, commission_pct: 0 });
                } else if (e.target.value === 'fixed') {
                  updateTransactionCosts({ commission_per_trade: 1.0, commission_pct: 0 });
                } else if (e.target.value === 'percentage') {
                  updateTransactionCosts({ commission_per_trade: 0, commission_pct: 0.001 });
                }
              }}
            >
              <option value="zero">Zero Commission (Robinhood-style)</option>
              <option value="fixed">Fixed Per Trade ($1-10)</option>
              <option value="percentage">Percentage-Based (0.1%)</option>
            </select>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-2">
                Commission per Trade ($)
              </label>
              <input
                type="number"
                min="0"
                max="50"
                step="0.1"
                value={transactionCosts.commission_per_trade}
                onChange={(e) =>
                  updateTransactionCosts({ commission_per_trade: parseFloat(e.target.value) })
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-700 mb-2">
                Commission (%)
              </label>
              <div className="relative">
                <input
                  type="number"
                  min="0"
                  max="1"
                  step="0.01"
                  value={(transactionCosts.commission_pct ?? 0.001) * 100}
                  onChange={(e) =>
                    updateTransactionCosts({ commission_pct: parseFloat(e.target.value) / 100 })
                  }
                  className="w-full px-3 py-2 pr-8 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                />
                <span className="absolute right-3 top-2 text-gray-500 text-sm">%</span>
              </div>
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-700 mb-2">
              Market Impact / Slippage (%)
            </label>
            <div className="relative">
              <input
                type="number"
                min="0"
                max="1"
                step="0.01"
                value={(transactionCosts.slippage_pct ?? 0.001) * 100}
                onChange={(e) =>
                  updateTransactionCosts({ slippage_pct: parseFloat(e.target.value) / 100 })
                }
                className="w-full px-3 py-2 pr-8 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
              />
              <span className="absolute right-3 top-2 text-gray-500 text-sm">%</span>
            </div>
            <p className="mt-1 text-xs text-gray-500">
              Average price slippage per trade (default: 0.1% = 10 bps)
            </p>
          </div>
        </div>
      </div>

      {/* Technical Indicators */}
      <div className="bg-white p-5 rounded-lg border border-gray-200">
        <h3 className="text-sm font-semibold text-gray-900 mb-4">Technical Indicator Parameters</h3>
        
        <div className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-2">
              Simple Moving Average (SMA) Periods
            </label>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <input
                  type="number"
                  min="10"
                  max="100"
                  defaultValue={50}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                  placeholder="Short SMA (50)"
                />
                <p className="mt-1 text-xs text-gray-500">Short-term SMA</p>
              </div>
              <div>
                <input
                  type="number"
                  min="100"
                  max="300"
                  defaultValue={200}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                  placeholder="Long SMA (200)"
                />
                <p className="mt-1 text-xs text-gray-500">Long-term SMA</p>
              </div>
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-700 mb-2">
              RSI Period
            </label>
            <input
              type="number"
              min="7"
              max="30"
              defaultValue={14}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
              placeholder="RSI Period (14)"
            />
            <p className="mt-1 text-xs text-gray-500">
              Relative Strength Index lookback period (default: 14)
            </p>
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-700 mb-2">
              Price Breakout Lookback (Days)
            </label>
            <input
              type="number"
              min="10"
              max="60"
              defaultValue={20}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
              placeholder="Breakout Period (20)"
            />
            <p className="mt-1 text-xs text-gray-500">
              Number of days to check for price breakout (default: 20)
            </p>
          </div>
        </div>
      </div>

      {/* Signal Weights (Conviction Scoring) */}
      <div className="bg-white p-5 rounded-lg border border-gray-200">
        <h3 className="text-sm font-semibold text-gray-900 mb-4">
          Conviction Scoring Weights
        </h3>
        <p className="text-xs text-gray-600 mb-4">
          Adjust the importance of each signal type in the conviction ranking algorithm
        </p>
        
        <div className="space-y-3">
          <div>
            <div className="flex justify-between text-xs mb-1">
              <span className="text-gray-700">Doubling Down Signal</span>
              <span className="text-gray-900 font-medium">40%</span>
            </div>
            <input
              type="range"
              min="0"
              max="100"
              defaultValue={40}
              className="w-full h-2 bg-blue-200 rounded-lg appearance-none cursor-pointer"
            />
          </div>

          <div>
            <div className="flex justify-between text-xs mb-1">
              <span className="text-gray-700">Insider Buying Signal</span>
              <span className="text-gray-900 font-medium">30%</span>
            </div>
            <input
              type="range"
              min="0"
              max="100"
              defaultValue={30}
              className="w-full h-2 bg-green-200 rounded-lg appearance-none cursor-pointer"
            />
          </div>

          <div>
            <div className="flex justify-between text-xs mb-1">
              <span className="text-gray-700">Institutional Herding Signal</span>
              <span className="text-gray-900 font-medium">20%</span>
            </div>
            <input
              type="range"
              min="0"
              max="100"
              defaultValue={20}
              className="w-full h-2 bg-purple-200 rounded-lg appearance-none cursor-pointer"
            />
          </div>

          <div>
            <div className="flex justify-between text-xs mb-1">
              <span className="text-gray-700">Technical Confirmation</span>
              <span className="text-gray-900 font-medium">10%</span>
            </div>
            <input
              type="range"
              min="0"
              max="100"
              defaultValue={10}
              className="w-full h-2 bg-amber-200 rounded-lg appearance-none cursor-pointer"
            />
          </div>
        </div>
      </div>

      {/* Universe Filters */}
      <div className="bg-white p-5 rounded-lg border border-gray-200">
        <h3 className="text-sm font-semibold text-gray-900 mb-4">Universe Filtration</h3>
        
        <div className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-2">
              Minimum Market Cap ($B)
            </label>
            <input
              type="number"
              min="0.1"
              max="50"
              step="0.5"
              defaultValue={3}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
            />
            <p className="mt-1 text-xs text-gray-500">
              Only consider stocks with market cap above this (default: $3B, per SRS)
            </p>
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-700 mb-2">
              Index Filter
            </label>
            <select
              defaultValue="sp1500"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="none">No Filter (All Stocks)</option>
              <option value="sp500">S&P 500 Only</option>
              <option value="sp1500">S&P 1500 (per SRS)</option>
              <option value="nasdaq100">NASDAQ 100</option>
              <option value="russell1000">Russell 1000</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-700 mb-2">
              Minimum Daily Volume
            </label>
            <input
              type="number"
              min="100000"
              max="10000000"
              step="100000"
              defaultValue={1000000}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
            />
            <p className="mt-1 text-xs text-gray-500">
              Minimum average daily trading volume (default: 1M shares)
            </p>
          </div>
        </div>
      </div>

      {/* Info Box */}
      <div className="bg-blue-50 p-4 rounded-lg border border-blue-200">
        <div className="flex items-start">
          <svg className="h-5 w-5 text-blue-400 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <div className="ml-3">
            <h4 className="text-sm font-medium text-blue-900">Default Settings Recommended</h4>
            <p className="mt-1 text-xs text-blue-700">
              These parameters are pre-configured based on institutional best practices and SRS specifications.
              Modify only if you have specific requirements or are conducting parameter sensitivity analysis.
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
          Continue to Review →
        </button>
      </div>

      {/* Help Panel */}
      <HelpPanel
        isOpen={isHelpOpen}
        onClose={() => setIsHelpOpen(false)}
        content={stepHelpContent[7]}
      />
    </div>
  );
};

export default Step7_Parameters;
