import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { StrategyConfig } from './StrategyWizard';
import BacktestProgressModal from './BacktestProgressModal';
import { apiClient } from '@/services/api';

interface Institution {
  cik: string;
  name: string;
  description: string;
  is_popular?: boolean;
  aum?: number;
}

// Tatvic-styled Collapsible Step Card Component
interface StepCardProps {
  number: number;
  title: string;
  icon: string;
  isExpanded: boolean;
  onToggle: () => void;
  children: React.ReactNode;
}

const StepCard: React.FC<StepCardProps> = ({ number, title, icon, isExpanded, onToggle, children }) => (
  <div className="bg-white rounded-lg shadow-tatvic-card hover:shadow-tatvic-card-hover overflow-hidden transition-all duration-300">
    <button
      onClick={onToggle}
      className="w-full flex items-center justify-between p-6 bg-tatvic-blue hover:bg-opacity-95 transition"
    >
      <div className="flex items-center gap-4">
        <div className="flex items-center justify-center w-12 h-12 rounded-full bg-white/10 backdrop-blur-sm border-2 border-white/20">
          <span className="text-xl font-bold text-white font-poppins">{number}</span>
        </div>
        <div className="text-left">
          <span className="text-3xl">{icon}</span>
          <h2 className="text-xl font-bold text-white mt-1 font-poppins">{title}</h2>
        </div>
      </div>
      <svg
        className={`w-6 h-6 text-white transition-transform ${isExpanded ? 'rotate-180' : ''}`}
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="3" d="M19 9l-7 7-7-7" />
      </svg>
    </button>
    {isExpanded && (
      <div className="p-6 bg-tatvic-background-alt">
        {children}
      </div>
    )}
  </div>
);

// Tatvic-styled Input Field Component
interface InputFieldProps {
  label: string;
  value: string | number;
  onChange: (value: string) => void;
  placeholder?: string;
  icon?: string;
  type?: string;
  min?: string | number;
  max?: string | number;
  step?: string | number;
}

const InputField: React.FC<InputFieldProps> = ({ label, value, onChange, placeholder, icon, type = 'text', min, max, step }) => (
  <div>
    <label className="block text-sm font-semibold text-tatvic-text-heading mb-2 flex items-center gap-2 font-poppins">
      {icon && <span>{icon}</span>}
      {label}
    </label>
    <input
      type={type}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      min={min}
      max={max}
      step={step}
      className="w-full px-4 py-3 border-2 border-gray-300 rounded-md focus:ring-2 focus:ring-tatvic-orange focus:border-transparent transition text-tatvic-text-body font-roboto"
    />
  </div>
);

// Tatvic-styled Checkbox Component
interface CheckboxFieldProps {
  label: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  icon?: string;
}

const CheckboxField: React.FC<CheckboxFieldProps> = ({ label, checked, onChange, icon }) => (
  <div className="flex items-center">
    <input
      type="checkbox"
      checked={checked}
      onChange={(e) => onChange(e.target.checked)}
      className="h-5 w-5 text-tatvic-orange focus:ring-tatvic-orange border-gray-300 rounded"
    />
    <label className="ml-3 text-sm font-medium text-tatvic-text-body font-roboto flex items-center gap-2">
      {icon && <span>{icon}</span>}
      {label}
    </label>
  </div>
);

