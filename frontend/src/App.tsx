import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import StrategyWizard from './components/strategy/StrategyWizard';
import StrategyLibrary from './components/strategy/StrategyLibrary';
import BacktestResultsPage from './pages/BacktestResultsPage';
import MyStrategiesPage from './pages/MyStrategiesPage';
import StrategyDetailsPage from './pages/StrategyDetailsPage';

const App: React.FC = () => {
  return (
    <Router>
      <div className="min-h-screen bg-gray-50">
        {/* Header */}
        <nav className="bg-white shadow">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between h-16">
              <div className="flex">
                <div className="flex-shrink-0 flex items-center">
                  <h1 className="text-2xl font-bold text-blue-600">PathVest</h1>
                  <span className="ml-3 text-sm text-gray-500">Equity Backtesting Engine</span>
                </div>
                <div className="hidden sm:ml-8 sm:flex sm:space-x-8">
                  <a
                    href="/"
                    className="border-blue-500 text-gray-900 inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium"
                  >
                    Strategy Builder
                  </a>
                  <a
                    href="/my-strategies"
                    className="border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700 inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium"
                  >
                    My Strategies
                  </a>
                  <a
                    href="/library"
                    className="border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700 inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium"
                  >
                    Library
                  </a>
                </div>
              </div>
            </div>
          </div>
        </nav>

        {/* Main Content */}
        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <Routes>
            <Route path="/" element={<Navigate to="/builder" replace />} />
            <Route path="/builder" element={<StrategyWizard />} />
            <Route path="/my-strategies" element={<MyStrategiesPage />} />
            <Route path="/strategies/:strategyId" element={<StrategyDetailsPage />} />
            <Route path="/library" element={<StrategyLibrary />} />
            <Route path="/results/:backtestId" element={<BacktestResultsPage />} />
            <Route path="*" element={<Navigate to="/builder" replace />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
};

export default App;
