/**
 * SEC Data Service
 * Handles all API calls related to SEC filings and holdings data
 */

import { apiClient } from './api'
import type {
  Institution,
  Filing,
  FilingSearchParams,
  FilingSearchResponse,
  FilingHoldingsResponse,
} from '../types/sec'

class SECService {
  /**
   * Get list of institutions
   */
  async getInstitutions(popularOnly: boolean = false): Promise<Institution[]> {
    const response = await apiClient.get<Institution[]>('/api/v1/sec/institutions', {
      params: { popular_only: popularOnly },
    })
    return response.data
  }

  /**
   * Seed popular institutions
   */
  async seedInstitutions(): Promise<void> {
    await apiClient.post('/api/v1/sec/institutions/seed')
  }

  /**
   * Search for SEC filings with smart caching
   */
  async searchFilings(params: FilingSearchParams): Promise<FilingSearchResponse> {
    // Build query parameters, excluding undefined values
    const queryParams: any = {
      cik: params.cik,
      form_type: params.formType || '13F-HR',
      size: params.size || 10,
      force_refresh: params.forceRefresh || false,
    }
    
    // Only add date params if they're provided
    if (params.fromDate) {
      queryParams.from_date = params.fromDate
    }
    if (params.toDate) {
      queryParams.to_date = params.toDate
    }

    const response = await apiClient.get<FilingSearchResponse>('/api/v1/sec/filings/search', {
      params: queryParams,
    })
    return response.data
  }

  /**
   * Get filing details by ID
   */
  async getFiling(filingId: number): Promise<Filing> {
    const response = await apiClient.get<Filing>(`/api/v1/sec/filings/${filingId}`)
    return response.data
  }

  /**
   * Get holdings for a specific filing
   */
  async getFilingHoldings(filingId: number): Promise<FilingHoldingsResponse> {
    const response = await apiClient.get<FilingHoldingsResponse>(
      `/api/v1/sec/filings/${filingId}/holdings`
    )
    return response.data
  }
}

export const secService = new SECService()
