import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import apiClient from '../../services/api';

interface Strategy {
  id: number;
  name: string;
  created_at: string;
  status: string;
  backtests_count: number;
  selected_institutions: string[];
  latest_backtest?: {
    backtest_id: string;
    status: string;
    total_return: number | null;
    sharpe_ratio: number | null;
    created_at: string;
  };
}

const StrategyLibrary: React.FC = () => {
  const navigate = useNavigate();
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [selectedStrategies, setSelectedStrategies] = useState<string[]>([]);
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
    } catch (err: any) {
      setError(err.message || 'Failed to load strategies');
      console.error('Error loading strategies:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSelect = (id: number) => {
    setSelectedStrategies((prev) =>
      prev.includes(id.toString()) ? prev.filter((s) => s !== id.toString()) : [...prev, id.toString()]
    );
  };

  const handleDelete = async (id: number) => {
    if (confirm('Are you sure you want to delete this strategy?')) {
      try {
        // TODO: Implement delete API call
        // await apiClient.delete(`/api/v1/strategies/${id}`);
        setStrategies((prev) => prev.filter((s) => s.id !== id));
      } catch (err) {
        console.error('Failed to delete strategy:', err);
        alert('Failed to delete strategy');
      }
    }
  };

  const handleCompare = () => {
    if (selectedStrategies.length >= 2) {
      navigate(`/compare?ids=${selectedStrategies.join(',')}`);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Strategy Library</h2>
          <p className="mt-1 text-sm text-gray-600">
            Saved strategies and their performance history
          </p>
        </div>
        
        {selectedStrategies.length >= 2 && (
          <button
            onClick={handleCompare}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
          >
            Compare Selected ({selectedStrategies.length})
          </button>
        )}
      </div>

      {/* Loading State */}
      {loading && (
        <div className="text-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading strategies...</p>
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-800">{error}</p>
        </div>
      )}

      {/* Stats Cards */}
      {!loading && !error && (
        <>
          <div className="grid grid-cols-1 gap-5 sm:grid-cols-3">
            <div className="bg-white overflow-hidden shadow rounded-lg">
              <div className="p-5">
                <div className="flex items-center">
                  <div className="flex-shrink-0">
                    <svg
                      className="h-6 w-6 text-gray-400"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                      />
                    </svg>
                  </div>
                  <div className="ml-5 w-0 flex-1">
                    <dl>
                      <dt className="text-sm font-medium text-gray-500 truncate">Total Strategies</dt>
                      <dd className="text-lg font-semibold text-gray-900">{strategies.length}</dd>
                    </dl>
                  </div>
                </div>
              </div>
            </div>

            <div className="bg-white overflow-hidden shadow rounded-lg">
              <div className="p-5">
                <div className="flex items-center">
                  <div className="flex-shrink-0">
                    <svg
                      className="h-6 w-6 text-green-400"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"
                      />
                    </svg>
                  </div>
                  <div className="ml-5 w-0 flex-1">
                    <dl>
                      <dt className="text-sm font-medium text-gray-500 truncate">Best Performer</dt>
                      <dd className="text-lg font-semibold text-gray-900">
                        {strategies.length > 0 && strategies.some(s => s.latest_backtest?.sharpe_ratio)
                          ? Math.max(...strategies.map((s) => s.latest_backtest?.sharpe_ratio || 0)).toFixed(2)
                          : '-'} SR
                      </dd>
                    </dl>
                  </div>
                </div>
              </div>
            </div>

            <div className="bg-white overflow-hidden shadow rounded-lg">
              <div className="p-5">
                <div className="flex items-center">
                  <div className="flex-shrink-0">
                    <svg
                      className="h-6 w-6 text-blue-400"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
                      />
                    </svg>
                  </div>
                  <div className="ml-5 w-0 flex-1">
                    <dl>
                      <dt className="text-sm font-medium text-gray-500 truncate">Total Backtests</dt>
                      <dd className="text-lg font-semibold text-gray-900">
                        {strategies.reduce((sum, s) => sum + s.backtests_count, 0)}
                      </dd>
                    </dl>
                  </div>
                </div>
              </div>
            </div>
          </div>

      {/* Strategies Table */}
      <div className="bg-white shadow rounded-lg overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                <input
                  type="checkbox"
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                  onChange={(e) => {
                    if (e.target.checked) {
                      setSelectedStrategies(strategies.map((s) => s.id.toString()));
                    } else {
                      setSelectedStrategies([]);
                    }
                  }}
                />
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Name
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Created
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Last Run
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Best Sharpe
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {strategies.map((strategy) => (
              <tr key={strategy.id} className="hover:bg-gray-50">
                <td className="px-6 py-4 whitespace-nowrap">
                  <input
                    type="checkbox"
                    checked={selectedStrategies.includes(strategy.id.toString())}
                    onChange={() => handleSelect(strategy.id)}
                    className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                  />
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="text-sm font-medium text-gray-900">{strategy.name}</div>
                  <div className="text-xs text-gray-500">
                    {strategy.selected_institutions.length} institutions
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {new Date(strategy.created_at).toLocaleDateString()}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {strategy.latest_backtest
                    ? new Date(strategy.latest_backtest.created_at).toLocaleDateString()
                    : '-'}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  {strategy.latest_backtest?.sharpe_ratio ? (
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                      {strategy.latest_backtest.sharpe_ratio.toFixed(2)}
                    </span>
                  ) : (
                    <span className="text-sm text-gray-400">-</span>
                  )}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium space-x-3">
                  {strategy.latest_backtest && (
                    <button
                      onClick={() => navigate(`/results/${strategy.latest_backtest?.backtest_id}`)}
                      className="text-blue-600 hover:text-blue-900"
                    >
                      View
                    </button>
                  )}
                  <button
                    onClick={() => navigate(`/strategies/${strategy.id}`)}
                    className="text-green-600 hover:text-green-900"
                  >
                    Details
                  </button>
                  <button
                    onClick={() => navigate(`/builder?clone=${strategy.id}`)}
                    className="text-gray-600 hover:text-gray-900"
                  >
                    Clone
                  </button>
                  <button
                    onClick={() => handleDelete(strategy.id)}
                    className="text-red-600 hover:text-red-900"
                  >
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {strategies.length === 0 && !loading && !error && (
        <div className="text-center py-12">
          <svg
            className="mx-auto h-12 w-12 text-gray-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
            />
          </svg>
          <h3 className="mt-2 text-sm font-medium text-gray-900">No strategies</h3>
          <p className="mt-1 text-sm text-gray-500">Get started by creating a new strategy.</p>
          <div className="mt-6">
            <button
              onClick={() => navigate('/builder')}
              className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
            >
              Create New Strategy
            </button>
          </div>
        </div>
      )}
        </>
      )}
    </div>
  );
};

export default StrategyLibrary;

