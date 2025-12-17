/**
 * Authentication API Service
 */

import apiClient from './api'
import type { User, LoginRequest, RegisterRequest, AuthResponse } from '@/types'

export const authService = {
  login: async (data: LoginRequest): Promise<AuthResponse> => {
    const formData = new FormData()
    formData.append('username', data.username)
    formData.append('password', data.password)
    
    const response = await apiClient.post<AuthResponse>('/api/v1/auth/login', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data
  },

  register: async (data: RegisterRequest): Promise<User> => {
    const response = await apiClient.post<User>('/api/v1/auth/register', data)
    return response.data
  },

  getCurrentUser: async (): Promise<User> => {
    const response = await apiClient.get<User>('/api/v1/auth/me')
    return response.data
  },
}

