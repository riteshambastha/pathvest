import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { StrategyConfig } from '../StrategyWizard';
import HelpPanel from '../../common/HelpPanel';
import { stepHelpContent } from '../helpContent';

interface StepProps {
  config: StrategyConfig;
  updateConfig: (updates: Partial<StrategyConfig>) => void;
  nextStep: () => void;
  prevStep: () => void;
}

const Step8_ReviewBacktest: React.FC<StepProps> = ({ config, prevStep }) => {
  const navigate = useNavigate();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isHelpOpen, setIsHelpOpen] = useState(false);
  const [showSuccessModal, setShowSuccessModal] = useState(false);
  const [backtestId, setBacktestId] = useState<string | null>(null);

  const handleRunBacktest = async () => {
    setIsSubmitting(true);
    setError(null);

    try {
      // Log the config being sent for debugging
      console.log('🚀 Submitting backtest with config:', JSON.stringify(config, null, 2));
      console.log('📊 Selected institutions:', config.sub_universe_filters?.selected_institutions || []);
      
      const response = await fetch(`${import.meta.env.VITE_API_BASE_URL}/api/v1/backtest/run`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ strategy_config: config }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to submit backtest');
      }

      const data = await response.json();
      const newBacktestId = data.backtest_id;
      
      console.log('✅ Backtest submitted successfully. ID:', newBacktestId);
      
      setBacktestId(newBacktestId);
      setIsSubmitting(false);
      setShowSuccessModal(true);
    } catch (err: any) {
      console.error('❌ Error submitting backtest:', err);
      setError(err.message || 'Failed to start backtest');
      setIsSubmitting(false);
    }
  };

  const handleViewResults = () => {
    if (backtestId) {
      navigate(`/results/${backtestId}`);
    }
  };

  const handleBackToStrategies = () => {
    navigate('/my-strategies');
  };

  return (
    <div className="space-y-6">
      {/* Header with Help Button */}
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Review & Run Backtest</h2>
          <p className="mt-1 text-sm text-gray-600">
            Review your strategy configuration and start the backtest
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

      {/* Strategy Overview */}
      <div className="bg-gradient-to-r from-blue-50 to-indigo-50 p-6 rounded-lg border border-blue-200">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Strategy Overview</h3>
        
        <div className="grid grid-cols-2 gap-4">
          <div>
            <span className="text-xs text-gray-600">Strategy Name</span>
            <p className="text-sm font-medium text-gray-900">{config.name || 'Unnamed Strategy'}</p>
          </div>
          
          <div>
            <span className="text-xs text-gray-600">Backtesting Engine</span>
            <p className="text-sm font-medium text-gray-900">
              {config.engine_type === 'lean' ? '⚡ LEAN Engine (Pro)' : 
               config.engine_type === 'backtrader' ? '📊 Backtrader Engine (New)' : 
               '🚀 Custom Engine (Fast)'}
            </p>
          </div>
          
          <div>
            <span className="text-xs text-gray-600">Backtest Period</span>
            <p className="text-sm font-medium text-gray-900">
              {config.backtest_period?.start_date} to {config.backtest_period?.end_date}
            </p>
          </div>
          
          <div>
            <span className="text-xs text-gray-600">Initial Capital</span>
            <p className="text-sm font-medium text-gray-900">
              ${(config.initial_capital || 100000).toLocaleString()}
            </p>
          </div>
        </div>
      </div>

      {/* Stock Selection Summary */}
      <div className="bg-white p-5 rounded-lg border border-gray-200">
        <h3 className="text-sm font-semibold text-gray-900 mb-3">Stock Selection</h3>
        
        {config.selected_institutions && config.selected_institutions.length > 0 ? (
          <div>
            <p className="text-xs text-gray-600 mb-2">Following {config.selected_institutions.length} institutions:</p>
            <div className="flex flex-wrap gap-2">
              {config.selected_institutions.map((cik) => (
                <span
                  key={cik}
                  className="px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded"
                >
                  CIK: {cik}
                </span>
              ))}
            </div>
          </div>
        ) : (
          <p className="text-xs text-gray-600">Using diverse stock selection from BigQuery</p>
        )}
      </div>

      {/* Position Sizing Summary */}
      <div className="bg-white p-5 rounded-lg border border-gray-200">
        <h3 className="text-sm font-semibold text-gray-900 mb-3">Position Sizing & Risk</h3>
        
        <div className="grid grid-cols-2 gap-4 text-xs">
          <div>
            <span className="text-gray-600">Method:</span>
            <span className="ml-2 font-medium text-gray-900">
              {config.position_sizing?.method === 'equal_weight' && 'Equal Weight'}
              {config.position_sizing?.method === 'fixed_size' && 'Fixed Size (5%)'}
              {config.position_sizing?.method === 'conviction_weighted' && 'Conviction Weighted'}
            </span>
          </div>
          
          <div>
            <span className="text-gray-600">Max Positions:</span>
            <span className="ml-2 font-medium text-gray-900">
              {config.position_sizing?.max_positions || 20}
            </span>
          </div>
          
          <div>
            <span className="text-gray-600">Position Size Range:</span>
            <span className="ml-2 font-medium text-gray-900">
              {((config.position_sizing?.min_position_size || 0.03) * 100).toFixed(0)}% - {((config.position_sizing?.max_position_size || 0.05) * 100).toFixed(0)}%
            </span>
          </div>
          
          <div>
            <span className="text-gray-600">Max Portfolio Drawdown:</span>
            <span className="ml-2 font-medium text-gray-900">
              {((config.risk_management?.max_portfolio_drawdown || 0.20) * 100).toFixed(0)}%
            </span>
          </div>
        </div>
      </div>

      {/* Entry & Exit Summary */}
      <div className="bg-white p-5 rounded-lg border border-gray-200">
        <h3 className="text-sm font-semibold text-gray-900 mb-3">Entry & Exit Rules</h3>
        
        <div className="space-y-3">
          <div>
            <span className="text-xs text-gray-600">Entry Timing:</span>
            <span className="ml-2 text-xs font-medium text-gray-900">
              {config.entry_rules?.timing === 'immediate' && 'Immediate (T+1)'}
              {config.entry_rules?.timing === 'end_of_day' && 'End of Day'}
              {config.entry_rules?.timing === 'delayed' && 'Delayed Entry'}
              {' '}
              {config.entry_rules?.technical_confirmation && '(with Technical Confirmation)'}
            </span>
          </div>
          
          <div>
            <span className="text-xs text-gray-600 block mb-1">Active Exit Modules:</span>
            <div className="flex flex-wrap gap-2">
              {config.exit_rules?.thesis_drift_enabled && (
                <span className="px-2 py-1 bg-green-100 text-green-800 text-xs rounded">
                  ✓ Thesis Drift
                </span>
              )}
              {config.exit_rules?.insider_reversal_enabled && (
                <span className="px-2 py-1 bg-green-100 text-green-800 text-xs rounded">
                  ✓ Insider Reversal
                </span>
              )}
              {config.exit_rules?.trailing_stop_enabled && (
                <span className="px-2 py-1 bg-green-100 text-green-800 text-xs rounded">
                  ✓ Trailing Stop ({((config.exit_rules.trailing_stop_pct ?? 0.15) * 100).toFixed(0)}%)
                </span>
              )}
              {config.exit_rules?.dead_money_enabled && (
                <span className="px-2 py-1 bg-green-100 text-green-800 text-xs rounded">
                  ✓ Dead Money ({config.exit_rules.dead_money_quarters}Q)
                </span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Transaction Costs */}
      <div className="bg-white p-5 rounded-lg border border-gray-200">
        <h3 className="text-sm font-semibold text-gray-900 mb-3">Transaction Costs</h3>
        
        <div className="grid grid-cols-3 gap-4 text-xs">
          <div>
            <span className="text-gray-600">Commission:</span>
            <span className="ml-2 font-medium text-gray-900">
              {config.transaction_costs?.commission_pct 
                ? `${(config.transaction_costs.commission_pct * 100).toFixed(2)}%`
                : `$${config.transaction_costs?.commission_per_trade || 0}`}
            </span>
          </div>
          
          <div>
            <span className="text-gray-600">Slippage:</span>
            <span className="ml-2 font-medium text-gray-900">
              {((config.transaction_costs?.slippage_pct || 0.001) * 100).toFixed(2)}%
            </span>
          </div>
          
          <div>
            <span className="text-gray-600">Rebalancing:</span>
            <span className="ml-2 font-medium text-gray-900">
              {config.risk_management?.rebalancing_frequency || 'Monthly'}
            </span>
          </div>
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="bg-red-50 p-4 rounded-lg border border-red-200">
          <div className="flex items-start">
            <svg className="h-5 w-5 text-red-400 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <div className="ml-3">
              <h4 className="text-sm font-medium text-red-900">Error</h4>
              <p className="mt-1 text-xs text-red-700">{error}</p>
            </div>
          </div>
        </div>
      )}

      {/* Important Notes */}
      <div className="bg-amber-50 p-4 rounded-lg border border-amber-200">
        <div className="flex items-start">
          <svg className="h-5 w-5 text-amber-400 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          <div className="ml-3">
            <h4 className="text-sm font-medium text-amber-900">Before Running</h4>
            <ul className="mt-1 text-xs text-amber-800 space-y-1">
              <li>• Backtest execution takes 2-3 minutes (fetching real market data)</li>
              <li>• Real SEC 13F filings and AlphaVantage prices will be used</li>
              <li>• Strategy will be automatically saved for future reference</li>
              <li>• You can view results and download reports after completion</li>
            </ul>
          </div>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="bg-gradient-to-r from-blue-600 to-indigo-600 p-6 rounded-lg">
        <h3 className="text-lg font-semibold text-white mb-2">Ready to Backtest?</h3>
        <p className="text-sm text-blue-100 mb-4">
          Click below to run your strategy against {' '}
          {config.backtest_period 
            ? `${Math.round((new Date(config.backtest_period.end_date).getTime() - new Date(config.backtest_period.start_date).getTime()) / (1000 * 60 * 60 * 24 * 365))} years`
            : 'historical'} data.
        </p>
        
        <div className="flex gap-3">
          <button
            onClick={prevStep}
            disabled={isSubmitting}
            className="px-6 py-3 bg-white text-blue-600 rounded-md hover:bg-blue-50 transition disabled:opacity-50 disabled:cursor-not-allowed"
          >
            ← Back to Edit
          </button>
          
          <button
            onClick={handleRunBacktest}
            disabled={isSubmitting}
            className="flex-1 px-6 py-3 bg-white text-blue-600 rounded-md hover:bg-blue-50 transition font-semibold disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
          >
            {isSubmitting ? (
              <>
                <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-blue-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Submitting...
              </>
            ) : (
              <>
                🚀 Run Backtest
              </>
            )}
          </button>
        </div>
      </div>

      {/* Debug Info (Optional - can be removed) */}
      <details className="bg-gray-50 p-4 rounded-lg border border-gray-200">
        <summary className="text-xs font-medium text-gray-700 cursor-pointer">
          View Full Configuration (Advanced)
        </summary>
        <pre className="mt-2 text-xs text-gray-600 overflow-auto max-h-60">
          {JSON.stringify(config, null, 2)}
        </pre>
      </details>

      {/* Help Panel */}
      <HelpPanel
        isOpen={isHelpOpen}
        onClose={() => setIsHelpOpen(false)}
        content={stepHelpContent[8]}
      />

      {/* Success Modal */}
      {showSuccessModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-2xl max-w-2xl w-full transform transition-all animate-fadeIn">
            {/* Header */}
            <div className="bg-gradient-to-r from-green-500 to-emerald-600 p-6 rounded-t-xl">
              <div className="flex items-center justify-center mb-4">
                <div className="bg-white rounded-full p-3">
                  <svg className="h-12 w-12 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
              </div>
              <h2 className="text-2xl font-bold text-white text-center">
                Backtest Submitted Successfully! 🎉
              </h2>
              <p className="text-green-50 text-center mt-2">
                Your strategy is now being processed in the background
              </p>
            </div>

            {/* Content */}
            <div className="p-6 space-y-4">
              {/* Status Info */}
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <div className="flex items-start">
                  <svg className="h-5 w-5 text-blue-500 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <div className="ml-3">
                    <h3 className="text-sm font-semibold text-blue-900">What's Happening Now?</h3>
                    <ul className="mt-2 text-sm text-blue-800 space-y-1">
                      <li>• Fetching real SEC 13F filings from EDGAR</li>
                      <li>• Downloading historical market data from AlphaVantage</li>
                      <li>• Running {config.engine_type === 'lean' ? 'LEAN' : config.engine_type === 'backtrader' ? 'Backtrader' : 'Custom'} backtest engine</li>
                      <li>• Calculating performance metrics and risk analytics</li>
                    </ul>
                  </div>
                </div>
              </div>

              {/* Timeline */}
              <div className="bg-gray-50 rounded-lg p-4">
                <h3 className="text-sm font-semibold text-gray-900 mb-3 flex items-center">
                  <svg className="h-5 w-5 mr-2 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  Expected Timeline
                </h3>
                <div className="space-y-2 text-sm">
                  <div className="flex items-center text-gray-700">
                    <span className="w-24 text-gray-600">0-30 sec:</span>
                    <span>Data fetching & validation</span>
                  </div>
                  <div className="flex items-center text-gray-700">
                    <span className="w-24 text-gray-600">30-90 sec:</span>
                    <span>Running backtest simulation</span>
                  </div>
                  <div className="flex items-center text-gray-700">
                    <span className="w-24 text-gray-600">90-120 sec:</span>
                    <span>Calculating metrics & generating report</span>
                  </div>
                </div>
                <div className="mt-3 pt-3 border-t border-gray-200">
                  <p className="text-xs text-gray-600 flex items-center">
                    <svg className="h-4 w-4 mr-1 text-amber-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    Total processing time: ~2-3 minutes
                  </p>
                </div>
              </div>

              {/* Strategy Info */}
              <div className="bg-gradient-to-r from-purple-50 to-pink-50 border border-purple-200 rounded-lg p-4">
                <h3 className="text-sm font-semibold text-gray-900 mb-2">Your Strategy Details</h3>
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div>
                    <span className="text-gray-600">Name:</span>
                    <span className="ml-2 font-medium text-gray-900">{config.name || 'Unnamed Strategy'}</span>
                  </div>
                  <div>
                    <span className="text-gray-600">Backtest ID:</span>
                    <span className="ml-2 font-mono text-xs font-medium text-purple-700">{backtestId?.substring(0, 8)}...</span>
                  </div>
                  <div>
                    <span className="text-gray-600">Period:</span>
                    <span className="ml-2 font-medium text-gray-900">
                      {config.backtest_period?.start_date} to {config.backtest_period?.end_date}
                    </span>
                  </div>
                  <div>
                    <span className="text-gray-600">Capital:</span>
                    <span className="ml-2 font-medium text-gray-900">
                      ${(config.initial_capital || 100000).toLocaleString()}
                    </span>
                  </div>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex gap-3 pt-2">
                <button
                  onClick={handleBackToStrategies}
                  className="flex-1 px-6 py-3 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition font-medium"
                >
                  View All Strategies
                </button>
                <button
                  onClick={handleViewResults}
                  className="flex-1 px-6 py-3 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-lg hover:from-blue-700 hover:to-indigo-700 transition font-semibold shadow-lg flex items-center justify-center group"
                >
                  <span>View Live Results</span>
                  <svg className="ml-2 h-5 w-5 group-hover:translate-x-1 transition-transform" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                  </svg>
                </button>
              </div>

              {/* Footer Note */}
              <div className="text-center pt-3 border-t border-gray-200">
                <p className="text-xs text-gray-500">
                  💡 Tip: Results will auto-refresh as your backtest completes. You can close this and come back anytime.
                </p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Step8_ReviewBacktest;

