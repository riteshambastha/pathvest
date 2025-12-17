import React, { useState, useEffect } from 'react';
import { StrategyConfig } from '../StrategyWizard';
import HelpPanel from '../../common/HelpPanel';
import { stepHelpContent } from '../helpContent';

interface StepProps {
  config: StrategyConfig;
  updateConfig: (updates: Partial<StrategyConfig>) => void;
  nextStep: () => void;
  prevStep: () => void;
}

interface Institution {
  cik: string;
  name: string;
  aum: number;
  description: string;
  category: string;
}

const Step2_StockSelection: React.FC<StepProps> = ({ config, updateConfig, nextStep, prevStep }) => {
  const [institutions, setInstitutions] = useState<Institution[]>([]);
  const [selectedInstitutions, setSelectedInstitutions] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [isHelpOpen, setIsHelpOpen] = useState(false);

  useEffect(() => {
    // Fetch available institutions
    fetch('/api/v1/data/sec/institutions')
      .then(res => res.json())
      .then(data => {
        setInstitutions(data.institutions || []);
        setLoading(false);
      })
      .catch(err => {
        console.error('Error fetching institutions:', err);
        setLoading(false);
      });
  }, []);

  const toggleInstitution = (cik: string) => {
    const newSelection = selectedInstitutions.includes(cik)
      ? selectedInstitutions.filter(c => c !== cik)
      : [...selectedInstitutions, cik];
    
    setSelectedInstitutions(newSelection);
    
    // Update config outside of the setState callback
    updateConfig({
      sub_universe_filters: {
        ...config.sub_universe_filters,
        selected_institutions: newSelection
      }
    });
  };

  return (
    <div className="space-y-6">
      {/* Header with Help Button */}
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Stock Selection Model</h2>
          <p className="mt-1 text-sm text-gray-600">
            Select institutions to follow and define filters to identify qualified stocks
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
          <span className="font-medium">Help</span>
        </button>
      </div>

      {/* Institution Selector - NEW! */}
      <div className="bg-gradient-to-r from-blue-50 to-indigo-50 p-6 rounded-lg border-2 border-blue-200">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-lg font-semibold text-gray-900">🏦 Select Institutions to Follow</h3>
            <p className="text-sm text-gray-600 mt-1">
              Choose institutional investors whose 13F filings you want to track
            </p>
          </div>
          <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
            ✓ Real SEC Data
          </span>
        </div>

        {loading ? (
          <div className="text-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
            <p className="mt-2 text-sm text-gray-600">Loading institutions...</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {institutions.map((inst) => (
              <div
                key={inst.cik}
                onClick={() => toggleInstitution(inst.cik)}
                className={`p-4 rounded-lg border-2 cursor-pointer transition-all ${
                  selectedInstitutions.includes(inst.cik)
                    ? 'border-blue-500 bg-blue-50 shadow-md'
                    : 'border-gray-200 bg-white hover:border-blue-300'
                }`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center">
                      <input
                        type="checkbox"
                        checked={selectedInstitutions.includes(inst.cik)}
                        onChange={() => {}}
                        className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded mr-3"
                      />
                      <div>
                        <h4 className="text-sm font-semibold text-gray-900">{inst.name}</h4>
                        <p className="text-xs text-gray-600 mt-0.5">{inst.description}</p>
                      </div>
                    </div>
                    <div className="mt-2 flex items-center space-x-3 text-xs">
                      <span className="inline-flex items-center px-2 py-0.5 rounded-full bg-purple-100 text-purple-800">
                        {inst.category}
                      </span>
                      <span className="text-gray-600">
                        AUM: ${(inst.aum / 1e9).toFixed(1)}B
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {selectedInstitutions.length > 0 && (
          <div className="mt-4 p-3 bg-blue-100 rounded-lg">
            <p className="text-sm text-blue-900">
              <span className="font-semibold">{selectedInstitutions.length} institution(s) selected</span>
              {' '}- Their 13F filings will be monitored for signals
            </p>
          </div>
        )}
      </div>

      {/* Universe Filters */}
      <div className="bg-gray-50 p-4 rounded-lg">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Universe Filters</h3>
        
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <label className="block text-sm font-medium text-gray-700">
              Market Cap Min ($B)
            </label>
            <input
              type="number"
              value={config.universe_filters.market_cap_min / 1e9}
              onChange={(e) =>
                updateConfig({
                  universe_filters: {
                    ...config.universe_filters,
                    market_cap_min: parseFloat(e.target.value) * 1e9,
                  },
                })
              }
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
              step="0.5"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">
              Index Membership
            </label>
            <select
              value={config.universe_filters.index_membership}
              onChange={(e) =>
                updateConfig({
                  universe_filters: {
                    ...config.universe_filters,
                    index_membership: e.target.value,
                  },
                })
              }
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
            >
              <option value="SP500">S&P 500</option>
              <option value="SP400">S&P 400 (Mid Cap)</option>
              <option value="SP600">S&P 600 (Small Cap)</option>
              <option value="SP1500">S&P 1500 (All)</option>
            </select>
          </div>
        </div>
      </div>

      {/* Investor Qualification */}
      <div className="bg-gray-50 p-4 rounded-lg">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Investor Qualification</h3>
        
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <label className="block text-sm font-medium text-gray-700">
              Min AUM ($B)
            </label>
            <input
              type="number"
              value={(config.sub_universe_filters?.investor?.aum_min || 1e9) / 1e9}
              onChange={(e) =>
                updateConfig({
                  sub_universe_filters: {
                    ...config.sub_universe_filters,
                    investor: {
                      ...(config.sub_universe_filters?.investor || {}),
                      aum_min: parseFloat(e.target.value) * 1e9,
                    },
                  },
                })
              }
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
              step="0.5"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">
              Track Record (Quarters)
            </label>
            <input
              type="number"
              value={config.sub_universe_filters?.investor?.track_record_quarters || 8}
              onChange={(e) =>
                updateConfig({
                  sub_universe_filters: {
                    ...config.sub_universe_filters,
                    investor: {
                      ...(config.sub_universe_filters?.investor || {}),
                      track_record_quarters: parseInt(e.target.value),
                    },
                  },
                })
              }
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">
              Max Concentration (%)
            </label>
            <input
              type="number"
              value={(config.sub_universe_filters?.investor?.concentration_max || 0.2) * 100}
              onChange={(e) =>
                updateConfig({
                  sub_universe_filters: {
                    ...config.sub_universe_filters,
                    investor: {
                      ...(config.sub_universe_filters?.investor || {}),
                      concentration_max: parseFloat(e.target.value) / 100,
                    },
                  },
                })
              }
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
              step="5"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">
              Max Turnover (%)
            </label>
            <input
              type="number"
              value={(config.sub_universe_filters?.investor?.turnover_max || 0.5) * 100}
              onChange={(e) =>
                updateConfig({
                  sub_universe_filters: {
                    ...config.sub_universe_filters,
                    investor: {
                      ...(config.sub_universe_filters?.investor || {}),
                      turnover_max: parseFloat(e.target.value) / 100,
                    },
                  },
                })
              }
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
              step="5"
            />
          </div>
        </div>
      </div>

      {/* Transaction Filters */}
      <div className="bg-gray-50 p-4 rounded-lg">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Transaction Filters</h3>
        
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <label className="block text-sm font-medium text-gray-700">
              Min Buy Value ($M)
            </label>
            <input
              type="number"
              value={config.sub_universe_filters.transaction.min_buy_value / 1e6}
              onChange={(e) =>
                updateConfig({
                  sub_universe_filters: {
                    ...config.sub_universe_filters,
                    transaction: {
                      ...config.sub_universe_filters.transaction,
                      min_buy_value: parseFloat(e.target.value) * 1e6,
                    },
                  },
                })
              }
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">
              Share Increase Min (%)
            </label>
            <input
              type="number"
              value={config.sub_universe_filters.transaction.share_increase_min * 100}
              onChange={(e) =>
                updateConfig({
                  sub_universe_filters: {
                    ...config.sub_universe_filters,
                    transaction: {
                      ...config.sub_universe_filters.transaction,
                      share_increase_min: parseFloat(e.target.value) / 100,
                    },
                  },
                })
              }
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
            />
          </div>
        </div>
      </div>

      {/* Insider Filters */}
      <div className="bg-gray-50 p-4 rounded-lg">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Insider Filters</h3>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Qualified Roles
          </label>
          <div className="space-y-2">
            {['CEO', 'CFO', 'COO', 'President', 'Chairman'].map((role) => (
              <label key={role} className="inline-flex items-center mr-4">
                <input
                  type="checkbox"
                  checked={config.sub_universe_filters.insider.roles.includes(role)}
                  onChange={(e) => {
                    const roles = e.target.checked
                      ? [...config.sub_universe_filters.insider.roles, role]
                      : config.sub_universe_filters.insider.roles.filter((r) => r !== role);
                    updateConfig({
                      sub_universe_filters: {
                        ...config.sub_universe_filters,
                        insider: {
                          ...config.sub_universe_filters.insider,
                          roles,
                        },
                      },
                    });
                  }}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="ml-2 text-sm text-gray-700">{role}</span>
              </label>
            ))}
          </div>
        </div>

        <div className="mt-4">
          <label className="block text-sm font-medium text-gray-700">
            Min Transaction Value ($K)
          </label>
          <input
            type="number"
            value={config.sub_universe_filters.insider.value_min / 1000}
            onChange={(e) =>
              updateConfig({
                sub_universe_filters: {
                  ...config.sub_universe_filters,
                  insider: {
                    ...config.sub_universe_filters.insider,
                    value_min: parseFloat(e.target.value) * 1000,
                  },
                },
              })
            }
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
          />
        </div>
      </div>

      {/* Navigation */}
      <div className="flex justify-between">
        <button
          onClick={prevStep}
          className="px-6 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition"
        >
          Previous
        </button>
        <button
          onClick={nextStep}
          className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
        >
          Next: Entry Signals
        </button>
      </div>

      {/* Help Panel */}
      <HelpPanel
        isOpen={isHelpOpen}
        onClose={() => setIsHelpOpen(false)}
        content={stepHelpContent[2]}
      />
    </div>
  );
};

export default Step2_StockSelection;

