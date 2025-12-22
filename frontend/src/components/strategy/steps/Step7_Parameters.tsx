import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
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
  const { t } = useTranslation(['strategy', 'common']);
  const [isHelpOpen, setIsHelpOpen] = useState(false);
  
  const transactionCosts = config.transaction_costs || {
    commission_per_trade: 0.0,
    commission_pct: 0.001,
    slippage_pct: 0.001,
    min_commission: 1.0,
  };

  // Conviction weights with defaults
  const convictionWeights = config.conviction_weights || {
    doubling_down: 40,
    insider_buying: 30,
    institutional_herding: 20,
    technical_confirmation: 10,
  };

  // Technical parameters with defaults
  const technicalParams = config.technical_params || {
    sma_short: 50,
    sma_long: 200,
    rsi_period: 14,
    breakout_days: 20,
  };

  // Universe filtration with defaults
  const universeFiltration = config.universe_filtration || {
    min_market_cap_b: 3,
    index_filter: 'sp1500',
    min_daily_volume: 1000000,
  };

  const updateTransactionCosts = (updates: any) => {
    updateConfig({
      transaction_costs: {
        ...transactionCosts,
        ...updates,
      },
    });
  };

  const updateConvictionWeights = (updates: Partial<typeof convictionWeights>) => {
    updateConfig({
      conviction_weights: {
        ...convictionWeights,
        ...updates,
      },
    });
  };

  const updateTechnicalParams = (updates: Partial<typeof technicalParams>) => {
    updateConfig({
      technical_params: {
        ...technicalParams,
        ...updates,
      },
    });
  };

  const updateUniverseFiltration = (updates: Partial<typeof universeFiltration>) => {
    updateConfig({
      universe_filtration: {
        ...universeFiltration,
        ...updates,
      },
    });
  };

  return (
    <div className="space-y-6">
      {/* Header with Help Button */}
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">{t('steps.step7.title')}</h2>
          <p className="mt-1 text-sm text-gray-600">
            {t('steps.step7.description')}
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
                  value={technicalParams.sma_short}
                  onChange={(e) => updateTechnicalParams({ sma_short: parseInt(e.target.value) || 50 })}
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
                  value={technicalParams.sma_long}
                  onChange={(e) => updateTechnicalParams({ sma_long: parseInt(e.target.value) || 200 })}
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
              value={technicalParams.rsi_period}
              onChange={(e) => updateTechnicalParams({ rsi_period: parseInt(e.target.value) || 14 })}
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
              value={technicalParams.breakout_days}
              onChange={(e) => updateTechnicalParams({ breakout_days: parseInt(e.target.value) || 20 })}
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
        
        {/* Total weight indicator */}
        <div className="mb-4 p-2 rounded-lg bg-gray-50">
          <div className="flex justify-between text-xs">
            <span className="text-gray-600">Total Weight:</span>
            <span className={`font-bold ${
              convictionWeights.doubling_down + convictionWeights.insider_buying + 
              convictionWeights.institutional_herding + convictionWeights.technical_confirmation === 100
                ? 'text-green-600' : 'text-orange-600'
            }`}>
              {convictionWeights.doubling_down + convictionWeights.insider_buying + 
               convictionWeights.institutional_herding + convictionWeights.technical_confirmation}%
              {(convictionWeights.doubling_down + convictionWeights.insider_buying + 
                convictionWeights.institutional_herding + convictionWeights.technical_confirmation !== 100) && 
                ' (should equal 100%)'}
            </span>
          </div>
        </div>
        
        <div className="space-y-4">
          <div>
            <div className="flex justify-between text-xs mb-1">
              <span className="text-gray-700">Doubling Down Signal</span>
              <span className="text-gray-900 font-bold">{convictionWeights.doubling_down}%</span>
            </div>
            <input
              type="range"
              min="0"
              max="100"
              step="5"
              value={convictionWeights.doubling_down}
              onChange={(e) => updateConvictionWeights({ doubling_down: parseInt(e.target.value) })}
              className="w-full h-2 bg-blue-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
            />
          </div>

          <div>
            <div className="flex justify-between text-xs mb-1">
              <span className="text-gray-700">Insider Buying Signal</span>
              <span className="text-gray-900 font-bold">{convictionWeights.insider_buying}%</span>
            </div>
            <input
              type="range"
              min="0"
              max="100"
              step="5"
              value={convictionWeights.insider_buying}
              onChange={(e) => updateConvictionWeights({ insider_buying: parseInt(e.target.value) })}
              className="w-full h-2 bg-green-200 rounded-lg appearance-none cursor-pointer accent-green-600"
            />
          </div>

          <div>
            <div className="flex justify-between text-xs mb-1">
              <span className="text-gray-700">Institutional Herding Signal</span>
              <span className="text-gray-900 font-bold">{convictionWeights.institutional_herding}%</span>
            </div>
            <input
              type="range"
              min="0"
              max="100"
              step="5"
              value={convictionWeights.institutional_herding}
              onChange={(e) => updateConvictionWeights({ institutional_herding: parseInt(e.target.value) })}
              className="w-full h-2 bg-purple-200 rounded-lg appearance-none cursor-pointer accent-purple-600"
            />
          </div>

          <div>
            <div className="flex justify-between text-xs mb-1">
              <span className="text-gray-700">Technical Confirmation</span>
              <span className="text-gray-900 font-bold">{convictionWeights.technical_confirmation}%</span>
            </div>
            <input
              type="range"
              min="0"
              max="100"
              step="5"
              value={convictionWeights.technical_confirmation}
              onChange={(e) => updateConvictionWeights({ technical_confirmation: parseInt(e.target.value) })}
              className="w-full h-2 bg-amber-200 rounded-lg appearance-none cursor-pointer accent-amber-600"
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
              value={universeFiltration.min_market_cap_b}
              onChange={(e) => updateUniverseFiltration({ min_market_cap_b: parseFloat(e.target.value) || 3 })}
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
              value={universeFiltration.index_filter}
              onChange={(e) => updateUniverseFiltration({ index_filter: e.target.value })}
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
              value={universeFiltration.min_daily_volume}
              onChange={(e) => updateUniverseFiltration({ min_daily_volume: parseInt(e.target.value) || 1000000 })}
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
