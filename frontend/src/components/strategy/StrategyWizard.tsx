import React, { useState, useEffect } from 'react';
import Step1_Setup from './steps/Step1_Setup';
import Step2_StockSelection from './steps/Step2_StockSelection';
import Step3_EntryPositionSizing from './steps/Step3_EntryPositionSizing';
import Step4_EntryScheduling from './steps/Step4_EntryScheduling';
import Step5_ExitModel from './steps/Step5_ExitModel';
import Step6_RiskManagement from './steps/Step6_RiskManagement';
import Step7_Parameters from './steps/Step7_Parameters';
import Step8_ReviewBacktest from './steps/Step8_ReviewBacktest';

export interface StrategyConfig {
  // Step 1: Setup
  name?: string;
  engine_type?: 'custom' | 'lean';
  backtest_period?: {
    start_date: string;
    end_date: string;
  };
  initial_capital?: number;
  max_positions?: number;  // Number of stocks to include in backtest (5-20 per SRS)

  // Step 2: Stock Selection
  selected_institutions?: string[];
  universe_filters?: {
    market_cap_min: number;
    index_membership: string;
    lookback_quarters: number;
  };
  sub_universe_filters?: {
    selected_institutions?: string[];
    investor?: {
      aum_min: number;
      track_record_quarters: number;
      concentration_max: number;
      turnover_max: number;
    };
    transaction?: {
      min_buy_value: number;
      share_increase_min: number;
    };
    insider?: {
      roles: string[];
      value_min: number;
    };
  };

  // Step 3: Position Sizing
  position_sizing?: {
    method?: string;
    max_position_size?: number;
    min_position_size?: number;
    max_positions?: number;
    min_positions?: number;
    percent_per_position?: number;
    rank_buffer?: number;
  };

  // Step 4: Entry Rules
  entry_rules?: {
    timing?: string;
    execution_delay?: number;
    entry_window_days?: number;
    technical_confirmation?: boolean;
    use_limit_orders?: boolean;
    max_slippage_pct?: number;
  };

  // Step 5: Exit Rules
  exit_rules?: {
    thesis_drift_enabled?: boolean;
    insider_reversal_enabled?: boolean;
    trailing_stop_enabled?: boolean;
    trailing_stop_pct?: number;
    take_profit_enabled?: boolean;
    take_profit_pct?: number;
    dead_money_enabled?: boolean;
    dead_money_quarters?: number;
    dead_money_threshold?: number;
    time_stop_enabled?: boolean;
    max_holding_days?: number;
    enable_thesis_drift?: boolean;
    enable_insider_reversal?: boolean;
    enable_trailing_stop?: boolean;
    trailing_stop_percent?: number;
    enable_dead_money?: boolean;
  };

  // Step 6: Risk Management
  risk_management?: {
    max_portfolio_drawdown?: number;
    max_position_loss?: number;
    correlation_limit?: number;
    sector_concentration_limit?: number;
    enable_dynamic_sizing?: boolean;
    volatility_scaling?: boolean;
    rebalancing_frequency?: string;
    cash_reserve_pct?: number;
  };

  // Transaction Costs
  transaction_costs?: {
    commission_per_trade?: number;
    commission_pct?: number;
    slippage_pct?: number;
    min_commission?: number;
    commission_per_share?: number;
    slippage_bps?: number;
  };

  // Step 7: Parameters & Technical Indicators
  entry_signals?: {
    enable_doubling_down?: boolean;
    enable_insider_buying?: boolean;
    enable_herding?: boolean;
    technical_confirmation?: {
      price_breakout_days?: number;
      sma_period?: number;
      rsi_period?: number;
      rsi_threshold?: number;
    };
  };

  // Rebalancing
  heartbeat?: {
    rebalance_frequency?: string;
  };

  // Step 8: Validation
  enable_validation?: boolean;
  validation_config?: {
    walk_forward?: boolean;
    monte_carlo?: boolean;
    parameter_sensitivity?: boolean;
    stress_test?: boolean;
  };

  // Conviction Scoring Weights (Step 7)
  conviction_weights?: {
    doubling_down: number;
    insider_buying: number;
    institutional_herding: number;
    technical_confirmation: number;
  };

  // Technical Parameters (Step 7)
  technical_params?: {
    sma_short: number;
    sma_long: number;
    rsi_period: number;
    breakout_days: number;
  };

  // Universe Filtration (Step 7)
  universe_filtration?: {
    min_market_cap_b: number;
    index_filter: string;
    min_daily_volume: number;
  };
}

const steps = [
  { number: 1, name: 'Strategy Setup', description: 'Name, period, and capital' },
  { number: 2, name: 'Stock Selection', description: 'Universe and sub-universe filters' },
  { number: 3, name: 'Entry & Position Sizing', description: 'Signals and allocation' },
  { number: 4, name: 'Entry Scheduling', description: 'Rebalancing frequency' },
  { number: 5, name: 'Exit Model', description: '4 exit modules' },
  { number: 6, name: 'Risk Management', description: 'Transaction costs' },
  { number: 7, name: 'Parameters', description: 'Benchmark and validation' },
  { number: 8, name: 'Review & Backtest', description: 'Review and execute' },
];

