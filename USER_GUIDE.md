# PathVest User Guide

**Version**: 1.0  
**Last Updated**: December 15, 2024  

Welcome to PathVest, the institutional-grade equity backtesting engine for strategies based on SEC 13F filings and insider transactions.

---

## Table of Contents

1. [Introduction](#introduction)
2. [Getting Started](#getting-started)
3. [Strategy Builder Workflow](#strategy-builder-workflow)
4. [Understanding Signals](#understanding-signals)
5. [Advanced Features](#advanced-features)
6. [Interpreting Results](#interpreting-results)
7. [Best Practices](#best-practices)
8. [FAQ](#faq)

---

## Introduction

### What is PathVest?

PathVest is a sophisticated backtesting platform that allows you to:
- **Follow Smart Money**: Track institutional investors' moves via 13F filings
- **Leverage Insider Activity**: Incorporate Form 4 insider buying/selling signals
- **Validate Rigor**: Use advanced validation techniques (Monte Carlo, Walk-Forward, Parameter Sensitivity, Stress Testing)
- **Optimize Performance**: Fine-tune entry, exit, and position sizing rules

### Who Should Use PathVest?

- Quantitative analysts building institutional following strategies
- Portfolio managers evaluating smart money signals
- Hedge fund professionals researching factor-based strategies
- Individual investors seeking systematic, data-driven approaches

---

## Getting Started

### Access the Platform

1. **Open your browser** and navigate to: `https://pathvest.app` (or your deployed URL)
2. **Log in** with your credentials (or use as guest during beta)
3. You'll see the **Home Dashboard** with two options:
   - **Strategy Builder**: Create a new strategy
   - **Library**: View saved strategies

### Quick Start: Run Your First Backtest

1. Click **"Strategy Builder"**
2. Use the default **"Combined Professional"** preset (recommended)
3. Click through all 8 steps (defaults are pre-configured)
4. On Step 8, click **"Run Backtest"**
5. Wait 1-2 minutes for results
6. View performance metrics, trade log, and charts

---

## Strategy Builder Workflow

The Strategy Builder guides you through an **8-step wizard** to define your trading strategy.

### Step 1: Strategy Setup

**Purpose**: Define basic parameters

**Inputs**:
- **Strategy Name**: Give your strategy a memorable name (e.g., "Buffett Followers Q1 2024")
- **Backtest Period**: 
  - Start Date (e.g., 2013-01-01)
  - End Date (e.g., 2023-12-31)
  - **Tip**: Use at least 5 years for statistical significance
- **Initial Capital**: Starting portfolio value (e.g., $1,000,000)

**Best Practice**: Use a period that covers multiple market cycles (bull + bear markets).

---

### Step 2: Stock Selection Model

**Purpose**: Define the "Universe" and "Sub-universe" of qualified stocks

#### **Universe Filters**

These create the initial search space:

- **Market Cap Min**: Minimum market capitalization (default: $3B)
  - *Why*: Larger stocks have better liquidity and data quality
- **Index Membership**: S&P 1500, S&P 500, etc.
  - *Why*: Ensures investable, liquid stocks

#### **Investor Qualification (Fund Characteristics)**

These filters identify "smart money" funds worth following:

- **Min AUM**: Minimum Assets Under Management (default: $1B)
  - *Why*: Larger funds have more resources for research
- **Track Record**: Minimum consecutive quarters (default: 8)
  - *Why*: Filters out flash-in-the-pan funds
- **Max Concentration**: Maximum single position as % of portfolio (default: 35%)
  - *Why*: Avoids overly concentrated (risky) portfolios
- **Max Turnover**: Maximum quarterly turnover (default: 40%)
  - *Why*: Focuses on long-term investors, not day traders

#### **Transaction Filters**

Criteria for a "meaningful" buy:

- **Min Buy Value**: Minimum dollar value purchased (default: $10M)
  - *Why*: Filters out insignificant position changes
- **Share Increase Min**: Minimum % increase in shares (default: 5%)
  - *Why*: Ensures material increase, not just minor adjustments

#### **Insider Filters**

Criteria for insider transactions (Form 4):

- **Qualified Roles**: CEO, CFO, COO, President, Chairman
  - *Why*: C-level insiders have the most information
- **Min Transaction Value**: Minimum dollar value (default: $100K)
  - *Why*: Filters out trivial stock awards/options exercises

---

### Step 3: Entry & Position Sizing

**Purpose**: Define when to buy and how much to allocate

#### **Primary Signals (Pick 1 or More)**

✅ **Signal A: Doubling Down**
- Triggered when: Stock price < Investor's Cost Basis AND Share count increased
- *Interpretation*: The fund is buying more at a lower price (conviction in recovery)

✅ **Signal B: Insider Buying**
- Triggered when: Large institutional buy AND Insider buy > 10% increase
- *Interpretation*: Smart money + insider confidence = strong signal

✅ **Signal C: Institutional Herding**
- Triggered when: 1 large institutional buy AND 2+ institutional followers
- *Interpretation*: Multiple funds piling in = crowded trade (can be good or bad)

**Recommended**: Enable all three signals (Combined Professional approach)

#### **Technical Confirmation**

All primary signals must also pass these technical filters:

- **Price Breakout**: Close > N-day high (default: 10 days)
  - *Why*: Confirms upward momentum
- **Trend Filter (SMA)**: Close > 50-day Simple Moving Average
  - *Why*: Avoids buying in downtrends
- **Momentum Filter (RSI)**: RSI (14-period) > 45
  - *Why*: Avoids oversold/weak stocks

#### **Position Sizing**

- **Position Size**: % of portfolio per stock (default: 5%)
  - *Why*: Diversification + concentrated enough to matter
- **Min Positions**: Minimum stocks to be active (default: 5)
  - *Why*: If < 5 qualified, go to cash (weak pipeline)
- **Max Positions**: Maximum stocks in portfolio (default: 20)
  - *Why*: Over-diversification = diluted alpha
- **Rank Buffer**: Buffer to prevent churn (default: 5 spots)
  - *Why*: Don't swap stock #20 for stock #21 on minor score changes

---

### Step 4: Entry Scheduling

**Purpose**: Define rebalancing frequency (strategy heartbeat)

**Options**:
- **Daily**: Re-scan universe every day (high churn, high costs)
- **Weekly**: Re-scan every week
- **Monthly** ⭐ (Recommended): Aligns with 13F filing frequency
- **Quarterly**: Lower churn, more concentrated positions

**Trade-off**: 
- Higher frequency = More responsive, but higher transaction costs
- Lower frequency = Less churn, but may miss opportunities

---

### Step 5: Exit Model

**Purpose**: Define when to sell (4 independent exit modules)

#### **Module 1: Thesis Drift Exit** (Mandatory)

**Trigger**: Smart money leaves
- No qualified institutions still holding
- Institutional ownership drops > 20% QoQ
- Stock fails fundamental filters (e.g., market cap < $3B)

**Execution**: Market order at open (T+1 after filing date)

**Why Mandatory**: If the thesis (following smart money) is invalidated, exit immediately.

#### **Module 2: Insider Reversal Exit** (Optional)

**Trigger**: Massive insider selling cluster
- Aggregate insider sales (30 days) > $5M
- Sales > 50% of insider holdings

**Execution**: Market order at open (T+1 after Form 4 date)

**Why Use**: Insiders sell for many reasons, but a massive cluster is a red flag.

#### **Module 3: Trailing Stop** (Recommended)

**Trigger**: High-water mark trailing stop
- Formula: `P_exit = Max(Price_history) × (1 - Trailing_Stop_Pct)`
- Default: 15% trailing stop

**Execution**: Market order at open (T+1 after breach)

**Why Use**: Protects gains between quarterly 13F updates (intra-quarter risk management).

#### **Module 4: Dead Money Exit** (Recommended)

**Trigger**: Stale position with negative return
- Held > 4 quarters AND Total return < 0%

**Execution**: Market order at open

**Why Use**: Frees up capital from positions that aren't working.

**Recommended Combination**: Enable Module 1 (mandatory) + Module 3 + Module 4.

---

### Step 6: Risk Management

**Purpose**: Model realistic transaction costs

#### **Commission per Share**
- Default: $0.005 (0.5 cents per share)
- *Typical Range*: $0.001 - $0.01 depending on broker

#### **Slippage (Basis Points)**
- Default: 25 bps (0.25% of execution price)
- *Why*: Difference between expected and actual execution price

**Impact**: Higher transaction costs significantly reduce strategy performance. Model conservatively!

---

### Step 7: Parameters & Validation

**Purpose**: Configure benchmark and enable validation suite

#### **Benchmark**
- **S&P 500 Total Return** (recommended)
- S&P 400 Mid Cap
- S&P 600 Small Cap
- Custom

**Why Important**: Alpha, Beta, and Information Ratio are calculated vs this benchmark.

#### **Validation Suite** (Advanced)

Enable these for robust strategy validation (increases backtest time to ~10 minutes):

- ✅ **Walk-Forward Optimization**: Tests with train/test splits (out-of-sample validation)
- ✅ **Monte Carlo Simulation**: 1000+ runs shuffling trades (probability distribution)
- ✅ **Parameter Sensitivity**: 2D heatmap testing robustness across parameter space
- ✅ **Stress Testing**: Performance during historical crisis periods (2008, COVID, etc.)

**Recommended**: Enable all four for final strategy validation.

---

### Step 8: Review & Backtest

**Purpose**: Review configuration and execute backtest

#### **Review**
- Double-check all settings
- Estimated runtime displayed (1 min baseline, 5-10 min with validation)

#### **Actions**
- **Save Strategy**: Save configuration for later (without running)
- **Run Backtest**: Execute the simulation

**What Happens Next**:
1. Strategy is submitted to the LEAN Engine
2. You're redirected to the **Results Page**
3. Results load when backtest completes

---

## Understanding Signals

### Signal A: Doubling Down

**Logic**: `Stock Price < Cost Basis AND Share Count Increased`

**Example**:
- Berkshire Hathaway owns Apple
- Q1: Bought 100M shares @ $150 (Cost Basis)
- Q2: Apple drops to $130
- Q2: Berkshire buys another 50M shares (total: 150M)
- **Signal**: Doubling Down (buying more at a lower price)

**Interpretation**: High conviction that the stock is undervalued.

---

### Signal B: Insider Buying

**Logic**: `Large Inst Buy AND Insider Buy > 10% Increase`

**Example**:
- Tiger Global buys $20M of Tesla (13F)
- Same quarter: Elon Musk buys $5M of Tesla (Form 4)
- **Signal**: Insider Buying (alignment of smart money + insider)

**Interpretation**: Both external investors and insiders are bullish.

---

### Signal C: Institutional Herding

**Logic**: `1 Large Inst Buy AND 2+ Followers`

**Example**:
- Soros Fund buys $30M of Nvidia (Leader)
- Renaissance Technologies buys $15M (Follower 1)
- Two Sigma buys $10M (Follower 2)
- **Signal**: Herding (multiple funds piling in)

**Interpretation**: Crowded trade. Can be bullish (momentum) or bearish (overheated).

---

## Advanced Features

### Conviction Ranking Algorithm

When > 20 stocks qualify, the system ranks them by:

**Formula**: `S_conviction = w₁(I_herding) + w₂(I_insider)`

- `I_herding`: Institutional Herding Score (0-100)
- `I_insider`: Insider Confidence Score (0-100)
- Default Weights: `w₁=0.6, w₂=0.4`

**Tie-Breaking**: If scores are identical, prioritize **lower market cap** (higher beta/growth potential).

---

### Walk-Forward Optimization

**Purpose**: Validate strategy on "unseen" data

**How It Works**:
1. Split backtest period into 4 windows
2. Window 1: Train on 2 years → Test on 6 months
3. Window 2: Train on next 2 years → Test on 6 months
4. Repeat for all windows

**Metric**: Walk-Forward Efficiency (WFE) = Out-of-Sample Return / In-Sample Return
- WFE > 0.6: Good (robust)
- WFE 0.6-1.2: Excellent (no overfitting)
- WFE > 1.2: Exceptional (strategy improves OOS)

---

### Monte Carlo Simulation

**Purpose**: Understand strategy's probability distribution

**How It Works**:
1. Take your trade sequence
2. Shuffle trades randomly 1000 times
3. Plot equity curves for all 1000 runs
4. Show 95% and 99% confidence intervals

**Interpretation**:
- **Narrow Cone**: Stable strategy (low luck dependence)
- **Wide Cone**: High variance (luck plays a big role)

---

### Parameter Sensitivity Analysis

**Purpose**: Test if strategy is overfitted to specific parameters

**How It Works**:
1. Vary 2 parameters (e.g., SMA period, Trailing Stop %)
2. Run backtest for each combination
3. Display heatmap of Sharpe Ratio

**Goal**: Find a "Green Island" (broad region of profitability) rather than a single peak.

**Red Flag**: If only one parameter combination works, strategy is likely overfitted.

---

### Stress Testing

**Purpose**: Benchmark drawdown during historical crises

**Scenarios**:
- **Dot Com Bubble** (2000-2002)
- **Financial Crisis 2008** (2008-2009)
- **COVID Crash** (Feb-Mar 2020)
- **Inflation Spike** (2022)

**Metric**: Compare strategy max drawdown vs S&P 500 during each crisis.

**Good Result**: Strategy drawdown < Benchmark drawdown (defensive)

---

## Interpreting Results

### Overview Tab

**Key Metrics**:

- **Total Return**: Cumulative return over entire period
- **CAGR**: Compound Annual Growth Rate (annualized return)
- **Volatility**: Standard deviation of returns (risk)
- **Sharpe Ratio**: Risk-adjusted return `(Return - Risk-Free Rate) / Volatility`
  - > 1: Good
  - > 2: Excellent
  - > 3: Outstanding
- **Sortino Ratio**: Like Sharpe, but only penalizes downside volatility
- **Max Drawdown**: Largest peak-to-trough decline
- **Alpha**: Excess return vs benchmark (goal: positive)
- **Beta**: Sensitivity to benchmark (< 1: defensive, > 1: aggressive)

**Equity Curve**: Visual representation of portfolio value over time.

---

### Trades Tab

**Trade Log Columns**:
- **Ticker**: Stock symbol
- **Entry Date**: When position was opened
- **Exit Date**: When position was closed
- **Return %**: Percentage gain/loss
- **P&L**: Dollar profit/loss
- **Holding Period**: Days held
- **Exit Reason**: Why position was closed (thesis drift, trailing stop, etc.)
- **Signal Type**: Which primary signal triggered entry

**Use Case**: Identify best/worst trades, common exit reasons, holding period patterns.

---

### Attribution Tab

**Breakdowns**:
- **By Signal Type**: Which signal (Doubling Down, Insider, Herding) performed best?
- **By Stock**: Which stocks contributed most to P&L?
- **By Time Period**: Performance by year, quarter, month
- **By Holding Period**: Do longer holds perform better?

**Use Case**: Understand what's working and what's not.

---

### Validation Tab

**Charts**:
- **Monte Carlo Cone**: Probability distribution of outcomes
- **Parameter Sensitivity Heatmap**: Robustness across parameter space
- **Walk-Forward Matrix**: Out-of-sample efficiency
- **Stress Testing Bar Chart**: Drawdown comparison during crises

**Use Case**: Validate strategy robustness before deploying real capital.

---

### Export Tab

**Options**:
- **Export Trades (CSV)**: Trade-by-trade log
- **Export Full Report (Excel)**: Multi-sheet workbook with metrics, trades, attribution
- **Export Summary (PDF)**: One-page tearsheet for presentations

---

## Best Practices

### 1. Start with Defaults
- Use the "Combined Professional" preset
- Run a backtest to understand baseline performance
- Then iterate on individual parameters

### 2. Use Long Backtest Periods
- **Minimum**: 5 years
- **Recommended**: 10+ years (covers multiple market cycles)

### 3. Model Transaction Costs Conservatively
- Use **realistic** commission and slippage estimates
- Don't assume zero costs (unrealistic)

### 4. Enable Validation Suite for Final Strategy
- Walk-forward, Monte Carlo, Sensitivity, Stress Testing
- Adds 5-10 minutes but ensures robustness

### 5. Avoid Overfitting
- Don't endlessly tweak parameters to maximize backtest performance
- If Sharpe Ratio > 3, be skeptical (too good to be true)
- Check parameter sensitivity heatmap for robustness

### 6. Diversify Across Signals
- Don't rely on only one signal type
- Enable all three primary signals for diversification

### 7. Understand Your Risk Tolerance
- If Max Drawdown > 30%, strategy may be too aggressive
- Consider lowering position size or tightening trailing stop

### 8. Paper Trade Before Going Live
- Run strategy in real-time without real money
- Validate execution delays, data quality, signal accuracy

---

## FAQ

### Q1: How often are 13F filings updated?
**A**: Quarterly. Funds must file 13F within 45 days of quarter-end. This means data is always 1.5-2 months delayed.

### Q2: Can I backtest with more than $10M capital?
**A**: Yes! Just change "Initial Capital" in Step 1. Note that very large portfolios may face liquidity constraints (not modeled in basic backtest).

### Q3: Why is my Sharpe Ratio negative?
**A**: Your strategy lost money or didn't beat the risk-free rate. Review your signals, filters, and exit rules.

### Q4: What's the difference between Sharpe and Sortino?
**A**: Sharpe penalizes all volatility (up and down). Sortino only penalizes downside volatility (losses). Sortino is more forgiving for strategies with asymmetric returns.

### Q5: How do I interpret Walk-Forward Efficiency (WFE)?
**A**: 
- WFE < 0.6: Strategy degraded out-of-sample (overfitted)
- WFE 0.6-1.2: Good (robust)
- WFE > 1.2: Exceptional (improved OOS)

### Q6: Can I customize the signals (e.g., change the 10% insider threshold)?
**A**: Not in the UI (v1.0). For custom signal logic, use the API (see API Documentation).

### Q7: What happens if my backtest fails?
**A**: Check the error log. Common causes:
- No data for selected period
- Invalid parameter (e.g., negative position size)
- API timeout (large backtest, try reducing period)

### Q8: Can I compare two strategies side-by-side?
**A**: Yes! Go to Library → Select 2+ strategies → Click "Compare Selected"

### Q9: How long does a backtest take?
**A**: 
- Basic (no validation): ~1 minute
- With validation suite: ~5-10 minutes
- Very long periods (15+ years): up to 15 minutes

### Q10: Is my data private?
**A**: Yes. All strategies and backtests are tied to your user account and not visible to others.

---

## Support

**Need Help?**  
- **Email**: support@pathvest.com  
- **Documentation**: https://docs.pathvest.com  
- **Community**: https://community.pathvest.com

---

**Happy Backtesting!** 🚀

*Disclaimer: Past performance is not indicative of future results. PathVest is for educational and research purposes only. Consult a financial advisor before making investment decisions.*

