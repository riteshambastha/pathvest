/**
 * Dashboard Page
 */

import { useAuthStore } from '@/context/authStore'
import { usePortfolios } from '@/hooks/usePortfolio'
import { BarChart3, TrendingUp, DollarSign, Briefcase } from 'lucide-react'
import { formatCurrency } from '@/utils/helpers'

export default function DashboardPage() {
  const user = useAuthStore((state) => state.user)
  const { data: portfolios, isLoading } = usePortfolios()

  const totalValue = portfolios?.reduce((sum, p) => sum + (p.current_value || p.initial_capital), 0) || 0
  const totalReturn = portfolios?.reduce((sum, p) => sum + (p.total_return || 0), 0) || 0

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-gray-600 mt-2">Welcome back, {user?.full_name || user?.email}!</p>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Total Portfolios</p>
              <p className="text-2xl font-bold text-gray-900 mt-1">
                {isLoading ? '...' : portfolios?.length || 0}
              </p>
            </div>
            <Briefcase className="w-10 h-10 text-primary-600" />
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Total Value</p>
              <p className="text-2xl font-bold text-gray-900 mt-1">
                {isLoading ? '...' : formatCurrency(totalValue)}
              </p>
            </div>
            <DollarSign className="w-10 h-10 text-green-600" />
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Total Return</p>
              <p className="text-2xl font-bold text-gray-900 mt-1">
                {isLoading ? '...' : formatCurrency(totalReturn)}
              </p>
            </div>
            <TrendingUp className="w-10 h-10 text-blue-600" />
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Active Strategies</p>
              <p className="text-2xl font-bold text-gray-900 mt-1">
                {isLoading ? '...' : new Set(portfolios?.map(p => p.strategy_type)).size || 0}
              </p>
            </div>
            <BarChart3 className="w-10 h-10 text-purple-600" />
          </div>
        </div>
      </div>

      {/* Recent Portfolios */}
      <div className="bg-white rounded-lg shadow">
        <div className="p-6 border-b">
          <h2 className="text-xl font-semibold text-gray-900">Recent Portfolios</h2>
        </div>
        <div className="p-6">
          {isLoading ? (
            <p className="text-gray-600">Loading...</p>
          ) : portfolios && portfolios.length > 0 ? (
            <div className="space-y-4">
              {portfolios.slice(0, 5).map((portfolio) => (
                <div key={portfolio.id} className="flex items-center justify-between py-3 border-b last:border-0">
                  <div>
                    <h3 className="font-medium text-gray-900">{portfolio.name}</h3>
                    <p className="text-sm text-gray-600">{portfolio.strategy_type}</p>
                  </div>
                  <div className="text-right">
                    <p className="font-semibold text-gray-900">
                      {formatCurrency(portfolio.current_value || portfolio.initial_capital)}
                    </p>
                    {portfolio.total_return !== null && portfolio.total_return !== undefined && (
                      <p className={`text-sm ${portfolio.total_return >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                        {portfolio.total_return >= 0 ? '+' : ''}{formatCurrency(portfolio.total_return)}
                      </p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-600">No portfolios yet. Create your first portfolio!</p>
          )}
        </div>
      </div>
    </div>
  )
}

