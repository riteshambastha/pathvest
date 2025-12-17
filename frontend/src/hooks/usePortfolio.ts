/**
 * Custom hooks for API queries
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { portfolioService } from '@/services/portfolioService'
import type { PortfolioCreate, PortfolioUpdate } from '@/types'

export const usePortfolios = () => {
  return useQuery({
    queryKey: ['portfolios'],
    queryFn: () => portfolioService.getAll(),
  })
}

export const usePortfolio = (id: number) => {
  return useQuery({
    queryKey: ['portfolio', id],
    queryFn: () => portfolioService.getById(id),
    enabled: !!id,
  })
}

export const useCreatePortfolio = () => {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: (data: PortfolioCreate) => portfolioService.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['portfolios'] })
    },
  })
}

export const useUpdatePortfolio = () => {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: PortfolioUpdate }) =>
      portfolioService.update(id, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['portfolios'] })
      queryClient.invalidateQueries({ queryKey: ['portfolio', variables.id] })
    },
  })
}

export const useDeletePortfolio = () => {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: (id: number) => portfolioService.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['portfolios'] })
    },
  })
}

