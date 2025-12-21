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

const Step6_RiskManagement: React.FC<StepProps> = ({ config, updateConfig, nextStep, prevStep }) => {
  const [isHelpOpen, setIsHelpOpen] = useState(false);
  const riskManagement = config.risk_management || {
    max_portfolio_drawdown: 0.20,
    max_position_loss: 0.15,
    correlation_limit: 0.70,
    sector_concentration_limit: 0.30,
    enable_dynamic_sizing: false,
    volatility_scaling: false,
    rebalancing_frequency: 'monthly',
    cash_reserve_pct: 0.05,
  };

  const updateRiskManagement = (updates: any) => {
    updateConfig({
      risk_management: {
        ...riskManagement,
        ...updates,
      },
    });
  };

  return (
    <div className="space-y-6">
      {/* Header with Help Button */}
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Risk Management</h2>
          <p className="mt-1 text-sm text-gray-600">
            Configure portfolio-level risk controls and diversification rules
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

      {/* Portfolio Drawdown Limit */}
      <div className="bg-white p-5 rounded-lg border border-gray-200">
        <h3 className="text-sm font-semibold text-gray-900 mb-4">Portfolio Risk Limits</h3>
        
        <div className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-2">
              Maximum Portfolio Drawdown
            </label>
            <div className="relative">
              <input
                type="number"
                min="5"
                max="50"
                step="1"
                value={(riskManagement.max_portfolio_drawdown ?? 0.2) * 100}
                onChange={(e) =>
                  updateRiskManagement({ max_portfolio_drawdown: parseFloat(e.target.value) / 100 })
                }
                className="w-full px-3 py-2 pr-8 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
              />
              <span className="absolute right-3 top-2 text-gray-500 text-sm">%</span>
            </div>
            <p className="mt-1 text-xs text-gray-500">
              Stop trading if portfolio drops more than this from peak (default: 20%)
            </p>
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-700 mb-2">
              Maximum Single Position Loss
            </label>
            <div className="relative">
              <input
                type="number"
                min="5"
                max="30"
                step="1"
                value={(riskManagement.max_position_loss ?? 0.15) * 100}
                onChange={(e) =>
                  updateRiskManagement({ max_position_loss: parseFloat(e.target.value) / 100 })
                }
                className="w-full px-3 py-2 pr-8 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
              />
              <span className="absolute right-3 top-2 text-gray-500 text-sm">%</span>
            </div>
            <p className="mt-1 text-xs text-gray-500">
              Force exit if any position loses more than this (default: 15%)
            </p>
          </div>
        </div>
      </div>

      {/* Diversification Controls */}
      <div className="bg-white p-5 rounded-lg border border-gray-200">
        <h3 className="text-sm font-semibold text-gray-900 mb-4">Diversification Controls</h3>
        
        <div className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-2">
              Maximum Stock Correlation
            </label>
            <div className="relative">
              <input
                type="number"
                min="0.3"
                max="1.0"
                step="0.05"
                value={riskManagement.correlation_limit}
                onChange={(e) =>
                  updateRiskManagement({ correlation_limit: parseFloat(e.target.value) })
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
            <p className="mt-1 text-xs text-gray-500">
              Limit highly correlated positions (0.70 = 70% correlation, default: 70%)
            </p>
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-700 mb-2">
              Sector Concentration Limit
            </label>
            <div className="relative">
              <input
                type="number"
                min="10"
                max="100"
                step="5"
                value={(riskManagement.sector_concentration_limit ?? 0.3) * 100}
                onChange={(e) =>
                  updateRiskManagement({ sector_concentration_limit: parseFloat(e.target.value) / 100 })
                }
                className="w-full px-3 py-2 pr-8 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
              />
              <span className="absolute right-3 top-2 text-gray-500 text-sm">%</span>
            </div>
            <p className="mt-1 text-xs text-gray-500">
              Maximum allocation to single sector (default: 30%)
            </p>
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-700 mb-2">
              Cash Reserve
            </label>
            <div className="relative">
              <input
                type="number"
                min="0"
                max="20"
                step="1"
                value={(riskManagement.cash_reserve_pct ?? 0.05) * 100}
                onChange={(e) =>
                  updateRiskManagement({ cash_reserve_pct: parseFloat(e.target.value) / 100 })
                }
                className="w-full px-3 py-2 pr-8 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
              />
              <span className="absolute right-3 top-2 text-gray-500 text-sm">%</span>
            </div>
            <p className="mt-1 text-xs text-gray-500">
              Minimum cash to keep for opportunities (default: 5%)
            </p>
          </div>
        </div>
      </div>

      {/* Advanced Position Sizing */}
      <div className="bg-white p-5 rounded-lg border border-gray-200">
        <h3 className="text-sm font-semibold text-gray-900 mb-4">Advanced Position Sizing</h3>
        
        <div className="space-y-3">
          <label className="flex items-center cursor-pointer">
            <input
              type="checkbox"
              checked={riskManagement.enable_dynamic_sizing}
              onChange={(e) => updateRiskManagement({ enable_dynamic_sizing: e.target.checked })}
              className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
            />
            <div className="ml-3">
              <span className="text-sm font-medium text-gray-700">Enable Dynamic Position Sizing</span>
              <p className="text-xs text-gray-500">Adjust position sizes based on conviction score</p>
            </div>
          </label>

          <label className="flex items-center cursor-pointer">
            <input
              type="checkbox"
              checked={riskManagement.volatility_scaling}
              onChange={(e) => updateRiskManagement({ volatility_scaling: e.target.checked })}
              className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
            />
            <div className="ml-3">
              <span className="text-sm font-medium text-gray-700">Volatility-Based Scaling</span>
              <p className="text-xs text-gray-500">Reduce size for high-volatility stocks</p>
            </div>
          </label>
        </div>
      </div>

      {/* Rebalancing */}
      <div className="bg-white p-5 rounded-lg border border-gray-200">
        <h3 className="text-sm font-semibold text-gray-900 mb-4">Rebalancing Frequency</h3>
        
        <select
          value={riskManagement.rebalancing_frequency}
          onChange={(e) => updateRiskManagement({ rebalancing_frequency: e.target.value })}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
        >
          <option value="never">Never (Buy and Hold)</option>
          <option value="weekly">Weekly</option>
          <option value="monthly">Monthly (Recommended)</option>
          <option value="quarterly">Quarterly</option>
          <option value="threshold">Threshold-Based (when drift &gt; 5%)</option>
        </select>
        <p className="mt-2 text-xs text-gray-600">
          How often to rebalance portfolio back to target allocations
        </p>
      </div>

      {/* Rank Buffer (SRS Specification) */}
      <div className="bg-gradient-to-r from-purple-50 to-indigo-50 p-5 rounded-lg border border-purple-200">
        <h3 className="text-sm font-semibold text-purple-900 mb-3">
          🎯 Rank Buffer (Churn Prevention)
        </h3>
        <div className="space-y-2 text-xs text-purple-800">
          <div className="flex items-start">
            <svg className="h-4 w-4 text-purple-600 mr-2 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span>
              <strong>Buffer Size (B=5)</strong>: Current holdings keep their spots unless new candidates rank 5+ places higher
            </span>
          </div>
          <div className="flex items-start">
            <svg className="h-4 w-4 text-purple-600 mr-2 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span>
              <strong>Prevents Churn</strong>: Reduces excessive turnover from minor ranking changes
            </span>
          </div>
          <div className="flex items-start">
            <svg className="h-4 w-4 text-purple-600 mr-2 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span>
              <strong>Tax Efficient</strong>: Minimizes short-term capital gains
            </span>
          </div>
        </div>
      </div>

      {/* Warning if no limits */}
      {(riskManagement.max_portfolio_drawdown ?? 0.2) >= 0.5 && (
        <div className="bg-red-50 p-4 rounded-lg border border-red-200">
          <div className="flex items-start">
            <svg className="h-5 w-5 text-red-400 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            <div className="ml-3">
              <h4 className="text-sm font-medium text-red-900">High Risk Configuration</h4>
              <p className="mt-1 text-xs text-red-700">
                Maximum drawdown of {(riskManagement.max_portfolio_drawdown ?? 0.2) * 100}% is very high. Consider reducing to 20-25% for most strategies.
              </p>
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
              20% max drawdown, 15% max position loss, monthly rebalancing, 5% cash reserve.
              These settings balance risk control with strategy flexibility.
            </p>
          </div>
        </div>
      </div>

      {/* Help Panel */}
      <HelpPanel
        isOpen={isHelpOpen}
        onClose={() => setIsHelpOpen(false)}
        content={stepHelpContent[6]}
      />
    </div>
  );
};

export default Step6_RiskManagement;
