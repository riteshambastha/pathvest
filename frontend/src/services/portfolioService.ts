/**
 * Portfolio API Service
 */

import apiClient from './api'
import type { Portfolio, PortfolioCreate, PortfolioUpdate } from '@/types'

export const portfolioService = {
  getAll: async (skip = 0, limit = 100): Promise<Portfolio[]> => {
    const response = await apiClient.get<Portfolio[]>('/api/v1/portfolios/', {
      params: { skip, limit },
    })
    return response.data
  },

  getById: async (id: number): Promise<Portfolio> => {
    const response = await apiClient.get<Portfolio>(`/api/v1/portfolios/${id}`)
    return response.data
  },

  create: async (data: PortfolioCreate): Promise<Portfolio> => {
    const response = await apiClient.post<Portfolio>('/api/v1/portfolios/', data)
    return response.data
  },

  update: async (id: number, data: PortfolioUpdate): Promise<Portfolio> => {
    const response = await apiClient.put<Portfolio>(`/api/v1/portfolios/${id}`, data)
    return response.data
  },

  delete: async (id: number): Promise<void> => {
    await apiClient.delete(`/api/v1/portfolios/${id}`)
  },
}

