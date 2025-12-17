/**
 * Portfolio Detail Page
 */

import { useParams, useNavigate } from 'react-router-dom'
import { usePortfolio, useDeletePortfolio } from '@/hooks/usePortfolio'
import { ArrowLeft, Trash2, Edit, TrendingUp, DollarSign } from 'lucide-react'
import { formatCurrency, formatDate, formatPercent } from '@/utils/helpers'

export default function PortfolioDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { data: portfolio, isLoading } = usePortfolio(parseInt(id!))
  const deletePortfolio = useDeletePortfolio()

  const handleDelete = async () => {
    if (window.confirm('Are you sure you want to delete this portfolio?')) {
      try {
        await deletePortfolio.mutateAsync(parseInt(id!))
        navigate('/portfolios')
      } catch (error) {
        console.error('Failed to delete portfolio:', error)
      }
    }
  }

  if (isLoading) {
    return <div className="text-center py-12">Loading...</div>
  }

  if (!portfolio) {
    return <div className="text-center py-12">Portfolio not found</div>
  }

  const returnPercent = portfolio.initial_capital > 0
    ? ((portfolio.total_return || 0) / portfolio.initial_capital) * 100
    : 0

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <button
          onClick={() => navigate('/portfolios')}
          className="inline-flex items-center space-x-2 text-gray-600 hover:text-gray-900"
        >
          <ArrowLeft className="w-5 h-5" />
          <span>Back to Portfolios</span>
        </button>

        <div className="flex space-x-3">
          <button className="inline-flex items-center space-x-2 border border-gray-300 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-50">
            <Edit className="w-4 h-4" />
            <span>Edit</span>
          </button>
          <button
            onClick={handleDelete}
            disabled={deletePortfolio.isPending}
            className="inline-flex items-center space-x-2 border border-red-300 text-red-600 px-4 py-2 rounded-lg hover:bg-red-50 disabled:opacity-50"
          >
            <Trash2 className="w-4 h-4" />
            <span>{deletePortfolio.isPending ? 'Deleting...' : 'Delete'}</span>
          </button>
        </div>
      </div>

      {/* Portfolio Info */}
      <div className="bg-white rounded-lg shadow p-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">{portfolio.name}</h1>
        <p className="text-gray-600 mb-6">{portfolio.strategy_type}</p>

        {portfolio.description && (
          <p className="text-gray-700 mb-6">{portfolio.description}</p>
        )}

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-8">
          <div className="bg-gradient-to-br from-blue-50 to-blue-100 rounded-lg p-6">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-blue-900">Initial Capital</span>
              <DollarSign className="w-5 h-5 text-blue-600" />
            </div>
            <p className="text-2xl font-bold text-blue-900">
              {formatCurrency(portfolio.initial_capital)}
            </p>
          </div>

          <div className="bg-gradient-to-br from-green-50 to-green-100 rounded-lg p-6">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-green-900">Current Value</span>
              <TrendingUp className="w-5 h-5 text-green-600" />
            </div>
            <p className="text-2xl font-bold text-green-900">
              {formatCurrency(portfolio.current_value || portfolio.initial_capital)}
            </p>
          </div>

          <div className={`bg-gradient-to-br ${returnPercent >= 0 ? 'from-emerald-50 to-emerald-100' : 'from-red-50 to-red-100'} rounded-lg p-6`}>
            <div className="flex items-center justify-between mb-2">
              <span className={`text-sm font-medium ${returnPercent >= 0 ? 'text-emerald-900' : 'text-red-900'}`}>
                Total Return
              </span>
              <TrendingUp className={`w-5 h-5 ${returnPercent >= 0 ? 'text-emerald-600' : 'text-red-600'}`} />
            </div>
            <p className={`text-2xl font-bold ${returnPercent >= 0 ? 'text-emerald-900' : 'text-red-900'}`}>
              {formatCurrency(portfolio.total_return || 0)}
            </p>
            <p className={`text-sm ${returnPercent >= 0 ? 'text-emerald-700' : 'text-red-700'}`}>
              {formatPercent(returnPercent)}
            </p>
          </div>
        </div>

        {/* Metadata */}
        <div className="mt-8 pt-8 border-t">
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="text-gray-600">Created:</span>
              <span className="ml-2 font-medium text-gray-900">{formatDate(portfolio.created_at)}</span>
            </div>
            <div>
              <span className="text-gray-600">Last Updated:</span>
              <span className="ml-2 font-medium text-gray-900">{formatDate(portfolio.updated_at)}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Performance Chart Placeholder */}
      <div className="bg-white rounded-lg shadow p-8">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Performance Chart</h2>
        <div className="h-64 flex items-center justify-center bg-gray-50 rounded-lg">
          <p className="text-gray-500">Performance chart will be displayed here</p>
        </div>
      </div>
    </div>
  )
}

