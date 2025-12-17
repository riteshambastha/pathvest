/**
 * Type definitions for the application
 */

export interface User {
  id: number
  email: string
  full_name?: string
  is_active: boolean
  is_superuser: boolean
  created_at: string
  updated_at: string
}

export interface Portfolio {
  id: number
  user_id: number
  name: string
  description?: string
  strategy_type: string
  initial_capital: number
  current_value?: number
  total_return?: number
  created_at: string
  updated_at: string
}

export interface PortfolioCreate {
  name: string
  description?: string
  strategy_type: string
  initial_capital: number
}

export interface PortfolioUpdate {
  name?: string
  description?: string
  strategy_type?: string
  initial_capital?: number
  current_value?: number
  total_return?: number
}

export interface LoginRequest {
  username: string // email
  password: string
}

export interface RegisterRequest {
  email: string
  password: string
  full_name?: string
}

export interface AuthResponse {
  access_token: string
  token_type: string
}

