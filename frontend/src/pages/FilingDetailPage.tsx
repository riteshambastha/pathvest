/**
 * Filing Detail Page
 * Week 2-3: View detailed holdings for a specific filing
 */

import { useState, useEffect } from 'react'
import { useParams, useNavigate, useSearchParams } from 'react-router-dom'
import { secService } from '../services/secService'
import type { Filing, FilingHoldingsResponse } from '../types/sec'

export default function FilingDetailPage() {
  const { filingId } = useParams<{ filingId: string }>()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()

  // State
  const [filing, setFiling] = useState<Filing | null>(null)
  const [holdingsData, setHoldingsData] = useState<FilingHoldingsResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string>('')
  const [searchTerm, setSearchTerm] = useState<string>('')
  const [sortField, setSortField] = useState<'name' | 'value' | 'percentage'>('value')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')

  useEffect(() => {
    if (filingId) {
      loadFilingDetails()
    }
  }, [filingId])

  const loadFilingDetails = async () => {
    try {
      setLoading(true)
      setError('')

      const id = parseInt(filingId!)
      const [filingData, holdingsResp] = await Promise.all([
        secService.getFiling(id),
        secService.getFilingHoldings(id),
      ])

      setFiling(filingData)
      setHoldingsData(holdingsResp)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load filing details')
    } finally {
      setLoading(false)
    }
  }

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value)
  }

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    })
  }

  const handleSort = (field: 'name' | 'value' | 'percentage') => {
    if (sortField === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')
    } else {
      setSortField(field)
      setSortOrder('desc')
    }
  }

  const handleBackToExplorer = () => {
    // Preserve search params when going back
    const cik = filing?.cik || searchParams.get('cik')
    const from = searchParams.get('from')
    const to = searchParams.get('to')
    
    const params = new URLSearchParams()
    if (cik) params.set('cik', cik)
    if (from) params.set('from', from)
    if (to) params.set('to', to)
    
    navigate(`/sec?${params.toString()}`)
  }

  // Filter and sort holdings
  const filteredAndSortedHoldings = () => {
    if (!holdingsData?.holdings) return []

    let filtered = holdingsData.holdings

    // Search filter
    if (searchTerm) {
      const term = searchTerm.toLowerCase()
      filtered = filtered.filter(
        (h) =>
          h.nameOfIssuer.toLowerCase().includes(term) ||
          h.ticker?.toLowerCase().includes(term) ||
          h.cusip.toLowerCase().includes(term)
      )
    }

    // Sort
    const sorted = [...filtered].sort((a, b) => {
      let comparison = 0

      if (sortField === 'name') {
        comparison = a.nameOfIssuer.localeCompare(b.nameOfIssuer)
      } else if (sortField === 'value') {
        comparison = a.value - b.value
      } else if (sortField === 'percentage') {
        comparison = a.percentage - b.percentage
      }

      return sortOrder === 'asc' ? comparison : -comparison
    })

    return sorted
  }

  const SortIcon = ({ field }: { field: 'name' | 'value' | 'percentage' }) => {
    if (sortField !== field) {
      return (
        <svg
          className="w-4 h-4 ml-1 text-gray-400"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M7 16V4m0 0L3 8m4-4l4 4m6 0v12m0 0l4-4m-4 4l-4-4"
          />
        </svg>
      )
    }

    return sortOrder === 'asc' ? (
      <svg
        className="w-4 h-4 ml-1 text-blue-600"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M5 15l7-7 7 7"
        />
      </svg>
    ) : (
      <svg
        className="w-4 h-4 ml-1 text-blue-600"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M19 9l-7 7-7-7"
        />
      </svg>
    )
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 py-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="bg-white rounded-lg shadow-sm p-12 text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
            <p className="mt-4 text-sm text-gray-500">Loading filing details...</p>
          </div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 py-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md">
            {error}
          </div>
          <button
            onClick={handleBackToExplorer}
            className="mt-4 text-blue-600 hover:text-blue-800"
          >
            ← Back to SEC Explorer
          </button>
        </div>
      </div>
    )
  }

  const holdings = filteredAndSortedHoldings()

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Back Button */}
        <button
          onClick={handleBackToExplorer}
          className="mb-4 text-blue-600 hover:text-blue-800 flex items-center"
        >
          <svg
            className="w-4 h-4 mr-1"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M15 19l-7-7 7-7"
            />
          </svg>
          Back to SEC Explorer
        </button>

        {/* Filing Header */}
        <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
          <h1 className="text-2xl font-bold text-gray-900 mb-4">
            {filing?.companyName}
          </h1>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div>
              <p className="text-sm text-gray-500">CIK</p>
              <p className="text-lg font-semibold text-gray-900">{filing?.cik}</p>
            </div>
            <div>
              <p className="text-sm text-gray-500">Filed Date</p>
              <p className="text-lg font-semibold text-gray-900">
                {filing?.filedAt ? formatDate(filing.filedAt) : 'N/A'}
              </p>
            </div>
            <div>
              <p className="text-sm text-gray-500">Total Holdings</p>
              <p className="text-lg font-semibold text-gray-900">
                {holdingsData?.total_holdings?.toLocaleString() || 'N/A'}
              </p>
            </div>
            <div>
              <p className="text-sm text-gray-500">Total Value</p>
              <p className="text-lg font-semibold text-gray-900">
                {holdingsData?.total_value
                  ? formatCurrency(holdingsData.total_value * 1000)
                  : 'N/A'}
              </p>
            </div>
          </div>

          {/* Links */}
          {filing?.linkToFilingDetails && (
            <div className="mt-4">
              <a
                href={filing.linkToFilingDetails}
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-600 hover:text-blue-800 text-sm"
              >
                View on SEC.gov →
              </a>
            </div>
          )}
        </div>

        {/* Holdings Section */}
        <div className="bg-white rounded-lg shadow-sm p-6">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-xl font-bold text-gray-900">Portfolio Holdings</h2>

            {/* Search */}
            <div className="w-64">
              <input
                type="text"
                placeholder="Search by name, ticker, or CUSIP..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>

          {/* Holdings Table */}
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th
                    className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                    onClick={() => handleSort('name')}
                  >
                    <div className="flex items-center">
                      Issuer Name
                      <SortIcon field="name" />
                    </div>
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Ticker
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    CUSIP
                  </th>
                  <th
                    className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                    onClick={() => handleSort('value')}
                  >
                    <div className="flex items-center justify-end">
                      Value
                      <SortIcon field="value" />
                    </div>
                  </th>
                  <th
                    className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                    onClick={() => handleSort('percentage')}
                  >
                    <div className="flex items-center justify-end">
                      % of Portfolio
                      <SortIcon field="percentage" />
                    </div>
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Shares
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {holdings.map((holding) => (
                  <tr key={holding.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4">
                      <div className="text-sm font-medium text-gray-900">
                        {holding.nameOfIssuer}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {holding.ticker || '-'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 font-mono">
                      {holding.cusip}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 text-right font-semibold">
                      {formatCurrency(holding.valueUsd)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 text-right">
                      {holding.percentage.toFixed(2)}%
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 text-right">
                      {holding.sharesOrPrnAmt?.toLocaleString() || '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Empty State */}
          {holdings.length === 0 && (
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
              <h3 className="mt-2 text-sm font-medium text-gray-900">No holdings found</h3>
              <p className="mt-1 text-sm text-gray-500">
                {searchTerm
                  ? 'Try adjusting your search term'
                  : 'Holdings data is being fetched'}
              </p>
            </div>
          )}

          {/* Pagination info */}
          {holdings.length > 0 && (
            <div className="mt-4 text-sm text-gray-500">
              Showing {holdings.length} of {holdingsData?.holdings.length || 0} holdings
              {searchTerm && ' (filtered)'}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
