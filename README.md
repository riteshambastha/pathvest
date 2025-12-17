# 🎓 Pathvest - Institutional Following Algorithmic Trading Platform

![Pathvest Banner](https://img.shields.io/badge/Pathvest-Algorithmic%20Trading-blue?style=for-the-badge)
![License](https://img.shields.io/badge/license-MIT-green?style=flat-square)
![Python](https://img.shields.io/badge/python-3.11+-blue?style=flat-square)
![React](https://img.shields.io/badge/react-18+-61DAFB?style=flat-square)
![TypeScript](https://img.shields.io/badge/typescript-5.2+-3178C6?style=flat-square)

**Pathvest** is a sophisticated algorithmic trading platform that enables users to follow the investment strategies of top institutional investors (like Renaissance Technologies, Berkshire Hathaway, etc.) using real SEC 13F filings and Form 4 insider data.

## 🌟 Key Features

### 📊 Signal Engine
- **Doubling Down Signal**: Detect when institutions significantly increase positions
- **Insider Buying Signal**: Track insider purchases via Form 4 filings
- **Institutional Herding**: Identify stocks where multiple top investors are buying
- **Technical Confirmation**: Validate signals with SMA, RSI, and price breakout analysis
- **Conviction Ranking**: Score and rank stocks based on signal strength

### 🎯 Position Management
- **Smart Position Sizing**: Equal weight, fixed size (5%), or conviction-weighted
- **Risk Controls**: Min/max position constraints (3-7% default)
- **Cash Drag Management**: Handle partial deployment scenarios
- **Rebalancing Logic**: Automatic portfolio rebalancing

### 🚪 Exit Modules
- **Thesis Drift**: Exit when institutional ownership falls below threshold
- **Insider Reversal**: Exit on significant insider selling
- **Trailing Stop/Take-Profit**: Dynamic stop-loss and profit-taking
- **Dead Money Exit**: Close positions with prolonged underperformance

### 📈 Dual Backtest Engines
- **Custom Engine**: Fast, lightweight backtesting (2-3 minutes)
- **LEAN Engine**: Professional-grade backtesting with institutional accuracy

### 📉 Advanced Analytics
- **Performance Metrics**: CAGR, Sharpe Ratio, Max Drawdown, Win Rate
- **Visualizations**: Equity curves, drawdown analysis, monthly returns heatmap
- **Risk Analysis**: Monte Carlo simulations, stress testing, parameter sensitivity
- **Real-time Data**: Integration with AlphaVantage, SEC EDGAR, and sec-api.io

### 🎨 Modern UI/UX
- **8-Step Strategy Builder**: Intuitive wizard for strategy creation
- **Interactive Help Panels**: Context-sensitive help for every step
- **Real-time Results**: Live backtest progress and results
- **Strategy Management**: Save, edit, and compare strategies

---

## 🏗️ Architecture

```
pathvest/
├── frontend/          # React + TypeScript + Tailwind UI
│   ├── src/
│   │   ├── components/    # Reusable UI components
│   │   ├── pages/         # Main application pages
│   │   ├── hooks/         # Custom React hooks
│   │   └── utils/         # Utility functions
│   └── package.json
│
├── backend/           # Python FastAPI backend
│   ├── app/
│   │   ├── api/           # REST API endpoints
│   │   ├── services/      # Business logic
│   │   │   ├── signal_engine/     # Signal generation
│   │   │   ├── exit_modules/      # Exit strategies
│   │   │   └── position_sizing/   # Position management
│   │   ├── db/            # Database models
│   │   └── schemas/       # Pydantic schemas
│   ├── lean_engine/       # LEAN integration
│   └── requirements.txt
│
├── terraform/         # Infrastructure as Code
└── docs/             # Documentation
```

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.11+**
- **Node.js 18+**
- **PostgreSQL 14+**
- **Docker** (optional, for LEAN engine)

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/pathvest.git
cd pathvest
```

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Setup environment variables
cp .env.example .env
# Edit .env with your API keys and database URL

# Initialize database
python -c "from app.db.database import init_db; init_db()"

# Run the server
python app/services/real_data_server.py
```

Backend will be running at `http://localhost:8000`

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Setup environment variables
cp .env.example .env
# Edit .env with your API base URL

# Run the development server
npm run dev
```

Frontend will be running at `http://localhost:5173`

---

## 🔑 Required API Keys

### Essential Services

1. **AlphaVantage** (Free tier available)
   - Get key: https://www.alphavantage.co/support/#api-key
   - Used for: Historical stock prices and market data

2. **sec-api.io** (Free tier: 100 requests/day)
   - Get key: https://sec-api.io/
   - Used for: Form 4 insider trading data

3. **OpenFIGI** (Free)
   - Get key: https://www.openfigi.com/api
   - Used for: CUSIP to ticker symbol mapping

### Optional Services

4. **Google Cloud Platform** (Optional, for BigQuery)
   - Used for: Large-scale data storage (PostgreSQL recommended instead)

---

## 📝 Environment Variables

### Backend (.env)

```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/pathvest

# API Keys
ALPHA_VANTAGE_API_KEY=your_key
SEC_API_KEY=your_key
OPENFIGI_API_KEY=your_key

# Application
SECRET_KEY=your_secret_key
DEBUG=True
CORS_ORIGINS=http://localhost:5173
```

### Frontend (.env)

```bash
VITE_API_BASE_URL=http://localhost:8000
VITE_ENABLE_LEAN_ENGINE=true
```

---

## 📖 Usage Guide

### Creating Your First Strategy

1. **Navigate to Strategy Builder**
   - Click "New Strategy" from the dashboard

2. **Step 1: Setup**
   - Name your strategy
   - Set backtest period (e.g., 2020-01-01 to 2024-12-31)
   - Choose backtest engine (Custom recommended for first run)
   - Set initial capital

3. **Step 2: Stock Selection**
   - Select institutions to follow (e.g., Renaissance Technologies)
   - Choose signals (Doubling Down, Insider Buying, Herding)
   - Apply universe filters (market cap, liquidity)

4. **Step 3: Position Sizing**
   - Choose sizing method (5% fixed recommended)
   - Set max positions (5-20 stocks)
   - Configure risk constraints

5. **Step 4-7: Entry & Exit Rules**
   - Configure entry timing
   - Enable exit modules (Thesis Drift, Trailing Stop, etc.)
   - Set stop-loss and take-profit levels

6. **Step 8: Review & Run**
   - Review your configuration
   - Click "Run Backtest"
   - View real-time results

### Viewing Results

- **Performance Tab**: Key metrics, equity curve, drawdown analysis
- **Trades Tab**: All trades with entry/exit details
- **Analytics Tab**: Advanced charts and risk metrics
- **Summary Tab**: AI-generated strategy assessment

---

## 🧪 Running Tests

### Backend Tests

```bash
cd backend
pytest tests/ -v
python verify_signal_engine.py
```

### Frontend Tests

```bash
cd frontend
npm test
```

---

## 📊 Sample Results

```
Strategy: Follow Renaissance Tech (2020-2024)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Initial Capital:       $100,000
Final Value:          $187,450
Total Return:          87.45%
CAGR:                  16.89%
Sharpe Ratio:          1.82
Max Drawdown:          -18.3%
Win Rate:              62.5%
Total Trades:          48
```

---

## 🗄️ Database Schema

### Core Tables

- **institutions**: Top institutional investors
- **filings**: SEC 13F filing records
- **holdings**: Stock positions from filings
- **form4_transactions**: Insider trading data
- **index_constituents**: S&P 500 and other indices
- **market_cap_history**: Historical market cap data
- **liquidity_metrics**: Stock liquidity metrics
- **strategies**: User-created strategies
- **backtests**: Backtest execution records

---

## 🔧 Configuration

### Position Sizing Defaults

```python
DEFAULT_CONFIG = {
    "method": "fixed_size",
    "fixed_size": 0.05,        # 5% per position
    "max_positions": 20,
    "min_position": 0.03,      # 3% minimum
    "max_position": 0.07,      # 7% maximum
    "rank_buffer": 5           # B=5 for entry/exit
}
```

### Signal Thresholds

```python
SIGNAL_CONFIG = {
    "doubling_down_threshold": 1.5,      # 50% increase
    "insider_buying_threshold": 10000,    # $10k+ purchases
    "herding_min_institutions": 3,        # 3+ institutions
    "technical_sma_period": 50,           # 50-day SMA
    "technical_rsi_threshold": 30         # RSI < 30 (oversold)
}
```

---

## 📚 Documentation

- **[Architecture Overview](docs/ARCHITECTURE.md)**: System design and data flow
- **[Signal Engine Guide](docs/SIGNAL_ENGINE_COMPLETE.md)**: How signals are generated
- **[Exit Modules Guide](docs/EXIT_MODULES_COMPLETE.md)**: Exit strategy implementation
- **[Position Sizing Guide](docs/POSITION_SIZING_COMPLETE.md)**: Position management logic
- **[API Documentation](docs/API_DOCS.md)**: REST API endpoints
- **[Deployment Guide](docs/DEPLOYMENT_GUIDE.md)**: Production deployment

---

## 🛠️ Tech Stack

### Frontend
- **React 18**: UI framework
- **TypeScript**: Type safety
- **Tailwind CSS**: Styling
- **Vite**: Build tool
- **Plotly.js**: Interactive charts
- **React Router**: Navigation

### Backend
- **Python 3.11**: Programming language
- **FastAPI**: Web framework
- **SQLAlchemy**: ORM
- **PostgreSQL**: Primary database
- **Pydantic**: Data validation
- **Pandas**: Data analysis
- **NumPy**: Numerical computing

### Infrastructure
- **Docker**: Containerization
- **Terraform**: Infrastructure as Code
- **GitHub Actions**: CI/CD
- **Google Cloud Run**: Deployment (optional)

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines

- Follow PEP 8 for Python code
- Use TypeScript for all new frontend code
- Write tests for new features
- Update documentation as needed
- Keep commits atomic and well-described

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **QuantConnect LEAN**: Inspiration for backtesting architecture
- **SEC EDGAR**: Real institutional trading data
- **AlphaVantage**: Historical market data
- **Renaissance Technologies, Berkshire Hathaway, and other institutions**: For their publicly filed 13F data

---

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/pathvest/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/pathvest/discussions)
- **Email**: support@pathvest.com

---

## 🚧 Roadmap

### Q1 2025
- [ ] Real-time trade execution via broker APIs
- [ ] Multi-asset support (options, futures)
- [ ] Machine learning signal enhancement
- [ ] Mobile app (React Native)

### Q2 2025
- [ ] Social trading features
- [ ] Paper trading mode
- [ ] Advanced portfolio optimization
- [ ] Custom indicator builder

### Q3 2025
- [ ] Multi-strategy portfolio allocation
- [ ] Tax-loss harvesting
- [ ] Performance attribution analysis
- [ ] White-label solutions

---

## ⚠️ Disclaimer

**This software is for educational and research purposes only.** 

- Past performance is not indicative of future results
- Trading involves substantial risk of loss
- You are solely responsible for your trading decisions
- Always consult with a licensed financial advisor
- The authors assume no liability for financial losses

---

## 🌟 Star History

[![Star History Chart](https://api.star-history.com/svg?repos=yourusername/pathvest&type=Date)](https://star-history.com/#yourusername/pathvest&Date)

---

Made by Ritesh Ambastha, for his friend Ravi Pathak.

**Happy Trading! 🚀📈**
