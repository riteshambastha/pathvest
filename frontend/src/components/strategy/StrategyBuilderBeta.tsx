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

const StrategyBuilderBeta: React.FC = () => {
  const { t } = useTranslation(['strategy', 'common']);
  const navigate = useNavigate();
  
  const [config, setConfig] = useState<StrategyConfig>({
    name: 'My Strategy',
    backtest_period: { start_date: '', end_date: '' },
    initial_capital: 1000000,
    max_positions: 10,
    engine_type: 'custom',
    sub_universe_filters: { selected_institutions: [], market_cap_min: 1000000000, lookback_quarters: 4 },
    position_sizing: { method: 'equal_weight', percent_per_position: 5, max_position_size: 0.05, min_position_size: 0.03, max_positions: 20, min_positions: 5 },
    entry_rules: { timing: 'immediate', execution_delay: 1, entry_window_days: 5, technical_confirmation: true },
    exit_rules: { thesis_drift_enabled: true, insider_reversal_enabled: true, trailing_stop_enabled: true, trailing_stop_pct: 0.15, dead_money_enabled: true, dead_money_quarters: 4 },
    risk_management: { max_portfolio_drawdown: 0.20, max_sector_exposure: 0.30, rebalance_frequency: 'quarterly' },
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
    <div className="min-h-screen bg-gradient-to-br from-purple-50 via-pink-50 to-orange-50">
      {/* Header */}
      <div className="bg-gradient-to-r from-purple-600 via-pink-600 to-orange-500 shadow-lg sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-5">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-white flex items-center gap-3">
                <span className="text-4xl">✨</span>
                Strategy Builder
                <span className="text-xs font-bold px-3 py-1 bg-white/20 backdrop-blur-sm text-white rounded-full border border-white/30">
                  BETA
                </span>
              </h1>
              <p className="text-white/90 text-sm mt-1">Build your institutional-grade investment strategy in 8 simple steps</p>
            </div>
            <button
              onClick={() => navigate('/builder')}
              className="text-sm text-white/90 hover:text-white flex items-center gap-2 bg-white/10 backdrop-blur-sm px-4 py-2 rounded-lg border border-white/20 transition"
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
              gradient="from-blue-500 to-cyan-500"
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
                  icon="💰"
                />
                <InputField
                  label="Max Positions"
                  type="number"
                  value={config.max_positions || 10}
                  onChange={(val) => updateConfig({ max_positions: parseInt(val) })}
                  min={5}
                  max={20}
                  icon="📊"
                />
                
                {/* Engine Selection */}
                <div className="pt-4 border-t border-gray-200">
                  <label className="block text-sm font-semibold text-gray-900 mb-3">Backtesting Engine</label>
                  <div className="space-y-2">
                    <EngineOption
                      name="Custom Engine"
                      tag="Fast"
                      tagColor="green"
                      description="Optimized for PathVest • Real data • 2-3 min"
                      selected={config.engine_type === 'custom'}
                      onSelect={() => updateConfig({ engine_type: 'custom' })}
                    />
                    <EngineOption
                      name="Backtrader"
                      tag="New"
                      tagColor="orange"
                      description="Industry-standard • YFinance • Full ecosystem"
                      selected={config.engine_type === 'backtrader'}
                      onSelect={() => updateConfig({ engine_type: 'backtrader' })}
                    />
                  </div>
                </div>
              </div>
            </StepCard>

            {/* Step 2: Stock Selection */}
            <StepCard
              number={2}
              title="Stock Selection"
              icon="🏦"
              gradient="from-green-500 to-emerald-500"
              isExpanded={expandedSections.has('step2')}
              onToggle={() => toggleSection('step2')}
            >
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <InputField
                    label="Market Cap Min ($)"
                    type="number"
                    value={config.sub_universe_filters?.market_cap_min || 1000000000}
                    onChange={(val) => updateConfig({
                      sub_universe_filters: { ...config.sub_universe_filters, market_cap_min: parseFloat(val) }
                    })}
                    icon="💵"
                  />
                  <InputField
                    label="Lookback Quarters"
                    type="number"
                    value={config.sub_universe_filters?.lookback_quarters || 4}
                    onChange={(val) => updateConfig({
                      sub_universe_filters: { ...config.sub_universe_filters, lookback_quarters: parseInt(val) }
                    })}
                    min={1}
                    max={8}
                    icon="📆"
                  />
                </div>

                {/* Institution Selection */}
                <div className="pt-4 border-t border-gray-200">
                  <div className="flex justify-between items-center mb-3">
                    <label className="block text-sm font-semibold text-gray-900">
                      Select Institutions ({selectedInstitutions.length} selected)
                    </label>
                    {selectedInstitutions.length > 0 && (
                      <button
                        onClick={() => updateConfig({ sub_universe_filters: { ...config.sub_universe_filters, selected_institutions: [] } })}
                        className="text-xs text-red-600 hover:text-red-700"
                      >
                        Clear all
                      </button>
                    )}
                  </div>
                  {loading ? (
                    <div className="text-center py-8">
                      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-green-600 mx-auto"></div>
                      <p className="mt-2 text-sm text-gray-600">Loading institutions...</p>
                    </div>
                  ) : (
                    <div className="max-h-96 overflow-y-auto space-y-2 pr-2">
                      {institutions.map((inst) => (
                        <button
                          key={inst.cik}
                          onClick={() => toggleInstitution(inst.cik)}
                          className={`w-full flex items-center gap-3 p-3 rounded-lg border-2 transition text-left ${
                            selectedInstitutions.includes(inst.cik)
                              ? 'border-green-500 bg-green-50 shadow-sm'
                              : 'border-gray-200 hover:border-green-300 bg-white'
                          }`}
                        >
                          <input
                            type="checkbox"
                            checked={selectedInstitutions.includes(inst.cik)}
                            onChange={() => {}}
                            className="h-4 w-4 text-green-600 rounded"
                          />
                          <div className="flex-1 min-w-0">
                            <div className="text-sm font-semibold text-gray-900 truncate">{inst.name}</div>
                            <div className="text-xs text-gray-600 truncate">{inst.description}</div>
                          </div>
                        </button>
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
              gradient="from-purple-500 to-indigo-500"
              isExpanded={expandedSections.has('step3')}
              onToggle={() => toggleSection('step3')}
            >
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-semibold text-gray-900 mb-3">Position Sizing Method</label>
                  <RadioOption
                    label="Equal Weight"
                    description="Allocate equal capital to each position"
                    selected={config.position_sizing?.method === 'equal_weight'}
                    onSelect={() => updateConfig({ position_sizing: { ...config.position_sizing, method: 'equal_weight' } })}
                  />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <InputField
                    label="Percent per Position (%)"
                    type="number"
                    value={config.position_sizing?.percent_per_position || 5}
                    onChange={(val) => updateConfig({ position_sizing: { ...config.position_sizing, percent_per_position: parseFloat(val) } })}
                    min={1}
                    max={20}
                    icon="📊"
                  />
                  <InputField
                    label="Max Position Size (%)"
                    type="number"
                    value={(config.position_sizing?.max_position_size || 0.05) * 100}
                    onChange={(val) => updateConfig({ position_sizing: { ...config.position_sizing, max_position_size: parseFloat(val) / 100 } })}
                    min={1}
                    max={20}
                    icon="⬆️"
                  />
                </div>
              </div>
            </StepCard>

            {/* Step 4: Entry Scheduling */}
            <StepCard
              number={4}
              title="Entry Scheduling"
              icon="⏰"
              gradient="from-orange-500 to-red-500"
              isExpanded={expandedSections.has('step4')}
              onToggle={() => toggleSection('step4')}
            >
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-semibold text-gray-900 mb-3">Entry Timing</label>
                  <RadioOption
                    label="Immediate (T+1)"
                    description="Enter at market open next trading day"
                    selected={config.entry_rules?.timing === 'immediate'}
                    onSelect={() => updateConfig({ entry_rules: { ...config.entry_rules, timing: 'immediate' } })}
                  />
                </div>
                <InputField
                  label="Execution Delay (days)"
                  type="number"
                  value={config.entry_rules?.execution_delay || 1}
                  onChange={(val) => updateConfig({ entry_rules: { ...config.entry_rules, execution_delay: parseInt(val) } })}
                  min={1}
                  max={5}
                  icon="⏱️"
                />
                <CheckboxOption
                  label="Technical Confirmation"
                  description="Require technical indicators confirmation before entry"
                  checked={config.entry_rules?.technical_confirmation || false}
                  onChange={(val) => updateConfig({ entry_rules: { ...config.entry_rules, technical_confirmation: val } })}
                />
              </div>
            </StepCard>

            {/* Step 5: Exit Model */}
            <StepCard
              number={5}
              title="Exit Model"
              icon="🚪"
              gradient="from-pink-500 to-rose-500"
              isExpanded={expandedSections.has('step5')}
              onToggle={() => toggleSection('step5')}
            >
              <div className="space-y-4">
                <CheckboxOption
                  label="Thesis Drift Detection"
                  description="Exit if institutional position is reduced >50%"
                  checked={config.exit_rules?.thesis_drift_enabled || false}
                  onChange={(val) => updateConfig({ exit_rules: { ...config.exit_rules, thesis_drift_enabled: val } })}
                />
                <CheckboxOption
                  label="Insider Reversal"
                  description="Exit on significant insider selling"
                  checked={config.exit_rules?.insider_reversal_enabled || false}
                  onChange={(val) => updateConfig({ exit_rules: { ...config.exit_rules, insider_reversal_enabled: val } })}
                />
                <CheckboxOption
                  label="Trailing Stop"
                  description="Protect profits with trailing stop"
                  checked={config.exit_rules?.trailing_stop_enabled || false}
                  onChange={(val) => updateConfig({ exit_rules: { ...config.exit_rules, trailing_stop_enabled: val } })}
                />
                {config.exit_rules?.trailing_stop_enabled && (
                  <InputField
                    label="Trailing Stop (%)"
                    type="number"
                    value={(config.exit_rules?.trailing_stop_pct || 0.15) * 100}
                    onChange={(val) => updateConfig({ exit_rules: { ...config.exit_rules, trailing_stop_pct: parseFloat(val) / 100 } })}
                    min={5}
                    max={30}
                    icon="📉"
                  />
                )}
                <CheckboxOption
                  label="Dead Money Rule"
                  description="Exit positions with no movement"
                  checked={config.exit_rules?.dead_money_enabled || false}
                  onChange={(val) => updateConfig({ exit_rules: { ...config.exit_rules, dead_money_enabled: val } })}
                />
              </div>
            </StepCard>

            {/* Step 6: Risk Management */}
            <StepCard
              number={6}
              title="Risk Management"
              icon="🛡️"
              gradient="from-cyan-500 to-blue-500"
              isExpanded={expandedSections.has('step6')}
              onToggle={() => toggleSection('step6')}
            >
              <div className="space-y-4">
                <InputField
                  label="Max Portfolio Drawdown (%)"
                  type="number"
                  value={(config.risk_management?.max_portfolio_drawdown || 0.20) * 100}
                  onChange={(val) => updateConfig({ risk_management: { ...config.risk_management, max_portfolio_drawdown: parseFloat(val) / 100 } })}
                  min={5}
                  max={50}
                  icon="⚠️"
                />
                <InputField
                  label="Max Sector Exposure (%)"
                  type="number"
                  value={(config.risk_management?.max_sector_exposure || 0.30) * 100}
                  onChange={(val) => updateConfig({ risk_management: { ...config.risk_management, max_sector_exposure: parseFloat(val) / 100 } })}
                  min={10}
                  max={50}
                  icon="🏭"
                />
                <div>
                  <label className="block text-sm font-semibold text-gray-900 mb-3">Rebalance Frequency</label>
                  <RadioOption
                    label="Quarterly"
                    description="Rebalance every 3 months"
                    selected={config.risk_management?.rebalance_frequency === 'quarterly'}
                    onSelect={() => updateConfig({ risk_management: { ...config.risk_management, rebalance_frequency: 'quarterly' } })}
                  />
                </div>
              </div>
            </StepCard>

            {/* Step 7: Transaction Costs */}
            <StepCard
              number={7}
              title="Transaction Costs"
              icon="💸"
              gradient="from-yellow-500 to-amber-500"
              isExpanded={expandedSections.has('step7')}
              onToggle={() => toggleSection('step7')}
            >
              <div className="space-y-4">
                <InputField
                  label="Commission per Share ($)"
                  type="number"
                  value={config.transaction_costs?.commission_per_share || 0.005}
                  onChange={(val) => updateConfig({ transaction_costs: { ...config.transaction_costs, commission_per_share: parseFloat(val) } })}
                  step={0.001}
                  icon="💵"
                />
                <InputField
                  label="Slippage (%)"
                  type="number"
                  value={(config.transaction_costs?.slippage_pct || 0.001) * 100}
                  onChange={(val) => updateConfig({ transaction_costs: { ...config.transaction_costs, slippage_pct: parseFloat(val) / 100 } })}
                  step={0.01}
                  icon="📊"
                />
              </div>
            </StepCard>

            {/* Step 8: Review */}
            <StepCard
              number={8}
              title="Review & Run"
              icon="🚀"
              gradient="from-indigo-500 to-purple-600"
              isExpanded={expandedSections.has('step8')}
              onToggle={() => toggleSection('step8')}
            >
              <div className="space-y-4">
                <div className="bg-gradient-to-r from-indigo-50 to-purple-50 p-4 rounded-lg border border-indigo-200">
                  <h4 className="font-semibold text-gray-900 mb-2">✅ Configuration Summary</h4>
                  <div className="space-y-1 text-sm text-gray-700">
                    <p>• <strong>Period:</strong> {config.backtest_period?.start_date} to {config.backtest_period?.end_date}</p>
                    <p>• <strong>Capital:</strong> ${config.initial_capital.toLocaleString()}</p>
                    <p>• <strong>Institutions:</strong> {selectedInstitutions.length} selected</p>
                    <p>• <strong>Max Positions:</strong> {config.max_positions}</p>
                    <p>• <strong>Engine:</strong> {config.engine_type}</p>
                  </div>
                </div>
              </div>
            </StepCard>
          </div>

          {/* Right Column - Summary & Actions */}
          <div className="lg:col-span-1">
            <div className="bg-gradient-to-br from-white to-gray-50 rounded-2xl shadow-xl border-2 border-gray-200 p-6 sticky top-28">
              <div className="flex items-center gap-2 mb-4">
                <span className="text-2xl">📋</span>
                <h3 className="text-xl font-bold text-gray-900">Quick Summary</h3>
              </div>
              <div className="space-y-3 mb-6">
                <SummaryItem icon="🎯" label="Strategy" value={config.name} />
                <SummaryItem
                  icon="📅"
                  label="Period"
                  value={
                    config.backtest_period?.start_date && config.backtest_period?.end_date
                      ? `${config.backtest_period.start_date} to ${config.backtest_period.end_date}`
                      : 'Not set'
                  }
                />
                <SummaryItem icon="💰" label="Capital" value={`$${config.initial_capital.toLocaleString()}`} />
                <SummaryItem icon="🏦" label="Institutions" value={selectedInstitutions.length} />
                <SummaryItem icon="📊" label="Max Positions" value={config.max_positions || 10} />
                <SummaryItem icon="🚀" label="Engine" value={config.engine_type || 'custom'} />
              </div>

              <button
                onClick={handleRunBacktest}
                disabled={isRunning || !config.backtest_period?.start_date || !config.backtest_period?.end_date || selectedInstitutions.length === 0}
                className="w-full bg-gradient-to-r from-purple-600 via-pink-600 to-orange-500 text-white py-4 px-6 rounded-xl font-bold text-lg hover:shadow-2xl transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-3 transform hover:scale-105"
              >
                {isRunning ? (
                  <>
                    <svg className="animate-spin h-6 w-6" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path
                        className="opacity-75"
                        fill="currentColor"
                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                      />
                    </svg>
                    Running...
                  </>
                ) : (
                  <>
                    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    Run Backtest
                  </>
                )}
              </button>

              <p className="text-xs text-gray-500 text-center mt-3">
                ⏱️ Est. time: ~{Math.ceil((config.max_positions || 10) * 0.2)} minutes
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Progress Modal */}
      {isRunning && backtestId && (
        <BacktestProgressModal
          backtestId={backtestId}
          onComplete={handleBacktestComplete}
          onClose={() => setIsRunning(false)}
        />
      )}
    </div>
  );
};

// Helper Components
const StepCard: React.FC<{
  number: number;
  title: string;
  icon: string;
  gradient: string;
  isExpanded: boolean;
  onToggle: () => void;
  children: React.ReactNode;
}> = ({ number, title, icon, gradient, isExpanded, onToggle, children }) => (
  <div className="bg-white rounded-2xl shadow-lg border-2 border-gray-200 overflow-hidden transition-all hover:shadow-xl">
    <button
      onClick={onToggle}
      className={`w-full flex items-center justify-between p-6 bg-gradient-to-r ${gradient} hover:opacity-90 transition`}
    >
      <div className="flex items-center gap-4">
        <div className="flex items-center justify-center w-12 h-12 rounded-full bg-white/20 backdrop-blur-sm border-2 border-white/30">
          <span className="text-xl font-bold text-white">{number}</span>
        </div>
        <div className="text-left">
          <span className="text-3xl">{icon}</span>
          <h2 className="text-xl font-bold text-white mt-1">{title}</h2>
        </div>
      </div>
      <svg
        className={`w-6 h-6 text-white transition-transform ${isExpanded ? 'rotate-180' : ''}`}
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M19 9l-7 7-7-7" />
      </svg>
    </button>
    {isExpanded && <div className="p-6">{children}</div>}
  </div>
);

const InputField: React.FC<{
  label: string;
  value: string | number;
  onChange: (value: string) => void;
  type?: string;
  placeholder?: string;
  min?: number;
  max?: number;
  step?: number;
  icon?: string;
}> = ({ label, value, onChange, type = 'text', placeholder, min, max, step, icon }) => (
  <div>
    <label className="block text-sm font-semibold text-gray-900 mb-2 flex items-center gap-2">
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
      className="w-full px-4 py-3 border-2 border-gray-300 rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-transparent transition text-gray-900 font-medium"
    />
  </div>
);

const EngineOption: React.FC<{
  name: string;
  tag: string;
  tagColor: 'green' | 'orange' | 'purple';
  description: string;
  selected: boolean;
  onSelect: () => void;
}> = ({ name, tag, tagColor, description, selected, onSelect }) => {
  const tagColors = {
    green: 'bg-green-100 text-green-700',
    orange: 'bg-orange-100 text-orange-700',
    purple: 'bg-purple-100 text-purple-700',
  };

  return (
    <button
      onClick={onSelect}
      className={`w-full flex items-center gap-3 p-4 rounded-xl border-2 transition text-left ${
        selected ? 'border-purple-500 bg-purple-50 shadow-md' : 'border-gray-200 hover:border-purple-300'
      }`}
    >
      <div
        className={`w-5 h-5 rounded-full border-2 flex items-center justify-center flex-shrink-0 ${
          selected ? 'border-purple-500 bg-purple-500' : 'border-gray-300'
        }`}
      >
        {selected && (
          <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
            <path
              fillRule="evenodd"
              d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
              clipRule="evenodd"
            />
          </svg>
        )}
      </div>
      <div className="flex-1">
        <div className="flex items-center gap-2 mb-1">
          <span className="font-semibold text-gray-900">{name}</span>
          <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${tagColors[tagColor]}`}>{tag}</span>
        </div>
        <p className="text-sm text-gray-600">{description}</p>
      </div>
    </button>
  );
};

const RadioOption: React.FC<{
  label: string;
  description: string;
  selected: boolean;
  onSelect: () => void;
}> = ({ label, description, selected, onSelect }) => (
  <button
    onClick={onSelect}
    className={`w-full flex items-center gap-3 p-4 rounded-xl border-2 transition text-left ${
      selected ? 'border-purple-500 bg-purple-50' : 'border-gray-200 hover:border-purple-300'
    }`}
  >
    <div
      className={`w-5 h-5 rounded-full border-2 flex items-center justify-center flex-shrink-0 ${
        selected ? 'border-purple-500 bg-purple-500' : 'border-gray-300'
      }`}
    >
      {selected && <div className="w-2 h-2 rounded-full bg-white" />}
    </div>
    <div>
      <div className="font-semibold text-gray-900">{label}</div>
      <div className="text-sm text-gray-600">{description}</div>
    </div>
  </button>
);

const CheckboxOption: React.FC<{
  label: string;
  description: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
}> = ({ label, description, checked, onChange }) => (
  <label className="flex items-start gap-3 cursor-pointer group">
    <input
      type="checkbox"
      checked={checked}
      onChange={(e) => onChange(e.target.checked)}
      className="mt-1 h-5 w-5 text-purple-600 rounded border-2 border-gray-300 focus:ring-purple-500 cursor-pointer"
    />
    <div className="flex-1">
      <div className="font-semibold text-gray-900 group-hover:text-purple-600 transition">{label}</div>
      <div className="text-sm text-gray-600">{description}</div>
    </div>
  </label>
);

const SummaryItem: React.FC<{ icon: string; label: string; value: string | number }> = ({ icon, label, value }) => (
  <div className="flex items-center justify-between p-3 bg-gradient-to-r from-gray-50 to-white rounded-lg border border-gray-200">
    <span className="text-sm text-gray-600 flex items-center gap-2">
      <span className="text-lg">{icon}</span>
      {label}
    </span>
    <span className="font-bold text-gray-900 text-sm">{value}</span>
  </div>
);

export default StrategyBuilderBeta;
