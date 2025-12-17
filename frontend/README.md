# PathVest Frontend - Strategy Builder UI

## Overview

The PathVest frontend is a React + TypeScript application providing a user-friendly interface for creating, managing, and analyzing equity trading strategies based on SEC 13F filings and insider transactions.

## Features

### 1. **8-Step Strategy Wizard** 🧙‍♂️
A guided workflow for building sophisticated trading strategies:

1. **Strategy Setup**: Name, backtest period, initial capital
2. **Stock Selection**: Universe and sub-universe filters (investor, transaction, insider criteria)
3. **Entry & Position Sizing**: Primary signals (Doubling Down, Insider Buying, Herding) + Technical Confirmation
4. **Entry Scheduling**: Rebalancing frequency (daily, weekly, monthly, quarterly)
5. **Exit Model**: 4 exit modules (Thesis Drift, Insider Reversal, Trailing Stop, Dead Money)
6. **Risk Management**: Transaction costs (commission, slippage)
7. **Parameters**: Benchmark selection and validation suite
8. **Review & Backtest**: Summary review and execution

### 2. **Results Dashboard** 📊
Comprehensive backtest results visualization with 5 tabs:

- **Overview**: Equity curve, key metrics (CAGR, Sharpe, Alpha, Max Drawdown)
- **Trades**: Detailed trade log with P&L, returns, holding periods
- **Attribution**: Performance breakdown by signal type, stock, time period
- **Validation**: Robustness analysis (Monte Carlo, Walk-Forward, Parameter Sensitivity, Stress Testing)
- **Export**: CSV, Excel, PDF export functionality

### 3. **Strategy Library** 📚
- View all saved strategies
- Compare multiple strategies side-by-side
- Clone existing strategies
- View historical performance metrics
- Quick access to backtest results

## Technology Stack

- **Framework**: React 18 + TypeScript
- **Build Tool**: Vite
- **Routing**: React Router v6
- **Styling**: Tailwind CSS
- **Charts**: Plotly.js (for advanced visualizations)
- **HTTP Client**: Axios
- **State Management**: React Hooks (useState, useEffect)

## Project Structure

```
frontend/
├── src/
│   ├── components/
│   │   └── strategy/
│   │       ├── StrategyWizard.tsx       # Main wizard orchestrator
│   │       ├── StrategyLibrary.tsx      # Library view
│   │       └── steps/
│   │           ├── Step1_Setup.tsx
│   │           ├── Step2_StockSelection.tsx
│   │           ├── Step3_EntryPositionSizing.tsx
│   │           ├── Step4_EntryScheduling.tsx
│   │           ├── Step5_ExitModel.tsx
│   │           ├── Step6_RiskManagement.tsx
│   │           ├── Step7_Parameters.tsx
│   │           └── Step8_Backtest.tsx
│   ├── pages/
│   │   └── BacktestResultsPage.tsx      # Results dashboard
│   ├── services/
│   │   └── backtestService.ts           # API integration
│   ├── App.tsx                          # Main app with routing
│   ├── main.tsx                         # Entry point
│   └── index.css                        # Global styles
├── package.json
├── vite.config.ts
├── tsconfig.json
├── tailwind.config.js
└── index.html
```

## Setup Instructions

### Prerequisites
- Node.js 18+ and npm/yarn
- Backend API running on `http://localhost:8000`

### Installation

```bash
cd frontend
npm install
```

### Development

```bash
npm run dev
```

Application will be available at `http://localhost:3000`

### Build for Production

```bash
npm run build
```

Outputs to `dist/` directory.

### Preview Production Build

```bash
npm run preview
```

## Configuration

Create a `.env` file in the frontend root:

```env
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

## API Integration

The frontend communicates with the backend via REST API:

### Key Endpoints

- `POST /api/v1/backtest/run` - Submit backtest
- `GET /api/v1/backtest/{id}` - Get backtest results
- `GET /api/v1/backtest/{id}/status` - Check backtest status
- `GET /api/v1/analytics/{id}/metrics` - Get performance metrics
- `GET /api/v1/analytics/{id}/attribution` - Get attribution analysis
- `GET /api/v1/analytics/{id}/visualizations/{type}` - Get visualizations
- `GET /api/v1/analytics/{id}/export/{format}` - Export results

See `src/services/backtestService.ts` for complete API client.

## Default Strategy Configuration

The wizard initializes with the **"Combined Professional"** configuration:

- **Period**: 2013-2023 (10 years)
- **Capital**: $1M
- **Signals**: All 3 primary signals enabled (Doubling Down, Insider Buying, Herding)
- **Technical**: 10-day breakout, 50-day SMA, RSI > 45
- **Position Size**: 5% per position
- **Portfolio**: 5-20 stocks
- **Exit Modules**: All enabled (Thesis Drift, Insider Reversal, 15% Trailing Stop, 4Q Dead Money)
- **Rebalance**: Monthly
- **Validation**: All 4 methods enabled

## Design Principles

1. **Progressive Disclosure**: Complex parameters hidden until needed
2. **Sensible Defaults**: Pre-configured with institutional-grade settings
3. **Immediate Feedback**: Validation and hints at each step
4. **Accessibility**: Keyboard navigation, ARIA labels, responsive design
5. **Performance**: Lazy loading, code splitting, optimized re-renders

## Responsive Design

The UI is fully responsive across devices:
- **Desktop**: Full wizard with side-by-side layouts
- **Tablet**: Adapted layouts, collapsible sections
- **Mobile**: Stacked views, simplified navigation

## Browser Support

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## Future Enhancements

1. **Real-time Updates**: WebSocket connection for live backtest progress
2. **Advanced Charting**: Interactive Plotly charts for equity curves
3. **Strategy Comparison**: Side-by-side comparison view
4. **Collaboration**: Share strategies with team members
5. **Templates**: Pre-built strategy templates
6. **Dark Mode**: Theme toggle

## Troubleshooting

### API Connection Issues
- Ensure backend is running on port 8000
- Check CORS configuration in backend
- Verify `VITE_API_BASE_URL` in `.env`

### Build Errors
- Clear `node_modules` and reinstall: `rm -rf node_modules && npm install`
- Clear Vite cache: `rm -rf node_modules/.vite`

### TypeScript Errors
- Run type check: `npx tsc --noEmit`
- Update types: `npm update @types/react @types/react-dom`

## Contributing

This UI is designed to be extended. To add a new filter or parameter:

1. Update `StrategyConfig` interface in `StrategyWizard.tsx`
2. Modify the relevant step component
3. Update default config in wizard state
4. Ensure backend API supports the new parameter

## License

Proprietary - PathVest Internal Use Only

---

Built with ❤️ by the PathVest Team