const StrategyWizard: React.FC = () => {
  const [currentStep, setCurrentStep] = useState(1);
  const [config, setConfig] = useState<StrategyConfig>({
    name: 'My Strategy',
    backtest_period: {
      start_date: '2013-01-01',
      end_date: '2023-12-31',
    },
    initial_capital: 1000000,
    universe_filters: {
      market_cap_min: 3000000000,
      index_membership: 'SP1500',
      lookback_quarters: 9,
    },
    sub_universe_filters: {
      selected_institutions: [],  // NEW: Will be populated in Step 2
      investor: {
        aum_min: 1000000000,
        track_record_quarters: 8,
        concentration_max: 0.35,
        turnover_max: 0.40,
      },
      transaction: {
        min_buy_value: 10000000,
        share_increase_min: 0.05,
      },
      insider: {
        roles: ['CEO', 'CFO', 'COO', 'President', 'Chairman'],
        value_min: 100000,
      },
    },
    entry_signals: {
      enable_doubling_down: true,
      enable_insider_buying: true,
      enable_herding: true,
      technical_confirmation: {
        price_breakout_days: 10,
        sma_period: 50,
        rsi_period: 14,
        rsi_threshold: 45,
      },
    },
    position_sizing: {
      method: 'static',
      percent_per_position: 0.05,
      min_positions: 5,
      max_positions: 20,
      rank_buffer: 5,
    },
    exit_rules: {
      enable_thesis_drift: true,
      enable_insider_reversal: true,
      enable_trailing_stop: true,
      trailing_stop_percent: 0.15,
      enable_dead_money: true,
      dead_money_quarters: 4,
    },
    transaction_costs: {
      commission_per_share: 0.005,
      slippage_bps: 25,
    },
    heartbeat: {
      rebalance_frequency: 'monthly',
    },
    enable_validation: true,
    validation_config: {
      walk_forward: true,
      monte_carlo: true,
      parameter_sensitivity: true,
      stress_test: true,
    },
  });

  // Load config from localStorage on mount
  useEffect(() => {
    const reloadedStrategy = localStorage.getItem('reloadStrategy');
    if (reloadedStrategy) {
      try {
        const parsedStrategy = JSON.parse(reloadedStrategy);
        setConfig(parsedStrategy);
        // Clear from localStorage after loading
        localStorage.removeItem('reloadStrategy');
        console.log('✅ Strategy reloaded from history');
      } catch (err) {
        console.error('Failed to parse reloaded strategy:', err);
      }
    } else {
      // Try to load saved config from localStorage
      const savedConfig = localStorage.getItem('strategyConfig');
      if (savedConfig) {
        try {
          const parsedConfig = JSON.parse(savedConfig);
          setConfig(parsedConfig);
          console.log('✅ Strategy config loaded from localStorage');
        } catch (err) {
          console.error('Failed to parse saved config:', err);
        }
      }
    }
  }, []);

  // Persist config to localStorage whenever it changes
  useEffect(() => {
    localStorage.setItem('strategyConfig', JSON.stringify(config));
    // Log institution selections for debugging
    if (config.sub_universe_filters?.selected_institutions) {
      console.log('📋 Institution selections saved:', config.sub_universe_filters.selected_institutions);
    }
  }, [config]);

  const nextStep = () => {
    if (currentStep < 8) {
      setCurrentStep(currentStep + 1);
    }
  };

  const prevStep = () => {
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1);
    }
  };

  const updateConfig = (updates: Partial<StrategyConfig>) => {
    setConfig((prev) => {
      const newConfig = { ...prev, ...updates };
      // Log when institution selections are updated
      if (updates.sub_universe_filters?.selected_institutions) {
        console.log('🔄 Institution selections updated:', updates.sub_universe_filters.selected_institutions);
      }
      return newConfig;
    });
  };

  const renderStep = () => {
    const commonProps = {
      config,
      updateConfig,
      nextStep,
      prevStep,
    };

    switch (currentStep) {
      case 1:
        return <Step1_Setup {...commonProps} />;
      case 2:
        return <Step2_StockSelection {...commonProps} />;
      case 3:
        return <Step3_EntryPositionSizing {...commonProps} />;
      case 4:
        return <Step4_EntryScheduling {...commonProps} />;
      case 5:
        return <Step5_ExitModel {...commonProps} />;
      case 6:
        return <Step6_RiskManagement {...commonProps} />;
      case 7:
        return <Step7_Parameters {...commonProps} />;
      case 8:
        return <Step8_ReviewBacktest {...commonProps} />;
      default:
        return null;
    }
  };

  return (
    <div className="bg-white rounded-lg shadow">
      {/* Progress Steps */}
      <div className="px-4 py-5 border-b border-gray-200 sm:px-6">
        <nav aria-label="Progress">
          <ol className="flex items-center justify-between">
            {steps.map((step, stepIdx) => (
              <li key={step.name} className="relative flex-1">
                {stepIdx !== steps.length - 1 && (
                  <div
                    className="absolute top-4 left-1/2 -ml-px mt-0.5 h-0.5 w-full bg-gray-300"
                    aria-hidden="true"
                  />
                )}
                <button
                  onClick={() => setCurrentStep(step.number)}
                  className="group relative flex flex-col items-center"
                >
                  <span
                    className={`relative z-10 flex h-8 w-8 items-center justify-center rounded-full ${
                      step.number === currentStep
                        ? 'bg-blue-600 text-white'
                        : step.number < currentStep
                        ? 'bg-blue-600 text-white'
                        : 'bg-white border-2 border-gray-300 text-gray-500'
                    }`}
                  >
                    {step.number < currentStep ? (
                      <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 20 20">
                        <path
                          fillRule="evenodd"
                          d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                          clipRule="evenodd"
                        />
                      </svg>
                    ) : (
                      <span className="text-sm font-semibold">{step.number}</span>
                    )}
                  </span>
                  <span className="mt-2 text-xs font-medium text-gray-900 text-center hidden md:block">
                    {step.name}
                  </span>
                </button>
              </li>
            ))}
          </ol>
        </nav>
      </div>

      {/* Step Content */}
      <div className="px-4 py-5 sm:p-6">{renderStep()}</div>
    </div>
  );
};

export default StrategyWizard;

