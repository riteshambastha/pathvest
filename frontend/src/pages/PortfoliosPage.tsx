/**
 * Portfolios Page
 */

import { useState } from 'react'
import { Link } from 'react-router-dom'
import { usePortfolios, useCreatePortfolio } from '@/hooks/usePortfolio'
import { Plus, TrendingUp, TrendingDown } from 'lucide-react'
import { formatCurrency, formatDate } from '@/utils/helpers'
import type { PortfolioCreate } from '@/types'

export default function PortfoliosPage() {
  const { data: portfolios, isLoading } = usePortfolios()
  const createPortfolio = useCreatePortfolio()
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [formData, setFormData] = useState<PortfolioCreate>({
    name: '',
    description: '',
    strategy_type: '',
    initial_capital: 0,
  })

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      await createPortfolio.mutateAsync(formData)
      setShowCreateForm(false)
      setFormData({
        name: '',
        description: '',
        strategy_type: '',
        initial_capital: 0,
      })
    } catch (error) {
      console.error('Failed to create portfolio:', error)
    }
  }

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Portfolios</h1>
          <p className="text-gray-600 mt-2">Manage and analyze your investment portfolios</p>
        </div>
        <button
          onClick={() => setShowCreateForm(!showCreateForm)}
          className="inline-flex items-center space-x-2 bg-primary-600 text-white px-6 py-3 rounded-lg font-semibold hover:bg-primary-700 transition"
        >
          <Plus className="w-5 h-5" />
          <span>New Portfolio</span>
        </button>
      </div>

      {/* Create Portfolio Form */}
      {showCreateForm && (
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Create New Portfolio</h2>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Portfolio Name
              </label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                required
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Strategy Type
              </label>
              <input
                type="text"
                value={formData.strategy_type}
                onChange={(e) => setFormData({ ...formData, strategy_type: e.target.value })}
                required
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                placeholder="e.g., Value Investing, Momentum, etc."
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Initial Capital
              </label>
              <input
                type="number"
                value={formData.initial_capital}
                onChange={(e) => setFormData({ ...formData, initial_capital: parseFloat(e.target.value) })}
                required
                min="0"
                step="0.01"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Description (Optional)
              </label>
              <textarea
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                rows={3}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
              />
            </div>

            <div className="flex space-x-4">
              <button
                type="submit"
                disabled={createPortfolio.isPending}
                className="bg-primary-600 text-white px-6 py-2 rounded-lg font-semibold hover:bg-primary-700 disabled:opacity-50"
              >
                {createPortfolio.isPending ? 'Creating...' : 'Create Portfolio'}
              </button>
              <button
                type="button"
                onClick={() => setShowCreateForm(false)}
                className="border border-gray-300 text-gray-700 px-6 py-2 rounded-lg font-semibold hover:bg-gray-50"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Portfolios List */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {isLoading ? (
          <p className="text-gray-600">Loading portfolios...</p>
        ) : portfolios && portfolios.length > 0 ? (
          portfolios.map((portfolio) => (
            <Link
              key={portfolio.id}
              to={`/portfolios/${portfolio.id}`}
              className="bg-white rounded-lg shadow hover:shadow-lg transition p-6"
            >
              <h3 className="text-xl font-semibold text-gray-900 mb-2">{portfolio.name}</h3>
              <p className="text-sm text-gray-600 mb-4">{portfolio.strategy_type}</p>

              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-sm text-gray-600">Current Value:</span>
                  <span className="font-semibold text-gray-900">
                    {formatCurrency(portfolio.current_value || portfolio.initial_capital)}
                  </span>
                </div>

                {portfolio.total_return !== null && portfolio.total_return !== undefined && (
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-gray-600">Total Return:</span>
                    <span className={`flex items-center space-x-1 font-semibold ${portfolio.total_return >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                      {portfolio.total_return >= 0 ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
                      <span>{formatCurrency(portfolio.total_return)}</span>
                    </span>
                  </div>
                )}

                <div className="pt-4 border-t">
                  <span className="text-xs text-gray-500">Created {formatDate(portfolio.created_at)}</span>
                </div>
              </div>
            </Link>
          ))
        ) : (
          <div className="col-span-3 text-center py-12">
            <p className="text-gray-600">No portfolios yet. Create your first portfolio to get started!</p>
          </div>
        )}
      </div>
    </div>
  )
}

