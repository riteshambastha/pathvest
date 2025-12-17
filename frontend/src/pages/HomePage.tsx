/**
 * Home Page
 */

import { Link } from 'react-router-dom'
import { useAuthStore } from '@/context/authStore'
import { ArrowRight, BarChart3, TrendingUp, Shield } from 'lucide-react'

export default function HomePage() {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated)

  return (
    <div className="space-y-16">
      {/* Hero Section */}
      <section className="text-center py-20">
        <h1 className="text-5xl font-bold text-gray-900 mb-6">
          Equity Backtesting Platform
        </h1>
        <p className="text-xl text-gray-600 mb-8 max-w-2xl mx-auto">
          Analyze historical SEC 13F filings, backtest investment strategies, and
          optimize your portfolio with data-driven insights.
        </p>
        <div className="flex justify-center space-x-4">
          {isAuthenticated ? (
            <Link
              to="/dashboard"
              className="inline-flex items-center space-x-2 bg-primary-600 text-white px-8 py-3 rounded-lg font-semibold hover:bg-primary-700 transition"
            >
              <span>Go to Dashboard</span>
              <ArrowRight className="w-5 h-5" />
            </Link>
          ) : (
            <>
              <Link
                to="/register"
                className="inline-flex items-center space-x-2 bg-primary-600 text-white px-8 py-3 rounded-lg font-semibold hover:bg-primary-700 transition"
              >
                <span>Get Started</span>
                <ArrowRight className="w-5 h-5" />
              </Link>
              <Link
                to="/login"
                className="inline-flex items-center space-x-2 border-2 border-primary-600 text-primary-600 px-8 py-3 rounded-lg font-semibold hover:bg-primary-50 transition"
              >
                <span>Sign In</span>
              </Link>
            </>
          )}
        </div>
      </section>

      {/* Features Section */}
      <section className="grid md:grid-cols-3 gap-8 py-16">
        <div className="text-center p-6">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-primary-100 text-primary-600 rounded-full mb-4">
            <BarChart3 className="w-8 h-8" />
          </div>
          <h3 className="text-xl font-semibold text-gray-900 mb-2">
            SEC 13F Data
          </h3>
          <p className="text-gray-600">
            Access real-time and historical 13F-HR filings from institutional
            investors like Renaissance Technologies.
          </p>
        </div>

        <div className="text-center p-6">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-primary-100 text-primary-600 rounded-full mb-4">
            <TrendingUp className="w-8 h-8" />
          </div>
          <h3 className="text-xl font-semibold text-gray-900 mb-2">
            Strategy Backtesting
          </h3>
          <p className="text-gray-600">
            Test your investment strategies against historical data and optimize
            for maximum returns.
          </p>
        </div>

        <div className="text-center p-6">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-primary-100 text-primary-600 rounded-full mb-4">
            <Shield className="w-8 h-8" />
          </div>
          <h3 className="text-xl font-semibold text-gray-900 mb-2">
            Risk Analysis
          </h3>
          <p className="text-gray-600">
            Comprehensive risk metrics including AUM analysis, concentration
            ratios, and portfolio diversification.
          </p>
        </div>
      </section>
    </div>
  )
}