const StrategyBuilderBeta: React.FC = () => {
  const { t } = useTranslation(['strategy', 'common']);
  const navigate = useNavigate();
  
  const [config, setConfig] = useState<StrategyConfig>({
    name: 'My Strategy',
    backtest_period: { start_date: '', end_date: '' },
    initial_capital: 1000000,
    max_positions: 10,
    engine_type: 'custom',
    universe_filters: { market_cap_min: 1000000000, index_membership: 'SP500', lookback_quarters: 4 },
    sub_universe_filters: { selected_institutions: [] },
    position_sizing: { method: 'equal_weight', percent_per_position: 5, max_position_size: 0.05, min_position_size: 0.03, max_positions: 20, min_positions: 5 },
    entry_rules: { timing: 'immediate', execution_delay: 1, entry_window_days: 5, technical_confirmation: true },
    exit_rules: { thesis_drift_enabled: true, insider_reversal_enabled: true, trailing_stop_enabled: true, trailing_stop_pct: 0.15, dead_money_enabled: true, dead_money_quarters: 4 },
    risk_management: { max_portfolio_drawdown: 0.20, sector_concentration_limit: 0.30, rebalancing_frequency: 'quarterly' },
    transaction_costs: { commission_per_share: 0.005, slippage_pct: 0.001 },
  });

  const [isRunning, setIsRunning] = useState(false);
  const [backtestId, setBacktestId] = useState<string | null>(null);
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set(['step1']));
  const [institutions, setInstitutions] = useState<Institution[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiClient.get('/api/v1/sec/institutions')
      .then(res => {
        const rawInstitutions = res.data || [];
        const normalizedMap = new Map<string, Institution>();
        
        rawInstitutions.forEach((inst: Institution) => {
          const normalizedCik = inst.cik.replace(/^0+/, '');
          const existing = normalizedMap.get(normalizedCik);
          if (!existing || inst.is_popular || (inst.aum && !existing.aum)) {
            normalizedMap.set(normalizedCik, { ...inst, cik: inst.cik });
          }
        });
        
        const uniqueInstitutions = Array.from(normalizedMap.values())
          .sort((a, b) => {
            if (a.is_popular && !b.is_popular) return -1;
            if (!a.is_popular && b.is_popular) return 1;
            return a.name.localeCompare(b.name);
          });
        
        setInstitutions(uniqueInstitutions);
        setLoading(false);
      })
      .catch(err => {
        console.error('Error fetching institutions:', err);
        setLoading(false);
      });
  }, []);

  const toggleSection = (section: string) => {
    const newExpanded = new Set(expandedSections);
    if (newExpanded.has(section)) {
      newExpanded.delete(section);
    } else {
      newExpanded.add(section);
    }
    setExpandedSections(newExpanded);
  };

  const updateConfig = (updates: Partial<StrategyConfig>) => {
    setConfig((prev) => ({ ...prev, ...updates }));
  };

  const toggleInstitution = (cik: string) => {
    const currentInstitutions = config.sub_universe_filters?.selected_institutions || [];
    const newSelection = currentInstitutions.includes(cik)
      ? currentInstitutions.filter(c => c !== cik)
      : [...currentInstitutions, cik];
    
    updateConfig({
      sub_universe_filters: {
        ...config.sub_universe_filters,
        selected_institutions: newSelection
      }
    });
  };

  const handleRunBacktest = async () => {
    if (!config.backtest_period?.start_date || !config.backtest_period?.end_date) {
      alert('Please set start and end dates');
      return;
    }
    if (!config.sub_universe_filters?.selected_institutions?.length) {
      alert('Please select at least one institution');
      return;
    }
    
    setIsRunning(true);
    try {
      const response = await fetch(`${import.meta.env.VITE_API_BASE_URL}/api/v1/backtest/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config),
      });
      const data = await response.json();
      setBacktestId(data.backtest_id);
    } catch (error) {
      console.error('Error starting backtest:', error);
      setIsRunning(false);
    }
  };

  const handleBacktestComplete = () => {
    setIsRunning(false);
    navigate('/my-strategies');
  };

  const selectedInstitutions = config.sub_universe_filters?.selected_institutions || [];

  return (
    <div className="min-h-screen bg-tatvic-background-alt">
      {/* Tatvic Brand Header */}
      <div className="bg-tatvic-blue shadow-lg sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-5">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-white flex items-center gap-3 font-poppins">
                <span className="text-4xl">✨</span>
                Strategy Builder
                <span className="text-xs font-bold px-3 py-1 bg-tatvic-orange text-white rounded-md">
                  BETA
                </span>
              </h1>
              <p className="text-white/90 text-sm mt-1 font-roboto">Build your institutional-grade investment strategy in 8 simple steps</p>
            </div>
            <button
              onClick={() => navigate('/builder')}
              className="text-sm text-white hover:text-white/80 flex items-center gap-2 bg-white/10 backdrop-blur-sm px-4 py-2 rounded-md border border-white/20 transition font-poppins"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
              </svg>
              Classic Builder
            </button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column - All 8 Steps */}
          <div className="lg:col-span-2 space-y-4">
            
            {/* Step 1: Strategy Setup */}
            <StepCard
              number={1}
              title="Strategy Setup"
              icon="🎯"
              isExpanded={expandedSections.has('step1')}
              onToggle={() => toggleSection('step1')}
            >
              <div className="space-y-4">
                <InputField
                  label="Strategy Name"
                  value={config.name}
                  onChange={(val) => updateConfig({ name: val })}
                  placeholder="My Institutional Strategy"
                  icon="📝"
                />
                <div className="grid grid-cols-2 gap-4">
                  <InputField
                    label="Start Date"
                    type="date"
                    value={config.backtest_period?.start_date || ''}
                    onChange={(val) =>
                      updateConfig({
                        backtest_period: {
                          start_date: val,
                          end_date: config.backtest_period?.end_date || '',
                        },
                      })
                    }
                    icon="📅"
                  />
                  <InputField
                    label="End Date"
                    type="date"
                    value={config.backtest_period?.end_date || ''}
                    onChange={(val) =>
                      updateConfig({
                        backtest_period: {
                          start_date: config.backtest_period?.start_date || '',
                          end_date: val,
                        },
                      })
                    }
                    icon="📅"
                  />
                </div>
                <InputField
                  label="Initial Capital ($)"
                  type="number"
                  value={config.initial_capital}
                  onChange={(val) => updateConfig({ initial_capital: parseFloat(val) })}
                  min="10000"
                  step="10000"
                  icon="💰"
                />
                <InputField
                  label="Max Positions"
                  type="number"
                  value={config.max_positions || 10}
                  onChange={(val) => updateConfig({ max_positions: parseInt(val) })}
                  min="5"
                  max="20"
                  step="1"
                  icon="📊"
                />
                
                {/* Engine Selection */}
                <div className="bg-white p-4 rounded-md shadow-tatvic-card">
                  <label className="block text-sm font-semibold text-tatvic-text-heading mb-3 flex items-center gap-2 font-poppins">
                    🚀 Backtesting Engine
                  </label>
                  <div className="space-y-3">
                    <label className="flex items-start cursor-pointer group">
                      <input
                        type="radio"
                        name="engine"
                        value="custom"
                        checked={config.engine_type === 'custom' || !config.engine_type}
                        onChange={() => updateConfig({ engine_type: 'custom' })}
                        className="mt-1 h-4 w-4 text-tatvic-orange focus:ring-tatvic-orange"
                      />
                      <div className="ml-3">
                        <div className="text-sm font-medium text-tatvic-text-heading font-poppins">
                          Custom Engine <span className="text-xs bg-green-100 text-green-800 px-2 py-0.5 rounded">Recommended</span>
                        </div>
                        <div className="text-xs text-tatvic-text-body mt-0.5 font-roboto">
                          Fast, optimized for institutional signals
                        </div>
                      </div>
                    </label>
                    <label className="flex items-start cursor-pointer group">
                      <input
                        type="radio"
                        name="engine"
                        value="backtrader"
                        checked={config.engine_type === 'backtrader'}
                        onChange={() => updateConfig({ engine_type: 'backtrader' })}
                        className="mt-1 h-4 w-4 text-tatvic-orange focus:ring-tatvic-orange"
                      />
                      <div className="ml-3">
                        <div className="text-sm font-medium text-tatvic-text-heading font-poppins">
                          Backtrader <span className="text-xs bg-blue-100 text-blue-800 px-2 py-0.5 rounded">Advanced</span>
                        </div>
                        <div className="text-xs text-tatvic-text-body mt-0.5 font-roboto">
                          Industry-standard backtesting framework
                        </div>
                      </div>
                    </label>
                  </div>
                </div>
              </div>
            </StepCard>

            {/* Step 2: Stock Selection */}
            <StepCard
              number={2}
              title="Stock Selection"
              icon="🏦"
              isExpanded={expandedSections.has('step2')}
              onToggle={() => toggleSection('step2')}
            >
              <div className="space-y-4">
                <InputField
                  label="Market Cap Minimum ($)"
                  type="number"
                  value={config.universe_filters?.market_cap_min || 1000000000}
                  onChange={(val) => updateConfig({
                    universe_filters: {
                      ...config.universe_filters,
                      market_cap_min: parseFloat(val),
                    },
                  })}
                  min="100000000"
                  step="100000000"
                  icon="📈"
                />
                <InputField
                  label="Lookback Quarters"
                  type="number"
                  value={config.universe_filters?.lookback_quarters || 4}
                  onChange={(val) => updateConfig({
                    universe_filters: {
                      ...config.universe_filters,
                      lookback_quarters: parseInt(val),
                    },
                  })}
                  min="1"
                  max="10"
                  step="1"
                  icon="🗓️"
                />
                
                {/* Institution Selection */}
                <div className="bg-white p-4 rounded-md shadow-tatvic-card">
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="text-sm font-semibold text-tatvic-text-heading flex items-center gap-2 font-poppins">
                      🏢 Select Institutions ({selectedInstitutions.length} selected)
                    </h3>
                    <button
                      onClick={() => updateConfig({ sub_universe_filters: { ...config.sub_universe_filters, selected_institutions: [] } })}
                      className="text-xs text-tatvic-orange hover:text-tatvic-orange-dark font-poppins"
                    >
                      Clear All
                    </button>
                  </div>
                  {loading ? (
                    <div className="text-center py-4">
                      <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-tatvic-orange mx-auto"></div>
                      <p className="mt-2 text-sm text-tatvic-text-body font-roboto">Loading institutions...</p>
                    </div>
                  ) : (
                    <div className="max-h-60 overflow-y-auto border border-gray-200 rounded-md p-2 space-y-2">
                      {institutions.map((inst) => (
                        <label key={inst.cik} className="flex items-center cursor-pointer p-2 hover:bg-tatvic-background-alt rounded-md transition">
                          <input
                            type="checkbox"
                            checked={selectedInstitutions.includes(inst.cik)}
                            onChange={() => toggleInstitution(inst.cik)}
                            className="h-4 w-4 text-tatvic-orange focus:ring-tatvic-orange border-gray-300 rounded"
                          />
                          <span className="ml-3 text-sm font-medium text-tatvic-text-body font-roboto">{inst.name}</span>
                          {inst.is_popular && (
                            <span className="ml-2 px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                              Popular
                            </span>
                          )}
                        </label>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </StepCard>

            {/* Step 3: Entry & Position Sizing */}
            <StepCard
              number={3}
              title="Entry & Position Sizing"
              icon="📈"
              isExpanded={expandedSections.has('step3')}
              onToggle={() => toggleSection('step3')}
            >
              <div className="space-y-4">
                <InputField
                  label="Percent per Position (%)"
                  type="number"
                  value={(config.position_sizing?.max_position_size || 0.05) * 100}
                  onChange={(val) => updateConfig({
                    position_sizing: {
                      ...config.position_sizing,
                      max_position_size: parseFloat(val) / 100,
                    },
                  })}
                  min="1"
                  max="100"
                  step="1"
                  icon="⚖️"
                />
              </div>
            </StepCard>

            {/* Step 4: Entry Scheduling */}
            <StepCard
              number={4}
              title="Entry Scheduling"
              icon="⏰"
              isExpanded={expandedSections.has('step4')}
              onToggle={() => toggleSection('step4')}
            >
              <div className="space-y-4">
                <InputField
                  label="Execution Delay (days)"
                  type="number"
                  value={config.entry_rules?.execution_delay || 1}
                  onChange={(val) => updateConfig({
                    entry_rules: {
                      ...config.entry_rules,
                      execution_delay: parseInt(val),
                    },
                  })}
                  min="0"
                  max="5"
                  step="1"
                  icon="⏳"
                />
                <CheckboxField
                  label="Enable Technical Confirmation"
                  checked={config.entry_rules?.technical_confirmation || false}
                  onChange={(checked) => updateConfig({
                    entry_rules: {
                      ...config.entry_rules,
                      technical_confirmation: checked,
                    },
                  })}
                  icon="⚙️"
                />
              </div>
            </StepCard>

            {/* Step 5: Exit Model */}
            <StepCard
              number={5}
              title="Exit Model"
              icon="🚪"
              isExpanded={expandedSections.has('step5')}
              onToggle={() => toggleSection('step5')}
            >
              <div className="space-y-4">
                <div className="bg-white p-4 rounded-md shadow-tatvic-card space-y-3">
                  <CheckboxField
                    label="Thesis Drift Detection"
                    checked={config.exit_rules?.thesis_drift_enabled || false}
                    onChange={(checked) => updateConfig({
                      exit_rules: {
                        ...config.exit_rules,
                        thesis_drift_enabled: checked,
                      },
                    })}
                    icon="📉"
                  />
                  <CheckboxField
                    label="Insider Reversal Detection"
                    checked={config.exit_rules?.insider_reversal_enabled || false}
                    onChange={(checked) => updateConfig({
                      exit_rules: {
                        ...config.exit_rules,
                        insider_reversal_enabled: checked,
                      },
                    })}
                    icon="🕵️"
                  />
                  <CheckboxField
                    label="Trailing Stop Loss"
                    checked={config.exit_rules?.trailing_stop_enabled || false}
                    onChange={(checked) => updateConfig({
                      exit_rules: {
                        ...config.exit_rules,
                        trailing_stop_enabled: checked,
                      },
                    })}
                    icon="🛑"
                  />
                  {config.exit_rules?.trailing_stop_enabled && (
                    <div className="ml-8">
                      <InputField
                        label="Trailing Stop %"
                        type="number"
                        value={(config.exit_rules?.trailing_stop_pct || 0.15) * 100}
                        onChange={(val) => updateConfig({
                          exit_rules: {
                            ...config.exit_rules,
                            trailing_stop_pct: parseFloat(val) / 100,
                          },
                        })}
                        min="1"
                        max="50"
                        step="1"
                      />
                    </div>
                  )}
                  <CheckboxField
                    label="Dead Money Rule"
                    checked={config.exit_rules?.dead_money_enabled || false}
                    onChange={(checked) => updateConfig({
                      exit_rules: {
                        ...config.exit_rules,
                        dead_money_enabled: checked,
                      },
                    })}
                    icon="💀"
                  />
                  {config.exit_rules?.dead_money_enabled && (
                    <div className="ml-8 space-y-3">
                      <InputField
                        label="Dead Money Quarters"
                        type="number"
                        value={config.exit_rules?.dead_money_quarters || 4}
                        onChange={(val) => updateConfig({
                          exit_rules: {
                            ...config.exit_rules,
                            dead_money_quarters: parseInt(val),
                          },
                        })}
                        min="1"
                        max="8"
                        step="1"
                      />
                    </div>
                  )}
                </div>
              </div>
            </StepCard>

            {/* Step 6: Risk Management */}
            <StepCard
              number={6}
              title="Risk Management"
              icon="🛡️"
              isExpanded={expandedSections.has('step6')}
              onToggle={() => toggleSection('step6')}
            >
              <div className="space-y-4">
                <InputField
                  label="Max Portfolio Drawdown (%)"
                  type="number"
                  value={(config.risk_management?.max_portfolio_drawdown || 0.20) * 100}
                  onChange={(val) => updateConfig({
                    risk_management: {
                      ...config.risk_management,
                      max_portfolio_drawdown: parseFloat(val) / 100,
                    },
                  })}
                  min="5"
                  max="50"
                  step="1"
                  icon="📉"
                />
                <InputField
                  label="Max Sector Exposure (%)"
                  type="number"
                  value={(config.risk_management?.sector_concentration_limit || 0.30) * 100}
                  onChange={(val) => updateConfig({
                    risk_management: {
                      ...config.risk_management,
                      sector_concentration_limit: parseFloat(val) / 100,
                    },
                  })}
                  min="10"
                  max="100"
                  step="5"
                  icon="📊"
                />
                <div>
                  <label className="block text-sm font-semibold text-tatvic-text-heading mb-2 flex items-center gap-2 font-poppins">
                    🔄 Rebalance Frequency
                  </label>
                  <select
                    value={config.risk_management?.rebalancing_frequency || 'quarterly'}
                    onChange={(e) => updateConfig({
                      risk_management: {
                        ...config.risk_management,
                        rebalancing_frequency: e.target.value as any,
                      },
                    })}
                    className="w-full px-4 py-3 border-2 border-gray-300 rounded-md focus:ring-2 focus:ring-tatvic-orange focus:border-transparent transition text-tatvic-text-body font-roboto"
                  >
                    <option value="never">Never</option>
                    <option value="weekly">Weekly</option>
                    <option value="monthly">Monthly</option>
                    <option value="quarterly">Quarterly</option>
                  </select>
                </div>
              </div>
            </StepCard>

            {/* Step 7: Transaction Costs */}
            <StepCard
              number={7}
              title="Transaction Costs"
              icon="💰"
              isExpanded={expandedSections.has('step7')}
              onToggle={() => toggleSection('step7')}
            >
              <div className="space-y-4">
                <InputField
                  label="Commission per Share ($)"
                  type="number"
                  value={config.transaction_costs?.commission_per_share || 0.005}
                  onChange={(val) => updateConfig({
                    transaction_costs: {
                      ...config.transaction_costs,
                      commission_per_share: parseFloat(val),
                    },
                  })}
                  min="0"
                  step="0.001"
                  icon="💲"
                />
                <InputField
                  label="Slippage (%)"
                  type="number"
                  value={(config.transaction_costs?.slippage_pct || 0.001) * 100}
                  onChange={(val) => updateConfig({
                    transaction_costs: {
                      ...config.transaction_costs,
                      slippage_pct: parseFloat(val) / 100,
                    },
                  })}
                  min="0"
                  max="1"
                  step="0.01"
                  icon="📉"
                />
              </div>
            </StepCard>

            {/* Step 8: Review & Run */}
            <StepCard
              number={8}
              title="Review & Run"
              icon="🚀"
              isExpanded={expandedSections.has('step8')}
              onToggle={() => toggleSection('step8')}
            >
              <div className="space-y-4">
                <div className="bg-white p-4 rounded-md shadow-tatvic-card">
                  <h3 className="text-lg font-semibold text-tatvic-text-heading mb-3 font-poppins">Configuration Summary</h3>
                  <div className="space-y-2 text-sm text-tatvic-text-body font-roboto">
                    <p><strong>Strategy:</strong> {config.name}</p>
                    <p><strong>Period:</strong> {config.backtest_period?.start_date} to {config.backtest_period?.end_date}</p>
                    <p><strong>Capital:</strong> ${config.initial_capital?.toLocaleString()}</p>
                    <p><strong>Max Positions:</strong> {config.max_positions}</p>
                    <p><strong>Institutions:</strong> {selectedInstitutions.length}</p>
                    <p><strong>Engine:</strong> {config.engine_type === 'custom' ? 'Custom' : 'Backtrader'}</p>
                  </div>
                </div>
              </div>
            </StepCard>

          </div>

          {/* Right Column - Quick Summary & CTA */}
          <div className="lg:col-span-1">
            <div className="sticky top-24 bg-white rounded-lg shadow-tatvic-card p-6">
              <h2 className="text-2xl font-bold text-tatvic-text-heading mb-4 font-poppins">
                ✨ Quick Summary
              </h2>
              <ul className="space-y-3 text-sm text-tatvic-text-body font-roboto mb-6">
                <li><strong className="text-tatvic-text-heading">Name:</strong> {config.name}</li>
                <li><strong className="text-tatvic-text-heading">Period:</strong> {config.backtest_period?.start_date || 'Not set'} to {config.backtest_period?.end_date || 'Not set'}</li>
                <li><strong className="text-tatvic-text-heading">Capital:</strong> ${config.initial_capital?.toLocaleString()}</li>
                <li><strong className="text-tatvic-text-heading">Max Positions:</strong> {config.max_positions}</li>
                <li><strong className="text-tatvic-text-heading">Engine:</strong> {config.engine_type === 'custom' ? 'Custom' : config.engine_type === 'backtrader' ? 'Backtrader' : 'LEAN'}</li>
                <li><strong className="text-tatvic-text-heading">Institutions:</strong> {selectedInstitutions.length}</li>
              </ul>

              {/* Tatvic CTA Button */}
              <button
                onClick={handleRunBacktest}
                disabled={isRunning}
                className="w-full flex items-center justify-center px-6 py-3 border border-transparent text-base font-semibold rounded-md text-white bg-tatvic-orange hover:bg-tatvic-orange-dark transition-all shadow-md hover:shadow-lg disabled:opacity-50 disabled:cursor-not-allowed font-poppins"
              >
                {isRunning ? (
                  <>
                    <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Running...
                  </>
                ) : (
                  <>
                    <span className="text-xl mr-2">🚀</span>
                    Run Backtest
                  </>
                )}
              </button>
              <p className="mt-3 text-center text-sm text-tatvic-text-body font-roboto">
                ⏱️ Est. time: ~{Math.ceil((config.max_positions || 10) * 12 / 60)} min
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Progress Modal - Only show when backtest is running */}
      {isRunning && backtestId && (
        <BacktestProgressModal
          backtestId={backtestId}
          onComplete={handleBacktestComplete}
          onClose={handleBacktestComplete}
        />
      )}
    </div>
  );
};

export default StrategyBuilderBeta;
