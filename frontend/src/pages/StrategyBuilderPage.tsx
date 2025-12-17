import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import StrategyWizard from '../components/strategy/StrategyWizard';
import StrategyLibrary from '../components/strategy/StrategyLibrary';

type Tab = 'builder' | 'library';

const StrategyBuilderPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<Tab>('builder');
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">
                Strategy Builder
              </h1>
              <p className="mt-1 text-sm text-gray-500">
                Configure and backtest institutional equity strategies
              </p>
            </div>
            
            <button
              onClick={() => navigate('/results')}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
            >
              View Results
            </button>
          </div>

          {/* Tabs */}
          <div className="flex space-x-8 border-b border-gray-200">
            <button
              onClick={() => setActiveTab('builder')}
              className={`py-4 px-1 border-b-2 font-medium text-sm transition ${
                activeTab === 'builder'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Create Strategy
            </button>
            
            <button
              onClick={() => setActiveTab('library')}
              className={`py-4 px-1 border-b-2 font-medium text-sm transition ${
                activeTab === 'library'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Strategy Library
            </button>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {activeTab === 'builder' ? (
          <StrategyWizard />
        ) : (
          <StrategyLibrary />
        )}
      </div>
    </div>
  );
};

export default StrategyBuilderPage;

