import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL 
  ? `${import.meta.env.VITE_API_BASE_URL}/api/v1`
  : 'http://localhost:8000/api/v1';

export interface BacktestRequest {
  strategy_config: any;
  enable_logging: boolean;
  save_results: boolean;
}

export interface BacktestSummary {
  total_return: number;
  cagr: number;
  volatility: number;
  sharpe_ratio: number;
  sortino_ratio: number;
  max_drawdown: number;
  romad: number;
  alpha: number;
  beta: number;
  information_ratio: number;
  var_95: number;
  cvar_95: number;
  win_rate_daily: number;
  win_rate_monthly: number;
  win_rate_yearly: number;
  best_day: number;
  worst_day: number;
  benchmark_total_return: number;
  benchmark_cagr: number;
}

export interface Trade {
  entry_date: string;
  exit_date?: string;
  ticker: string;
  entry_price: number;
  exit_price?: number;
  shares: number;
  pnl?: number;
  return_pct?: number;
  holding_period_days?: number;
  exit_reason?: string;
  signal_type?: string;
  conviction_score?: number;
  rank?: number;
}

export interface BacktestResponse {
  backtest_id: string;
  status: string;
  execution_time_seconds: number;
  summary: BacktestSummary;
  equity_curve: {
    dates: string[];
    portfolio_values: number[];
    benchmark_values: number[];
  };
  trades: Trade[];
  strategy_name?: string;
  start_date?: string;
  end_date?: string;
  initial_capital?: number;
  stocks_analyzed?: string[];
  sec_filings_fetched?: number;
  institutional_signals?: {
    sec_filings_fetched?: number;
    institutions_tracked?: number;
    simulation_mode?: string;
  };
  selected_institutions?: string[];
  real_market_data?: {
    data_source?: string;
    api_calls?: number;
    note?: string;
  };
}

export interface BacktestStatus {
  backtest_id: string;
  status: string;
  progress_pct?: number;
  message?: string;
  estimated_completion_seconds?: number;
}

export interface Attribution {
  by_signal_type: Record<string, any>;
  by_stock: Array<any>;
  by_time_period: Record<string, any>;
  by_holding_period: Array<any>;
  win_loss_analysis: Record<string, any>;
}

// Submit a new backtest
export const submitBacktest = async (request: BacktestRequest): Promise<string> => {
  const response = await axios.post(`${API_BASE_URL}/backtest/run`, request);
  return response.data.backtest_id;
};

// Get backtest status
export const getBacktestStatus = async (backtestId: string): Promise<BacktestStatus> => {
  const response = await axios.get(`${API_BASE_URL}/backtest/${backtestId}/status`);
  return response.data;
};

// Get backtest results
export const getBacktestResults = async (backtestId: string): Promise<BacktestResponse> => {
  const response = await axios.get(`${API_BASE_URL}/backtest/${backtestId}`);
  return response.data;
};

// Get attribution analysis
export const getAttribution = async (backtestId: string): Promise<Attribution> => {
  const response = await axios.get(`${API_BASE_URL}/analytics/${backtestId}/attribution`);
  return response.data;
};

// Get metrics
export const getMetrics = async (backtestId: string): Promise<Record<string, number>> => {
  const response = await axios.get(`${API_BASE_URL}/analytics/${backtestId}/metrics`);
  return response.data;
};

// Get visualization (HTML format)
export const getVisualization = async (
  backtestId: string,
  type: 'equity-curve' | 'monte-carlo-cone' | 'parameter-sensitivity' | 'walk-forward-matrix' | 'stress-test',
  format: 'html' | 'json' | 'png' = 'html'
): Promise<string> => {
  const response = await axios.get(
    `${API_BASE_URL}/analytics/${backtestId}/visualizations/${type}?format=${format}`
  );
  return response.data;
};

// Export to CSV (trades)
export const exportTradesCSV = async (backtestId: string): Promise<Blob> => {
  const response = await axios.get(`${API_BASE_URL}/analytics/${backtestId}/export/csv/trades`, {
    responseType: 'blob',
  });
  return response.data;
};

// Export to CSV (equity curve)
export const exportEquityCurveCSV = async (backtestId: string): Promise<Blob> => {
  const response = await axios.get(`${API_BASE_URL}/analytics/${backtestId}/export/csv/equity-curve`, {
    responseType: 'blob',
  });
  return response.data;
};

// Export to Excel
export const exportToExcel = async (backtestId: string, includeAttribution: boolean = true): Promise<Blob> => {
  const response = await axios.get(
    `${API_BASE_URL}/analytics/${backtestId}/export/excel?include_attribution=${includeAttribution}`,
    { responseType: 'blob' }
  );
  return response.data;
};

// Export to PDF
export const exportToPDF = async (backtestId: string): Promise<Blob> => {
  const response = await axios.get(`${API_BASE_URL}/analytics/${backtestId}/export/pdf`, {
    responseType: 'blob',
  });
  return response.data;
};

// Helper function to download a blob
export const downloadBlob = (blob: Blob, filename: string) => {
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  window.URL.revokeObjectURL(url);
};

