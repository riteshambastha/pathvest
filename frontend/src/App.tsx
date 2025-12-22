import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, Link, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import StrategyWizard from './components/strategy/StrategyWizard';
import StrategyLibrary from './components/strategy/StrategyLibrary';
import BacktestResultsPage from './pages/BacktestResultsPage';
import MyStrategiesPage from './pages/MyStrategiesPage';
import StrategyDetailsPage from './pages/StrategyDetailsPage';
import LanguageSelector from './components/common/LanguageSelector';

// Navigation component with active state
const NavLink: React.FC<{ to: string; children: React.ReactNode }> = ({ to, children }) => {
  const location = useLocation();
  const isActive = location.pathname === to || (to === '/builder' && location.pathname === '/');
  
  return (
    <Link
      to={to}
      className={`inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium transition-colors ${
        isActive
          ? 'border-blue-500 text-gray-900'
          : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
      }`}
    >
      {children}
    </Link>
  );
};

const AppContent: React.FC = () => {
  const { t } = useTranslation(['nav', 'common']);
  
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <nav className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex">
              <div className="flex-shrink-0 flex items-center">
                <Link to="/" className="flex items-center">
                  <h1 className="text-2xl font-bold text-blue-600">{t('common:appName')}</h1>
                  <span className="ml-3 text-sm text-gray-500">Trade AI</span>
                </Link>
              </div>
              <div className="hidden sm:ml-8 sm:flex sm:space-x-8">
                <NavLink to="/builder">{t('strategyBuilder')}</NavLink>
                <NavLink to="/my-strategies">{t('strategies')}</NavLink>
                <NavLink to="/library">Library</NavLink>
              </div>
            </div>
            
            {/* Right side - Language Selector */}
            <div className="flex items-center">
              <LanguageSelector />
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
  );
};

const App: React.FC = () => {
  return (
    <Router>
      <AppContent />
    </Router>
  );
};

export default App;
