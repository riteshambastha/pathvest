import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { apiClient } from '@/services/api';

interface Strategy {
  id: number;
  name: string;
  description: string | null;
  selected_institutions: string[];
  status: string;
  created_at: string;
  backtests_count: number;
  latest_backtest: {
    backtest_id: string;
    status: string;
    total_return: number | null;
    sharpe_ratio: number | null;
    created_at: string;
  } | null;
}

const MyStrategiesPage: React.FC = () => {
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadStrategies();
  }, []);

  const loadStrategies = async () => {
    try {
      setLoading(true);
      const response = await apiClient.get('/api/v1/strategies');
      setStrategies(response.data.strategies || []);
    } catch (err) {
      setError('Failed to load strategies');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteStrategy = async (strategyId: number, strategyName: string) => {
    if (confirm(`Are you sure you want to delete "${strategyName}"? This will also delete all associated backtests and cannot be undone.`)) {
      try {
        await apiClient.delete(`/api/v1/strategies/${strategyId}`);
        
        // Remove from local state
        setStrategies((prev) => prev.filter((s) => s.id !== strategyId));
        
        // Show success message
        alert(`Successfully deleted "${strategyName}"`);
      } catch (err: any) {
        console.error('Failed to delete strategy:', err);
        const errorMessage = err.response?.data?.detail || 'Failed to delete strategy';
        alert(`Error: ${errorMessage}`);
      }
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50">
        {/* Header */}
        <div className="bg-white shadow">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-3xl font-bold text-gray-900">My Strategies</h1>
                <p className="mt-1 text-sm text-gray-600">Loading your strategies...</p>
              </div>
            </div>
          </div>
        </div>

        {/* Loading Skeleton */}
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="bg-white rounded-lg shadow p-6 animate-pulse">
                <div className="h-6 bg-gray-200 rounded w-3/4 mb-4"></div>
                <div className="h-4 bg-gray-200 rounded w-1/2 mb-4"></div>
                <div className="h-20 bg-gray-100 rounded mb-4"></div>
                <div className="flex gap-2">
                  <div className="h-10 bg-gray-200 rounded flex-1"></div>
                  <div className="h-10 bg-gray-200 rounded flex-1"></div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-600">{error}</p>
          <button
            onClick={loadStrategies}
            className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            Retry
          </button>
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
            <div>
              <h1 className="text-3xl font-bold text-gray-900">My Strategies</h1>
              <p className="mt-1 text-sm text-gray-600">
                All your saved strategies and backtest history
              </p>
            </div>
            <Link
              to="/"
              className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition font-medium"
            >
              + Create New Strategy
            </Link>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {strategies.length === 0 ? (
          <div className="bg-white rounded-lg shadow p-12 text-center">
            <svg
              className="mx-auto h-12 w-12 text-gray-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
              />
            </svg>
            <h3 className="mt-2 text-sm font-medium text-gray-900">No strategies yet</h3>
            <p className="mt-1 text-sm text-gray-500">
              Get started by creating your first strategy
            </p>
            <div className="mt-6">
              <Link
                to="/"
                className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
              >
                + Create Strategy
              </Link>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {strategies.map((strategy) => (
              <div
                key={strategy.id}
                className="bg-white rounded-lg shadow hover:shadow-lg transition-shadow overflow-hidden"
              >
                <div className="p-6">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <h3 className="text-lg font-semibold text-gray-900 mb-2">
                        {strategy.name}
                      </h3>
                      {strategy.description && (
                        <p className="text-sm text-gray-600 mb-3">{strategy.description}</p>
                      )}
                    </div>
                    <span
                      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                        strategy.status === 'active'
                          ? 'bg-green-100 text-green-800'
                          : 'bg-gray-100 text-gray-800'
                      }`}
                      title={strategy.status === 'active' ? 'Strategy is saved and ready to use' : strategy.status}
                    >
                      {strategy.status === 'active' ? '✓ Saved' : strategy.status}
                    </span>
                  </div>

                  {/* Institutions */}
                  {strategy.selected_institutions.length > 0 && (
                    <div className="mb-4">
                      <div className="flex flex-wrap gap-1">
                        {strategy.selected_institutions.slice(0, 2).map((inst, idx) => (
                          <span
                            key={idx}
                            className="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium bg-purple-100 text-purple-800"
                          >
                            🏦 {inst}
                          </span>
                        ))}
                        {strategy.selected_institutions.length > 2 && (
                          <span className="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium bg-gray-100 text-gray-600">
                            +{strategy.selected_institutions.length - 2} more
                          </span>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Latest Backtest */}
                  {strategy.latest_backtest ? (
                    <div className="bg-gray-50 rounded-lg p-4 mb-4">
                      <div className="text-xs text-gray-500 mb-2">Latest Backtest</div>
                      <div className="grid grid-cols-2 gap-3">
                        <div>
                          <div className="text-xs text-gray-600">Return</div>
                          <div className="text-lg font-bold text-green-600">
                            {strategy.latest_backtest.total_return
                              ? `${(strategy.latest_backtest.total_return * 100).toFixed(1)}%`
                              : 'N/A'}
                          </div>
                        </div>
                        <div>
                          <div className="text-xs text-gray-600">Sharpe</div>
                          <div className="text-lg font-bold text-blue-600">
                            {strategy.latest_backtest.sharpe_ratio?.toFixed(2) || 'N/A'}
                          </div>
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="bg-yellow-50 rounded-lg p-4 mb-4">
                      <div className="text-sm text-yellow-800">No backtests yet</div>
                    </div>
                  )}

                  {/* Meta Info */}
                  <div className="flex items-center justify-between text-xs text-gray-500 mb-4">
                    <span>Created {new Date(strategy.created_at).toLocaleDateString()}</span>
                    <span>{strategy.backtests_count} backtest(s)</span>
                  </div>

                  {/* Actions */}
                  <div className="space-y-2">
                    <div className="flex gap-2">
                      <Link
                        to={`/strategies/${strategy.id}`}
                        className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 text-center"
                      >
                        View Details
                      </Link>
                      {strategy.latest_backtest && (
                        <Link
                          to={`/results/${strategy.latest_backtest.backtest_id}`}
                          className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 text-center"
                        >
                          View Results
                        </Link>
                      )}
                    </div>
                    <button
                      onClick={() => handleDeleteStrategy(strategy.id, strategy.name)}
                      className="w-full px-4 py-2 border border-red-300 rounded-lg text-sm font-medium text-red-700 hover:bg-red-50 text-center"
                    >
                      🗑️ Delete Strategy
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default MyStrategiesPage;

