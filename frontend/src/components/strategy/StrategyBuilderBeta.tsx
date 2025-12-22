import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { StrategyConfig } from './StrategyWizard';
import BacktestProgressModal from './BacktestProgressModal';

const StrategyBuilderBeta: React.FC = () => {
  const { t } = useTranslation(['strategy', 'common']);
  const navigate = useNavigate();
  
  const [config, setConfig] = useState<StrategyConfig>({
    name: 'My Strategy',
    backtest_period: { start_date: '', end_date: '' },
    initial_capital: 1000000,
    max_positions: 10,
    engine_type: 'custom',
    sub_universe_filters: { selected_institutions: [] },
    position_sizing: { method: 'equal_weight', percent_per_position: 5 },
    entry_rules: { timing: 'immediate' },
    exit_rules: {},
    risk_management: {},
    transaction_costs: {},
  });

  const [isRunning, setIsRunning] = useState(false);
  const [backtestId, setBacktestId] = useState<string | null>(null);
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set(['setup']));

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

  const handleRunBacktest = async () => {
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

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 shadow-sm sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
                <span className="bg-gradient-to-r from-blue-600 to-indigo-600 text-transparent bg-clip-text">
                  Strategy Builder
                </span>
                <span className="text-xs font-semibold px-2 py-1 bg-blue-100 text-blue-700 rounded-full">
                  BETA
                </span>
              </h1>
              <p className="text-sm text-gray-600 mt-1">Build and test your institutional-grade investment strategy</p>
            </div>
            <button
              onClick={() => navigate('/builder')}
              className="text-sm text-gray-600 hover:text-gray-900 flex items-center gap-1"
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
          {/* Left Column - Configuration */}
          <div className="lg:col-span-2 space-y-4">
            {/* Setup Card */}
            <ConfigCard
              title="Strategy Setup"
              icon="⚙️"
              isExpanded={expandedSections.has('setup')}
              onToggle={() => toggleSection('setup')}
            >
              <div className="space-y-4">
                <InputField
                  label="Strategy Name"
                  value={config.name}
                  onChange={(val) => updateConfig({ name: val })}
                  placeholder="My Institutional Strategy"
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
                  />
                </div>
                <InputField
                  label="Initial Capital ($)"
                  type="number"
                  value={config.initial_capital}
                  onChange={(val) => updateConfig({ initial_capital: parseFloat(val) })}
                />
                <InputField
                  label="Max Positions"
                  type="number"
                  value={config.max_positions || 10}
                  onChange={(val) => updateConfig({ max_positions: parseInt(val) })}
                  min={5}
                  max={20}
                />
              </div>
            </ConfigCard>

            {/* Engine Selection Card */}
            <ConfigCard
              title="Backtesting Engine"
              icon="🚀"
              isExpanded={expandedSections.has('engine')}
              onToggle={() => toggleSection('engine')}
            >
              <div className="space-y-3">
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
            </ConfigCard>

            {/* Stock Selection Card */}
            <ConfigCard
              title="Stock Selection"
              icon="📊"
              isExpanded={expandedSections.has('stocks')}
              onToggle={() => toggleSection('stocks')}
            >
              <p className="text-sm text-gray-600">Select institutions and filtering criteria (coming soon)</p>
            </ConfigCard>
          </div>

          {/* Right Column - Summary & Actions */}
          <div className="lg:col-span-1">
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 sticky top-24">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Quick Summary</h3>
              <div className="space-y-3 mb-6">
                <SummaryItem label="Strategy" value={config.name} />
                <SummaryItem
                  label="Period"
                  value={
                    config.backtest_period?.start_date && config.backtest_period?.end_date
                      ? `${config.backtest_period.start_date} to ${config.backtest_period.end_date}`
                      : 'Not set'
                  }
                />
                <SummaryItem label="Capital" value={`$${config.initial_capital.toLocaleString()}`} />
                <SummaryItem label="Max Positions" value={config.max_positions || 10} />
                <SummaryItem label="Engine" value={config.engine_type || 'custom'} />
              </div>

              <button
                onClick={handleRunBacktest}
                disabled={isRunning || !config.backtest_period?.start_date || !config.backtest_period?.end_date}
                className="w-full bg-gradient-to-r from-blue-600 to-indigo-600 text-white py-3 px-4 rounded-lg font-medium hover:from-blue-700 hover:to-indigo-700 transition disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                {isRunning ? (
                  <>
                    <svg className="animate-spin h-5 w-5" fill="none" viewBox="0 0 24 24">
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
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    Run Backtest
                  </>
                )}
              </button>

              <p className="text-xs text-gray-500 text-center mt-3">
                Est. time: ~{Math.ceil((config.max_positions || 10) * 0.2)} minutes
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
const ConfigCard: React.FC<{
  title: string;
  icon: string;
  isExpanded: boolean;
  onToggle: () => void;
  children: React.ReactNode;
}> = ({ title, icon, isExpanded, onToggle, children }) => (
  <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden transition-all">
    <button
      onClick={onToggle}
      className="w-full flex items-center justify-between p-5 hover:bg-gray-50 transition"
    >
      <div className="flex items-center gap-3">
        <span className="text-2xl">{icon}</span>
        <h2 className="text-lg font-semibold text-gray-900">{title}</h2>
      </div>
      <svg
        className={`w-5 h-5 text-gray-400 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
      </svg>
    </button>
    {isExpanded && <div className="p-5 pt-0 border-t border-gray-100">{children}</div>}
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
}> = ({ label, value, onChange, type = 'text', placeholder, min, max }) => (
  <div>
    <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
    <input
      type={type}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      min={min}
      max={max}
      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition"
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
      className={`w-full flex items-start gap-3 p-4 rounded-lg border-2 transition text-left ${
        selected ? 'border-blue-500 bg-blue-50' : 'border-gray-200 hover:border-gray-300'
      }`}
    >
      <div className="flex-shrink-0 mt-0.5">
        <div
          className={`w-5 h-5 rounded-full border-2 flex items-center justify-center ${
            selected ? 'border-blue-500 bg-blue-500' : 'border-gray-300'
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
      </div>
      <div className="flex-1">
        <div className="flex items-center gap-2 mb-1">
          <span className="font-medium text-gray-900">{name}</span>
          <span className={`text-xs font-semibold px-2 py-0.5 rounded ${tagColors[tagColor]}`}>{tag}</span>
        </div>
        <p className="text-sm text-gray-600">{description}</p>
      </div>
    </button>
  );
};

const SummaryItem: React.FC<{ label: string; value: string | number }> = ({ label, value }) => (
  <div className="flex justify-between items-center text-sm">
    <span className="text-gray-600">{label}</span>
    <span className="font-medium text-gray-900">{value}</span>
  </div>
);

export default StrategyBuilderBeta;

