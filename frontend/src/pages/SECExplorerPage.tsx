/**
 * SEC Explorer Page
 * Week 1-2: Browse and search institutional 13F-HR filings
 */

import { useState, useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { secService } from '../services/secService'
import type { Institution, Filing, FilingSearchParams } from '../types/sec'

export default function SECExplorerPage() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()

  // State
  const [institutions, setInstitutions] = useState<Institution[]>([])
  const [selectedInstitution, setSelectedInstitution] = useState<string>(
    searchParams.get('cik') || ''
  )
  const [filings, setFilings] = useState<Filing[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string>('')
  const [fromDate, setFromDate] = useState<string>(searchParams.get('from') || '')
  const [toDate, setToDate] = useState<string>(searchParams.get('to') || '')
  const [forceRefresh, setForceRefresh] = useState(false)
  const [cached, setCached] = useState(false)

  // Load institutions on mount
  useEffect(() => {
    loadInstitutions()
  }, [])

  const loadInstitutions = async () => {
    try {
      const data = await secService.getInstitutions(false)
      setInstitutions(data)

      // If no institutions, seed them
      if (data.length === 0) {
        await secService.seedInstitutions()
        const newData = await secService.getInstitutions(false)
        setInstitutions(newData)
      }

      // Auto-search if we have URL params (coming back from filing detail)
      const cik = searchParams.get('cik')
      if (cik && data.length > 0) {
        // Trigger search automatically
        performSearch(cik, searchParams.get('from') || '', searchParams.get('to') || '')
      }
    } catch (err: any) {
      console.error('Error loading institutions:', err)
      setError('Failed to load institutions')
    }
  }

  const performSearch = async (cik: string, from: string, to: string) => {
    setLoading(true)
    setError('')

    try {
      const params: FilingSearchParams = {
        cik: cik,
        formType: '13F-HR',
        fromDate: from || undefined,
        toDate: to || undefined,
        size: 20,
        forceRefresh,
      }

      // Remove undefined values from params
      Object.keys(params).forEach(key => {
        if (params[key as keyof FilingSearchParams] === undefined) {
          delete params[key as keyof FilingSearchParams]
        }
      })

      const response = await secService.searchFilings(params)
      setFilings(response.filings)
      setCached(response.cached)

      // Update URL with search params (for back navigation)
      const urlParams = new URLSearchParams()
      urlParams.set('cik', cik)
      if (from) urlParams.set('from', from)
      if (to) urlParams.set('to', to)
      setSearchParams(urlParams)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to search filings')
      setFilings([])
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = async () => {
    if (!selectedInstitution) {
      setError('Please select an institution')
      return
    }

    await performSearch(selectedInstitution, fromDate, toDate)
  }

  const handleViewFiling = (filing: Filing) => {
    // Preserve current search params when navigating to detail page
    const params = new URLSearchParams()
    params.set('cik', selectedInstitution)
    if (fromDate) params.set('from', fromDate)
    if (toDate) params.set('to', toDate)
    
    navigate(`/sec/filings/${filing.id}?${params.toString()}`)
  }

  const formatCurrency = (value: number | undefined) => {
    if (!value) return 'N/A'
    // Value is in thousands of dollars in DB (e.g., 12215126 means $12,215,126,000)
    // Convert to billions: value * 1000 / 1,000,000,000 = value / 1,000,000
    // But that gives us trillions...
    // Actually, the SEC API returns value in thousands, so:
    // XML: 12215 means $12,215,000 (12.2 million)
    // So we should just divide by 1,000,000 to get millions, then by 1,000 more for billions
    const billions = value / 1000000000
    if (billions >= 1) {
      return `$${billions.toFixed(2)}B`
    }
    // Show in millions
    const millions = value / 1000000
    return `$${millions.toFixed(2)}M`
  }

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    })
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">SEC 13F-HR Explorer</h1>
          <p className="mt-2 text-sm text-gray-600">
            Browse institutional holdings from SEC 13F-HR filings
          </p>
        </div>

        {/* Search Form */}
        <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Institution Select */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Institution
              </label>
              <select
                value={selectedInstitution}
                onChange={(e) => setSelectedInstitution(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">Select an institution...</option>
                {institutions.map((inst) => (
                  <option key={inst.id} value={inst.cik}>
                    {inst.name}
                  </option>
                ))}
              </select>
            </div>

            {/* From Date */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                From Date
              </label>
              <input
                type="date"
                value={fromDate}
                onChange={(e) => setFromDate(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            {/* To Date */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                To Date
              </label>
              <input
                type="date"
                value={toDate}
                onChange={(e) => setToDate(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            {/* Search Button */}
            <div className="flex items-end">
              <button
                onClick={handleSearch}
                disabled={loading}
                className="w-full bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
              >
                {loading ? 'Searching...' : 'Search Filings'}
              </button>
            </div>
          </div>

          {/* Force Refresh Checkbox */}
          <div className="mt-4 flex items-center">
            <input
              type="checkbox"
              id="forceRefresh"
              checked={forceRefresh}
              onChange={(e) => setForceRefresh(e.target.checked)}
              className="h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
            />
            <label htmlFor="forceRefresh" className="ml-2 text-sm text-gray-700">
              Force refresh from API (otherwise use cached data)
            </label>
          </div>
        </div>

        {/* Error Message */}
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md mb-6">
            {error}
          </div>
        )}

        {/* Cache Notice */}
        {!loading && filings.length > 0 && (
          <div
            className={`mb-4 px-4 py-2 rounded-md text-sm ${
              cached
                ? 'bg-green-50 border border-green-200 text-green-700'
                : 'bg-blue-50 border border-blue-200 text-blue-700'
            }`}
          >
            {cached
              ? '✓ Data served from cache (API request saved)'
              : '↻ Data fetched from SEC-API.io and cached for future use'}
          </div>
        )}

        {/* Filings Table */}
        {!loading && filings.length > 0 && (
          <div className="bg-white rounded-lg shadow-sm overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Company
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Filed Date
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Period
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Total Holdings
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Total Value
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {filings.map((filing) => (
                  <tr key={filing.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm font-medium text-gray-900">
                        {filing.companyName}
                      </div>
                      <div className="text-sm text-gray-500">CIK: {filing.cik}</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {formatDate(filing.filedAt)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {filing.periodOfReport || 'N/A'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {filing.totalHoldings?.toLocaleString() || 'N/A'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {formatCurrency(filing.totalValue)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      <button
                        onClick={() => handleViewFiling(filing)}
                        className="text-blue-600 hover:text-blue-800 font-medium"
                      >
                        View Details →
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Empty State */}
        {!loading && filings.length === 0 && !error && (
          <div className="bg-white rounded-lg shadow-sm p-12 text-center">
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
            <h3 className="mt-2 text-sm font-medium text-gray-900">No filings found</h3>
            <p className="mt-1 text-sm text-gray-500">
              Select an institution and click search to view 13F-HR filings
            </p>
          </div>
        )}

        {/* Loading State */}
        {loading && (
          <div className="bg-white rounded-lg shadow-sm p-12 text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
            <p className="mt-4 text-sm text-gray-500">Searching for filings...</p>
          </div>
        )}
      </div>
    </div>
  )
}
