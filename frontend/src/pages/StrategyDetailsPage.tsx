import React, { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';

interface StrategyDetails {
  id: number;
  name: string;
  description: string | null;
  strategy_config: any;
  selected_institutions: string[];
  status: string;
  created_at: string;
  updated_at: string;
  backtests: Array<{
    backtest_id: string;
    status: string;
    total_return: number | null;
    sharpe_ratio: number | null;
    max_drawdown: number | null;
    created_at: string;
    completed_at: string | null;
  }>;
}

const StrategyDetailsPage: React.FC = () => {
  const { strategyId } = useParams<{ strategyId: string }>();
  const navigate = useNavigate();
  const [strategy, setStrategy] = useState<StrategyDetails | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadStrategy();
  }, [strategyId]);

  const loadStrategy = async () => {
    try {
      setLoading(true);
      const response = await fetch(`/api/v1/strategies/${strategyId}`);
      if (!response.ok) {
        throw new Error('Strategy not found');
      }
      const data = await response.json();
      setStrategy(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load strategy');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleReloadStrategy = async () => {
    if (!strategy) return;
    
    try {
      // Store strategy config in localStorage for the wizard to pick up
      localStorage.setItem('reloadStrategy', JSON.stringify({
        ...strategy.strategy_config,
        sub_universe_filters: {
          ...strategy.strategy_config.sub_universe_filters,
          selected_institutions: strategy.selected_institutions
        }
      }));
      
      // Navigate to builder
      navigate('/builder');
    } catch (err) {
      console.error('Failed to reload strategy:', err);
      alert('Failed to reload strategy');
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading strategy...</p>
        </div>
      </div>
    );
  }

  if (error || !strategy) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-600">{error || 'Strategy not found'}</p>
          <Link
            to="/my-strategies"
            className="mt-4 inline-block px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            Back to My Strategies
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center justify-between">
            <div className="flex-1">
              <div className="flex items-center gap-3">
                <Link to="/my-strategies" className="text-gray-400 hover:text-gray-600">
                  ← Back
                </Link>
                <h1 className="text-3xl font-bold text-gray-900">{strategy.name}</h1>
                <span
                  className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${
                    strategy.status === 'active'
                      ? 'bg-green-100 text-green-800'
                      : 'bg-gray-100 text-gray-800'
                  }`}
                >
                  {strategy.status}
                </span>
              </div>
              {strategy.description && (
                <p className="mt-2 text-sm text-gray-600">{strategy.description}</p>
              )}
              <p className="mt-1 text-xs text-gray-500">
                Created {new Date(strategy.created_at).toLocaleString()}
              </p>
            </div>
            <button
              onClick={handleReloadStrategy}
              className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition font-medium"
            >
              🔄 Reload & Edit
            </button>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column: Configuration */}
          <div className="lg:col-span-2 space-y-6">
            {/* Institutions */}
            {strategy.selected_institutions.length > 0 && (
              <div className="bg-white rounded-lg shadow p-6">
                <h2 className="text-lg font-semibold text-gray-900 mb-4">
                  Selected Institutions ({strategy.selected_institutions.length})
                </h2>
                <div className="flex flex-wrap gap-2">
                  {strategy.selected_institutions.map((inst, idx) => (
                    <span
                      key={idx}
                      className="inline-flex items-center px-3 py-1.5 rounded-md text-sm font-medium bg-purple-100 text-purple-800"
                    >
                      🏦 {inst}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Strategy Configuration */}
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Strategy Configuration</h2>
              <div className="space-y-3">
                {strategy.strategy_config.backtest_period && (
                  <div>
                    <span className="text-sm font-medium text-gray-700">Backtest Period:</span>
                    <span className="ml-2 text-sm text-gray-600">
                      {strategy.strategy_config.backtest_period.start_date} to{' '}
                      {strategy.strategy_config.backtest_period.end_date}
                    </span>
                  </div>
                )}
                {strategy.strategy_config.initial_capital && (
                  <div>
                    <span className="text-sm font-medium text-gray-700">Initial Capital:</span>
                    <span className="ml-2 text-sm text-gray-600">
                      ${strategy.strategy_config.initial_capital.toLocaleString()}
                    </span>
                  </div>
                )}
                {strategy.strategy_config.benchmark && (
                  <div>
                    <span className="text-sm font-medium text-gray-700">Benchmark:</span>
                    <span className="ml-2 text-sm text-gray-600">
                      {strategy.strategy_config.benchmark}
                    </span>
                  </div>
                )}
              </div>

              {/* Full Config (Collapsed) */}
              <details className="mt-4">
                <summary className="cursor-pointer text-sm font-medium text-blue-600 hover:text-blue-700">
                  View Full Configuration JSON
                </summary>
                <pre className="mt-2 p-3 bg-gray-50 rounded text-xs overflow-auto max-h-96">
                  {JSON.stringify(strategy.strategy_config, null, 2)}
                </pre>
              </details>
            </div>

            {/* Backtests History */}
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">
                Backtest History ({strategy.backtests.length})
              </h2>
              {strategy.backtests.length === 0 ? (
                <p className="text-sm text-gray-500">No backtests yet</p>
              ) : (
                <div className="space-y-3">
                  {strategy.backtests.map((backtest) => (
                    <div
                      key={backtest.backtest_id}
                      className="border border-gray-200 rounded-lg p-4 hover:bg-gray-50"
                    >
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-mono text-sm text-gray-600">
                          {backtest.backtest_id}
                        </span>
                        <span
                          className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                            backtest.status === 'completed'
                              ? 'bg-green-100 text-green-800'
                              : backtest.status === 'running'
                              ? 'bg-yellow-100 text-yellow-800'
                              : 'bg-red-100 text-red-800'
                          }`}
                        >
                          {backtest.status}
                        </span>
                      </div>
                      {backtest.status === 'completed' && (
                        <div className="grid grid-cols-3 gap-4 mb-3">
                          <div>
                            <div className="text-xs text-gray-500">Return</div>
                            <div className="text-sm font-semibold text-green-600">
                              {backtest.total_return
                                ? `${(backtest.total_return * 100).toFixed(1)}%`
                                : 'N/A'}
                            </div>
                          </div>
                          <div>
                            <div className="text-xs text-gray-500">Sharpe</div>
                            <div className="text-sm font-semibold text-blue-600">
                              {backtest.sharpe_ratio?.toFixed(2) || 'N/A'}
                            </div>
                          </div>
                          <div>
                            <div className="text-xs text-gray-500">Max DD</div>
                            <div className="text-sm font-semibold text-red-600">
                              {backtest.max_drawdown
                                ? `${(Math.abs(backtest.max_drawdown) * 100).toFixed(1)}%`
                                : 'N/A'}
                            </div>
                          </div>
                        </div>
                      )}
                      <div className="flex items-center justify-between text-xs text-gray-500">
                        <span>
                          {new Date(backtest.created_at).toLocaleString()}
                        </span>
                        {backtest.status === 'completed' && (
                          <Link
                            to={`/results/${backtest.backtest_id}`}
                            className="text-blue-600 hover:text-blue-700 font-medium"
                          >
                            View Results →
                          </Link>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Right Column: Stats */}
          <div className="space-y-6">
            {/* Quick Stats */}
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-sm font-semibold text-gray-700 mb-4">Quick Stats</h3>
              <div className="space-y-3">
                <div>
                  <div className="text-xs text-gray-500">Total Backtests</div>
                  <div className="text-2xl font-bold text-gray-900">
                    {strategy.backtests.length}
                  </div>
                </div>
                <div>
                  <div className="text-xs text-gray-500">Institutions Following</div>
                  <div className="text-2xl font-bold text-purple-600">
                    {strategy.selected_institutions.length}
                  </div>
                </div>
                {strategy.backtests.length > 0 && (
                  <div>
                    <div className="text-xs text-gray-500">Latest Backtest</div>
                    <div className="text-sm text-gray-900">
                      {new Date(strategy.backtests[0].created_at).toLocaleDateString()}
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Actions */}
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-sm font-semibold text-gray-700 mb-4">Actions</h3>
              <div className="space-y-2">
                <button
                  onClick={handleReloadStrategy}
                  className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm font-medium"
                >
                  🔄 Reload & Edit
                </button>
                <Link
                  to="/builder"
                  className="block w-full px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 text-center text-sm font-medium"
                >
                  Create New Strategy
                </Link>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default StrategyDetailsPage;

