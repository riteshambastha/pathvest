import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { StrategyConfig } from '../StrategyWizard';
import HelpPanel from '../../common/HelpPanel';
import { stepHelpContent } from '../helpContent';

interface StepProps {
  config: StrategyConfig;
  updateConfig: (updates: Partial<StrategyConfig>) => void;
  nextStep: () => void;
  prevStep: () => void;
}

interface DateRange {
  min_date: string;
  max_date: string;
  years_covered: number;
  source: string;
}

const Step1_Setup: React.FC<StepProps> = ({ config, updateConfig, nextStep }) => {
  const { t } = useTranslation(['strategy', 'common']);
  const [dateRange, setDateRange] = useState<DateRange | null>(null);
  const [loading, setLoading] = useState(true);
  const [isHelpOpen, setIsHelpOpen] = useState(false);

  useEffect(() => {
    // Fetch available date range from backend
    fetch(`${import.meta.env.VITE_API_BASE_URL}/api/v1/data/date-range`)
      .then((res) => res.json())
      .then((data) => {
        setDateRange(data);
        setLoading(false);
      })
      .catch((err) => {
        console.error('Error fetching date range:', err);
        // Use fallback dates
        setDateRange({
          min_date: '2019-02-14',
          max_date: '2025-12-16',
          years_covered: 7,
          source: 'fallback',
        });
        setLoading(false);
      });
  }, []);

  return (
    <div className="space-y-6">
      {/* Header with Help Button */}
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">{t('steps.step1.title')}</h2>
          <p className="mt-1 text-sm text-gray-600">
            {t('steps.step1.description')}
          </p>
        </div>
        <button
          onClick={() => setIsHelpOpen(true)}
          className="flex items-center space-x-2 px-4 py-2 bg-blue-50 text-blue-700 rounded-lg hover:bg-blue-100 transition border border-blue-200 group"
          title="Open help documentation"
        >
          <svg className="h-5 w-5 group-hover:scale-110 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span className="font-medium">{t('common:help')}</span>
        </button>
      </div>

      {/* Engine Selection */}
      <div className="bg-gradient-to-r from-blue-50 to-indigo-50 p-4 rounded-lg border border-blue-200">
        <label className="block text-sm font-semibold text-gray-900 mb-3">
          {t('engine.title')}
        </label>
        <div className="space-y-3">
          <label className="flex items-start cursor-pointer group">
            <input
              type="radio"
              name="engine"
              value="custom"
              checked={config.engine_type === 'custom' || !config.engine_type}
              onChange={(e) => updateConfig({ engine_type: 'custom' })}
              className="mt-1 h-4 w-4 text-blue-600 focus:ring-blue-500"
            />
            <div className="ml-3">
              <div className="text-sm font-medium text-gray-900 group-hover:text-blue-600">
                {t('engine.custom.name')} <span className="text-xs bg-green-100 text-green-800 px-2 py-0.5 rounded">{t('engine.custom.tag')}</span>
              </div>
              <div className="text-xs text-gray-600 mt-0.5">
                {t('engine.custom.description')}
              </div>
            </div>
          </label>
          
          <label className="flex items-start cursor-pointer group">
            <input
              type="radio"
              name="engine"
              value="backtrader"
              checked={config.engine_type === 'backtrader'}
              onChange={(e) => updateConfig({ engine_type: 'backtrader' })}
              className="mt-1 h-4 w-4 text-blue-600 focus:ring-blue-500"
            />
            <div className="ml-3">
              <div className="text-sm font-medium text-gray-900 group-hover:text-blue-600">
                {t('engine.backtrader.name')} <span className="text-xs bg-orange-100 text-orange-800 px-2 py-0.5 rounded">{t('engine.backtrader.tag')}</span>
              </div>
              <div className="text-xs text-gray-600 mt-0.5">
                {t('engine.backtrader.description')}
              </div>
            </div>
          </label>
          
          <label className="flex items-start cursor-pointer group opacity-60">
            <input
              type="radio"
              name="engine"
              value="lean"
              checked={config.engine_type === 'lean'}
              onChange={(e) => updateConfig({ engine_type: 'lean' })}
              className="mt-1 h-4 w-4 text-blue-600 focus:ring-blue-500"
              disabled
            />
            <div className="ml-3">
              <div className="text-sm font-medium text-gray-900 group-hover:text-blue-600">
                {t('engine.lean.name')} <span className="text-xs bg-purple-100 text-purple-800 px-2 py-0.5 rounded">{t('engine.lean.tag')}</span> <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded">Coming Soon</span>
              </div>
              <div className="text-xs text-gray-600 mt-0.5">
                {t('engine.lean.description')}
              </div>
            </div>
          </label>
        </div>
      </div>

      <div className="space-y-6">
        {/* Strategy Name */}
        <div>
          <label htmlFor="name" className="block text-sm font-medium text-gray-700">
            {t('labels.strategyName')}
          </label>
          <input
            type="text"
            id="name"
            value={config.name}
            onChange={(e) => updateConfig({ name: e.target.value })}
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
            placeholder="My Institutional Strategy"
          />
        </div>

        {/* Backtest Period */}
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
          <div>
            <label htmlFor="start_date" className="block text-sm font-medium text-gray-700">
              {t('labels.startDate')}
            </label>
            <input
              type="date"
              id="start_date"
              value={config.backtest_period?.start_date || ''}
              min={dateRange?.min_date}
              max={dateRange?.max_date}
              onChange={(e) =>
                updateConfig({
                  backtest_period: { 
                    start_date: e.target.value,
                    end_date: config.backtest_period?.end_date || ''
                  },
                })
              }
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
              disabled={loading}
            />
            {dateRange && (
              <p className="mt-1 text-xs text-gray-500">
                Available from: {new Date(dateRange.min_date).toLocaleDateString()}
              </p>
            )}
          </div>

          <div>
            <label htmlFor="end_date" className="block text-sm font-medium text-gray-700">
              {t('labels.endDate')}
            </label>
            <input
              type="date"
              id="end_date"
              value={config.backtest_period?.end_date || ''}
              min={dateRange?.min_date}
              max={dateRange?.max_date}
              onChange={(e) =>
                updateConfig({
                  backtest_period: { 
                    start_date: config.backtest_period?.start_date || '',
                    end_date: e.target.value
                  },
                })
              }
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
              disabled={loading}
            />
            {dateRange && (
              <p className="mt-1 text-xs text-gray-500">
                Available until: {new Date(dateRange.max_date).toLocaleDateString()}
              </p>
            )}
          </div>
        </div>

        {/* Initial Capital */}
        <div>
          <label htmlFor="initial_capital" className="block text-sm font-medium text-gray-700">
            {t('labels.initialCapital')} ($)
          </label>
          <input
            type="number"
            id="initial_capital"
            value={config.initial_capital}
            onChange={(e) => updateConfig({ initial_capital: parseFloat(e.target.value) })}
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
            step="10000"
            min="10000"
          />
          <p className="mt-1 text-sm text-gray-500">
            Default: $1,000,000 (minimum: $10,000)
          </p>
        </div>

        {/* Maximum Positions */}
        <div>
          <label htmlFor="max_positions" className="block text-sm font-medium text-gray-700">
            {t('labels.maxPositions')}
          </label>
          <input
            type="number"
            id="max_positions"
            value={config.max_positions || 10}
            onChange={(e) => updateConfig({ max_positions: parseInt(e.target.value) })}
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
            min="5"
            max="20"
            step="1"
          />
          <div className="mt-2 space-y-1">
            <p className="text-sm text-gray-500">
              Number of stocks to include in backtest (per SRS: 5-20 stocks)
            </p>
            <p className="text-xs text-amber-600 flex items-center">
              <svg className="h-4 w-4 mr-1" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
              </svg>
              ⏱️ Estimated time: ~{Math.ceil((config.max_positions || 10) * 12 / 60)} minutes (AlphaVantage rate limit: 5 calls/min)
            </p>
            <p className="text-xs text-gray-500">
              💡 Recommended: 10 stocks (2 min) for quick tests, 20 stocks (4 min) for full diversification
            </p>
          </div>
        </div>

        {/* Info Box */}
        <div className="rounded-md bg-blue-50 p-4">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg
                className="h-5 w-5 text-blue-400"
                fill="currentColor"
                viewBox="0 0 20 20"
              >
                <path
                  fillRule="evenodd"
                  d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
                  clipRule="evenodd"
                />
              </svg>
            </div>
            <div className="ml-3 flex-1">
              <h3 className="text-sm font-medium text-blue-800">Setup Tips</h3>
              <div className="mt-2 text-sm text-blue-700">
                <ul className="list-disc space-y-1 pl-5">
                  {dateRange ? (
                    <li>
                      <strong>Available data range:</strong> {new Date(dateRange.min_date).toLocaleDateString()} to{' '}
                      {new Date(dateRange.max_date).toLocaleDateString()} ({dateRange.years_covered} years)
                    </li>
                  ) : (
                    <li>Loading available date range...</li>
                  )}
                  <li>Initial capital affects position sizes but not strategy logic</li>
                  <li><strong>Max positions:</strong> Each position gets 5% allocation (per SRS FR-3.1.C.10)</li>
                  <li>Backtest will use adjusted prices (splits/dividends handled)</li>
                  <li>Longer periods provide more robust validation (3+ years recommended)</li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Help Panel */}
      <HelpPanel
        isOpen={isHelpOpen}
        onClose={() => setIsHelpOpen(false)}
        content={stepHelpContent[1]}
      />
    </div>
  );
};

export default Step1_Setup;
