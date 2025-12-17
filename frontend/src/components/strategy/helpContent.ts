import { HelpContent } from '../common/HelpPanel';

export const stepHelpContent: Record<number, HelpContent> = {
  1: {
    stepTitle: 'Strategy Setup',
    stepNumber: 1,
    overview: 'Configure the foundation of your backtesting strategy: name, time period, initial capital, engine selection, and portfolio size. These parameters define the scope and constraints of your backtest.',
    sections: [
      {
        title: 'Backtesting Engine Selection',
        icon: '⚙️',
        content: `
          <p class="mb-2"><strong>Custom Engine:</strong> PathVest's proprietary engine optimized for SEC filing analysis. Fast execution (~2-3 minutes), easier to debug, and tailored for institutional following strategies.</p>
          <p><strong>LEAN Engine:</strong> QuantConnect's production-grade engine with advanced features like fractional shares, live trading capability, and industry-standard compliance. Ideal for complex strategies and eventual live deployment.</p>
        `,
      },
      {
        title: 'Backtest Period',
        icon: '📅',
        content: `
          <p class="mb-2">Select the historical time range for your backtest. The available data spans <strong>7 years (2019-2025)</strong> of SEC 13F filings and market data.</p>
          <p class="text-sm text-gray-600 italic">💡 Recommendation: Use at least 3 years for robust validation and to capture multiple market cycles.</p>
        `,
      },
      {
        title: 'Initial Capital',
        icon: '💰',
        content: `
          <p class="mb-2">Your starting portfolio value. This affects position sizes but not strategy logic or relative returns.</p>
          <p class="text-sm">• Minimum: $10,000<br>• Default: $1,000,000<br>• Each position gets 5% allocation (per SRS FR-3.1.C.10)</p>
        `,
      },
      {
        title: 'Maximum Positions',
        icon: '📊',
        content: `
          <p class="mb-2">Number of stocks to include in your backtest (5-20 per SRS specification).</p>
          <p class="text-sm">• <strong>5 stocks:</strong> ~1 min (fast testing)<br>• <strong>10 stocks:</strong> ~2 min (balanced default)<br>• <strong>15 stocks:</strong> ~3 min (more diversity)<br>• <strong>20 stocks:</strong> ~4 min (full diversification)</p>
          <p class="text-xs text-amber-700 mt-2">⏱️ Time varies due to AlphaVantage API rate limit (5 calls/min)</p>
        `,
      },
    ],
    technicalDetails: {
      backend: [
        'Validates date range against BigQuery data availability (2019-2025)',
        'Enforces SRS position constraints (5-20 stocks, 5% allocation each)',
        'Initializes backtest configuration with validated parameters',
      ],
      frontend: [
        'Dynamic date picker constrained to available data range',
        'Real-time backtest duration estimation based on max_positions',
        'Engine selector with feature comparison tooltips',
      ],
      dataFlow: [
        'Frontend fetches available date range from /api/v1/data/date-range',
        'User inputs are validated client-side before proceeding',
        'Configuration is saved to StrategyConfig state for subsequent steps',
      ],
    },
    tips: [
      'Start with 10 stocks and Custom Engine for quick iteration',
      'Longer backtest periods (5+ years) provide better statistical significance',
      'Initial capital can be adjusted later without re-running the backtest',
      'Use LEAN Engine if you plan to eventually deploy this strategy live',
    ],
  },

  2: {
    stepTitle: 'Stock Selection',
    stepNumber: 2,
    overview: 'Define your investment universe by selecting institutional investors to follow. PathVest tracks their SEC 13F filings to identify stocks they\'re actively buying, selling, or holding.',
    sections: [
      {
        title: 'Institution Selection',
        icon: '🏦',
        content: `
          <p class="mb-2">Choose from <strong>45+ major institutions</strong> including Berkshire Hathaway, ARK Investment, Tiger Global, and more. Each institution files quarterly 13F reports disclosing their equity holdings.</p>
          <p class="text-sm text-gray-600">Our database contains <strong>8,344 holdings</strong> across 7 years (2019-2025) with real SEC filing dates for point-in-time accuracy.</p>
        `,
      },
      {
        title: 'Universe Filtration',
        icon: '🔍',
        content: `
          <p class="mb-2">Automatically filters the stock universe based on:</p>
          <ul class="text-sm space-y-1 ml-4">
            <li>• <strong>Index Membership:</strong> S&P 1500 constituents</li>
            <li>• <strong>Market Cap:</strong> Minimum $3B (default)</li>
            <li>• <strong>Liquidity:</strong> Average daily volume thresholds</li>
            <li>• <strong>Filing History:</strong> Lookback period (default: 4 quarters)</li>
          </ul>
        `,
      },
      {
        title: 'Sub-Universe Filters',
        icon: '⚡',
        content: `
          <p class="mb-2">Advanced filters to refine institutional following:</p>
          <p class="text-sm"><strong>Investor Filters:</strong> AUM requirements, track record, portfolio concentration, turnover rate</p>
          <p class="text-sm"><strong>Transaction Filters:</strong> Minimum buy value, share increase percentage (≥100% for "doubling down")</p>
          <p class="text-sm"><strong>Insider Filters:</strong> C-level executive activity, cluster detection</p>
        `,
      },
    ],
    technicalDetails: {
      backend: [
        'Fetches institution list from BigQuery sec_institutions table',
        'Retrieves holdings for selected institutions from sec_holdings_13f',
        'Applies universe filters: market cap, index membership, lookback period',
        'Calculates position changes quarter-over-quarter for signal generation',
      ],
      frontend: [
        'Multi-select dropdown with search functionality',
        'Real-time preview of selected institutions',
        'Filter toggles for universe and sub-universe criteria',
      ],
      dataFlow: [
        'GET /api/v1/institutions → Returns list of available institutions',
        'User selects institutions → Saved to config.selected_institutions',
        'Filter changes → Updates config.universe_filters and config.sub_universe_filters',
      ],
    },
    tips: [
      'Start with 2-3 institutions to understand signal patterns before scaling',
      'Combining value investors (Berkshire) with growth investors (ARK) creates diverse signals',
      'More institutions = more signals but also more potential noise',
      'Check institution filing history - some file more consistently than others',
    ],
  },

  3: {
    stepTitle: 'Entry & Position Sizing',
    stepNumber: 3,
    overview: 'Configure how the strategy enters positions and allocates capital. PathVest uses static 5% position sizing with rank-based buffering to minimize portfolio churn.',
    sections: [
      {
        title: 'Static Position Sizing (5%)',
        icon: '📏',
        content: `
          <p class="mb-2">Each position receives <strong>5% of portfolio capital</strong> (per SRS FR-3.1.C.10). This ensures:</p>
          <ul class="text-sm space-y-1 ml-4">
            <li>• <strong>Diversification:</strong> 5-20 stocks max</li>
            <li>• <strong>Risk management:</strong> No single position dominates</li>
            <li>• <strong>Consistent allocation:</strong> Equal-weight portfolio</li>
          </ul>
        `,
      },
      {
        title: 'Rank Buffer (B=5)',
        icon: '🛡️',
        content: `
          <p class="mb-2">Prevents excessive trading due to small ranking changes. A stock must drop <strong>5+ ranks</strong> below the portfolio size limit to trigger a sell.</p>
          <p class="text-sm text-gray-600">Example: If max positions = 20, a stock ranked #23 is kept (within buffer), but #26 is sold.</p>
        `,
      },
      {
        title: 'Entry Signals',
        icon: '🎯',
        content: `
          <p class="mb-2">Positions are entered when stocks meet signal criteria:</p>
          <ul class="text-sm space-y-1 ml-4">
            <li>• <strong>Signal A:</strong> Doubling Down (≥100% position increase + price < cost basis)</li>
            <li>• <strong>Signal B:</strong> Insider Buying (C-level executive purchases)</li>
            <li>• <strong>Signal C:</strong> Institutional Herding (2+ institutions buying within 30 days)</li>
          </ul>
          <p class="text-sm text-gray-600 mt-2">Plus optional technical confirmation: price breakout, SMA trend, RSI momentum</p>
        `,
      },
    ],
    technicalDetails: {
      backend: [
        'StaticPositionSizer class enforces 5% allocation per position',
        'Rank buffer logic prevents churn: keeps positions within B=5 ranks',
        'Min/max constraints enforced: 5-20 stocks in portfolio',
        'Cash drag management: if <5 candidates, stays 100% cash',
      ],
      frontend: [
        'Visual representation of position allocation (pie chart)',
        'Toggle switches for entry signal types',
        'Rank buffer slider with real-time impact preview',
      ],
      dataFlow: [
        'Signal Engine generates ranked candidates list',
        'Position Sizer calculates 5% allocation for top N candidates',
        'Rank buffer filters out positions falling >5 ranks below limit',
        'Trade orders generated for new entries and forced exits',
      ],
    },
    tips: [
      'Rank buffer (B=5) significantly reduces turnover costs - don\'t disable it',
      'Static 5% sizing is conservative - perfect for following institutional moves',
      'If you see frequent rebalancing, consider increasing the rank buffer',
      'Watch for cash drag - if signals are sparse, portfolio may stay in cash',
    ],
  },

  4: {
    stepTitle: 'Entry Scheduling Rules',
    stepNumber: 4,
    overview: 'Define timing rules for entering positions. Configure execution delays, batch entry constraints, and filing-to-trade lag to simulate realistic institutional following.',
    sections: [
      {
        title: 'Execution Delay (T+1)',
        icon: '⏰',
        content: `
          <p class="mb-2">Realistic execution timing: trades execute at <strong>next day's open</strong>, not instantaneously. This prevents look-ahead bias.</p>
          <p class="text-sm text-gray-600">If a signal fires on Monday close, the position is entered at Tuesday open.</p>
        `,
      },
      {
        title: 'Filing-to-Trade Lag',
        icon: '📆',
        content: `
          <p class="mb-2">SEC 13F filings are public information, but there's a lag between:</p>
          <ul class="text-sm space-y-1 ml-4">
            <li>• <strong>Quarter End:</strong> When the institution held the position</li>
            <li>• <strong>Filing Date:</strong> When it becomes public (45 days later)</li>
            <li>• <strong>Trade Date:</strong> When you can act on it (T+1)</li>
          </ul>
          <p class="text-sm text-amber-700 mt-2">💡 PathVest uses filing date for point-in-time accuracy - no cheating!</p>
        `,
      },
      {
        title: 'Batch Entry Constraints',
        icon: '📦',
        content: `
          <p class="mb-2">Optionally limit how many positions can be entered per day/week to simulate capital constraints or gradual deployment.</p>
          <p class="text-sm">Default: No constraint (enter all qualified signals immediately)</p>
        `,
      },
    ],
    technicalDetails: {
      backend: [
        'Event-driven simulation with chronological filing date ordering',
        'T+1 execution: trades scheduled for next market day open',
        'Filing date extraction from BigQuery sec_filings_13f table',
        'Market calendar validation (skips weekends, holidays)',
      ],
      frontend: [
        'Calendar visualization of filing dates and trade dates',
        'Execution delay slider (T+0 to T+5)',
        'Batch entry toggle with max positions/day input',
      ],
      dataFlow: [
        'Signal Engine emits signals with filing_date timestamp',
        'Backtest Executor queues trades for next_market_day + T+1',
        'AlphaVantage market data fetched for execution day open price',
        'Trade recorded with realistic slippage and commission',
      ],
    },
    tips: [
      'Keep T+1 execution delay for realistic results - removing it inflates returns',
      'Filing lag is automatic and mandatory - SEC regulations require it',
      'Batch entry constraints are optional but useful for stress testing liquidity',
      'Review trade timing in the "Trades" tab to verify no look-ahead bias',
    ],
  },

  5: {
    stepTitle: 'Exit Model Configuration',
    stepNumber: 5,
    overview: 'Define when and why to exit positions. PathVest implements 4 exit modules: Thesis Drift, Insider Reversal, Trailing Stop, and Dead Money. Each has specific trigger conditions.',
    sections: [
      {
        title: 'Module 1: Thesis Drift',
        icon: '🔄',
        content: `
          <p class="mb-2"><strong>Trigger:</strong> The triggering institution reduces their position by ≥50%</p>
          <p class="text-sm text-gray-600">If you entered AAPL because Berkshire doubled down, but Berkshire later cuts their stake in half, the original thesis is invalidated.</p>
          <p class="text-sm mt-2"><strong>Priority:</strong> Mandatory (highest priority)</p>
        `,
      },
      {
        title: 'Module 2: Insider Reversal',
        icon: '👔',
        content: `
          <p class="mb-2"><strong>Trigger:</strong> C-level executives sell ≥2 insider transactions within 30 days</p>
          <p class="text-sm text-gray-600">Insider selling often signals deteriorating fundamentals or overvaluation. Form 4 filings provide real-time insider activity.</p>
          <p class="text-sm mt-2"><strong>Priority:</strong> High</p>
        `,
      },
      {
        title: 'Module 3: Trailing Stop/Take-Profit',
        icon: '🎯',
        content: `
          <p class="mb-2"><strong>Stop Loss:</strong> Exit if position drops ≥15% from entry (default, configurable)</p>
          <p class="mb-2"><strong>Take Profit:</strong> Exit if position gains ≥50% (default, configurable)</p>
          <p class="mb-2"><strong>Trailing Stop:</strong> Stop loss rises as position appreciates, locking in gains</p>
          <p class="text-sm mt-2"><strong>Priority:</strong> Medium</p>
        `,
      },
      {
        title: 'Module 4: Dead Money Exit',
        icon: '💀',
        content: `
          <p class="mb-2"><strong>Trigger:</strong> Position held for 4+ quarters with negative return</p>
          <p class="text-sm text-gray-600">Cuts stagnant positions that aren't working out. Frees capital for better opportunities.</p>
          <p class="text-sm mt-2"><strong>Priority:</strong> Low (only if no other signals)</p>
        `,
      },
    ],
    technicalDetails: {
      backend: [
        'ExitOrchestrator coordinates all 4 modules with priority queue',
        'ThesisDriftModule queries 13F filings for position history changes',
        'InsiderReversalModule monitors Form 4 filings for C-level sells',
        'TrailingStopModule tracks high water marks and % drawdowns',
        'DeadMoneyModule calculates holding period and cumulative return',
      ],
      frontend: [
        'Exit module enable/disable toggles',
        'Parameter sliders for stop loss, take profit, holding period',
        'Visual priority order with drag-and-drop reordering (future)',
      ],
      dataFlow: [
        'Each module independently checks exit conditions on every event',
        'ExitOrchestrator collects exit signals and deduplicates',
        'Highest priority exit wins if multiple signals fire',
        'Exit reason recorded in trades table for attribution analysis',
      ],
    },
    tips: [
      'Thesis Drift is mandatory and catches the most important red flag',
      'Tighten stop losses (10-12%) for volatile stocks to preserve capital',
      'Widen take profits (70-100%) for high-conviction long-term holds',
      'Dead Money exit is a safety net - tune holding period based on strategy horizon',
    ],
  },

  6: {
    stepTitle: 'Risk Management Rules',
    stepNumber: 6,
    overview: 'Configure portfolio-level risk controls including rebalancing frequency, cash drag management, concentration limits, and volatility constraints.',
    sections: [
      {
        title: 'Rebalancing Logic',
        icon: '⚖️',
        content: `
          <p class="mb-2">Periodically adjust position sizes back to target 5% allocation:</p>
          <ul class="text-sm space-y-1 ml-4">
            <li>• <strong>Monthly:</strong> Rebalance on first trading day of each month</li>
            <li>• <strong>Quarterly:</strong> Align with 13F filing cadence (default)</li>
            <li>• <strong>Never:</strong> Let winners run, no rebalancing</li>
          </ul>
          <p class="text-sm text-gray-600 mt-2">Rank buffer applies to rebalancing too - prevents over-trading.</p>
        `,
      },
      {
        title: 'Cash Drag Management',
        icon: '💵',
        content: `
          <p class="mb-2"><strong>Rule:</strong> If fewer than 5 qualified candidates, stay 100% cash</p>
          <p class="text-sm text-gray-600">Prevents forced allocation to weak signals. Cash drag reduces returns when signal quality is poor, but protects capital.</p>
          <p class="text-sm mt-2">Monitor "Cash Allocation Over Time" chart to track deployment.</p>
        `,
      },
      {
        title: 'Concentration Limits',
        icon: '📊',
        content: `
          <p class="mb-2">Enforces maximum exposure per:</p>
          <ul class="text-sm space-y-1 ml-4">
            <li>• <strong>Single position:</strong> 5% (static sizing)</li>
            <li>• <strong>Single sector:</strong> 30% (optional constraint)</li>
            <li>• <strong>Single institution's picks:</strong> No limit by default</li>
          </ul>
        `,
      },
    ],
    technicalDetails: {
      backend: [
        'Rebalancing triggered on schedule: first_day_of_month or first_day_of_quarter',
        'Cash drag logic: if len(candidates) < 5: cash_allocation = 100%',
        'Position size drift calculation: abs(current_weight - target_weight) > 2%',
        'Sector exposure tracking via GICS classification (if enabled)',
      ],
      frontend: [
        'Rebalancing frequency dropdown (Monthly/Quarterly/Never)',
        'Cash drag threshold slider (3-7 minimum candidates)',
        'Sector concentration toggle with max % input',
      ],
      dataFlow: [
        'Backtest Executor checks rebalance schedule on every date tick',
        'Position Sizer calculates rebalance trades to restore 5% allocation',
        'Rank buffer prevents selling positions within buffer zone',
        'Rebalance trades executed at next day open with slippage/commissions',
      ],
    },
    tips: [
      'Quarterly rebalancing aligns well with 13F filing cadence',
      'If using momentum strategies, consider "Never" rebalance to let winners run',
      'Cash drag is a feature, not a bug - it prevents bad trades in weak markets',
      'Watch transaction costs - frequent rebalancing eats into returns',
    ],
  },

  7: {
    stepTitle: 'Parameters (Fine-Tuning)',
    stepNumber: 7,
    overview: 'Fine-tune strategy parameters like stop loss percentages, take profit targets, technical indicator thresholds, and signal confirmation requirements. These parameters are tested via sensitivity analysis.',
    sections: [
      {
        title: 'Stop Loss & Take Profit',
        icon: '🎚️',
        content: `
          <p class="mb-2">Adjust risk/reward thresholds:</p>
          <ul class="text-sm space-y-1 ml-4">
            <li>• <strong>Stop Loss:</strong> 10%, 15% (default), 20%</li>
            <li>• <strong>Take Profit:</strong> 30%, 50% (default), 70%, 100%</li>
            <li>• <strong>Trailing Stop:</strong> Enable/disable + lockup period</li>
          </ul>
          <p class="text-sm text-gray-600 mt-2">Tighter stops = more trades, lower max drawdown. Wider targets = fewer trades, higher potential upside.</p>
        `,
      },
      {
        title: 'Technical Indicator Thresholds',
        icon: '📈',
        content: `
          <p class="mb-2">Optional technical confirmation filters:</p>
          <ul class="text-sm space-y-1 ml-4">
            <li>• <strong>SMA Trend:</strong> Require price > 50 SMA and/or 200 SMA</li>
            <li>• <strong>RSI Momentum:</strong> 30 ≤ RSI ≤ 70 (avoid extremes)</li>
            <li>• <strong>Price Breakout:</strong> Require 20-day high</li>
          </ul>
          <p class="text-sm text-gray-600 mt-2">Adding filters reduces signal count but may improve quality.</p>
        `,
      },
      {
        title: 'Signal Confirmation Requirements',
        icon: '✅',
        content: `
          <p class="mb-2">How many signals must fire to trigger entry:</p>
          <ul class="text-sm space-y-1 ml-4">
            <li>• <strong>Any 1 signal:</strong> Maximum signals (default)</li>
            <li>• <strong>2+ signals:</strong> Higher conviction, fewer trades</li>
            <li>• <strong>All 3 signals:</strong> Rare, high-conviction only</li>
          </ul>
        `,
      },
      {
        title: 'Transaction Costs',
        icon: '💸',
        content: `
          <p class="mb-2">Simulate realistic trading costs:</p>
          <ul class="text-sm space-y-1 ml-4">
            <li>• <strong>Commission:</strong> $0 (zero-commission default), or $5-10/trade</li>
            <li>• <strong>Slippage:</strong> 0.05% (5 bps default), adjustable</li>
          </ul>
          <p class="text-sm text-amber-700 mt-2">⚠️ Don't ignore transaction costs - they compound over time!</p>
        `,
      },
    ],
    technicalDetails: {
      backend: [
        'Parameter Sensitivity Analyzer tests 2D grid of parameter combinations',
        'Heatmap generation: X-axis = stop_loss, Y-axis = take_profit, Z-axis = Sharpe',
        'Transaction costs applied on every trade: slippage = fill_price * (1 + slippage_pct)',
        'Technical filters evaluated using AlphaVantage SMA/RSI indicators',
      ],
      frontend: [
        'Slider controls for all numeric parameters with live preview',
        'Toggle switches for binary parameters (enable/disable filters)',
        'Parameter sensitivity heatmap visualization (Plotly.js)',
      ],
      dataFlow: [
        'User adjusts parameters → Updates config.parameters object',
        'Backtest runs with selected parameters',
        'Sensitivity analysis (optional): runs N backtests with parameter variations',
        'Results displayed as heatmap showing optimal parameter zones',
      ],
    },
    tips: [
      'Run Parameter Sensitivity Analysis to find optimal stop/profit levels for your data',
      'Conservative: 15% stop, 50% profit. Aggressive: 10% stop, 100% profit.',
      'Technical filters work well in trending markets, hurt in choppy markets',
      'Always include realistic transaction costs - 0.05% slippage is standard',
    ],
  },

  8: {
    stepTitle: 'Review & Backtest Confirmation',
    stepNumber: 8,
    overview: 'Final review of your complete strategy configuration before running the backtest. Verify all parameters, estimate execution time, and choose validation methods.',
    sections: [
      {
        title: 'Configuration Summary',
        icon: '📋',
        content: `
          <p class="mb-2">Review all 7 previous steps in a consolidated view:</p>
          <ul class="text-sm space-y-1 ml-4">
            <li>• Strategy name, engine, period, capital</li>
            <li>• Selected institutions and filters</li>
            <li>• Entry/exit rules and position sizing</li>
            <li>• Risk management and parameters</li>
          </ul>
          <p class="text-sm text-gray-600 mt-2">Click any section to edit before running.</p>
        `,
      },
      {
        title: 'Backtest Execution Estimate',
        icon: '⏱️',
        content: `
          <p class="mb-2">Estimated time based on configuration:</p>
          <ul class="text-sm space-y-1 ml-4">
            <li>• <strong>Custom Engine:</strong> 2-4 minutes (depends on max_positions)</li>
            <li>• <strong>LEAN Engine:</strong> 3-5 minutes (includes Docker setup)</li>
          </ul>
          <p class="text-sm text-gray-600 mt-2">AlphaVantage API rate limit (5 calls/min) is the primary bottleneck.</p>
        `,
      },
      {
        title: 'Validation Methods',
        icon: '🧪',
        content: `
          <p class="mb-2">Optionally run advanced validation (adds 5-15 minutes):</p>
          <ul class="text-sm space-y-1 ml-4">
            <li>• <strong>Monte Carlo Simulation:</strong> 1000 random paths to estimate probability cone</li>
            <li>• <strong>Walk-Forward Optimization:</strong> Train/test splits to avoid overfitting</li>
            <li>• <strong>Parameter Sensitivity:</strong> 2D heatmap of stop/profit combinations</li>
            <li>• <strong>Stress Testing:</strong> Performance during 2008, 2020, 2022 crises</li>
          </ul>
          <p class="text-sm text-amber-700 mt-2">💡 Run validation for strategies you plan to deploy with real money.</p>
        `,
      },
      {
        title: 'What Happens When You Click "Run Backtest"',
        icon: '🚀',
        content: `
          <ol class="text-sm space-y-2 ml-4 list-decimal">
            <li>Frontend sends POST /api/v1/backtest/submit with full config</li>
            <li>Backend saves strategy to SQLite database (for history tracking)</li>
            <li>Background task starts: fetches SEC filings from BigQuery</li>
            <li>Generates institutional signals (doubling down, herding, insider buying)</li>
            <li>Fetches market data from AlphaVantage API (respecting rate limits)</li>
            <li>Runs event-driven simulation with your entry/exit rules</li>
            <li>Calculates performance metrics (Sharpe, Sortino, Alpha, Max DD, etc.)</li>
            <li>Optionally runs validation modules (Monte Carlo, Walk-Forward, etc.)</li>
            <li>Returns results to frontend, updates database with backtest status</li>
            <li>Results page displays: Overview, Trades, Attribution, Validation tabs</li>
          </ol>
        `,
      },
    ],
    technicalDetails: {
      backend: [
        'POST /api/v1/backtest/submit → Creates backtest_id and saves to DB',
        'asyncio.create_task(process_backtest) → Background execution',
        'BigQuery queries: sec_filings_13f, sec_holdings_13f, institutional_holdings',
        'AlphaVantage API: TIME_SERIES_DAILY_ADJUSTED for each ticker',
        'Backtest Orchestrator: event-driven loop with chronological execution',
        'Result storage: SQLite (strategy_db) + in-memory cache',
      ],
      frontend: [
        'Polling mechanism: checks /api/v1/backtest/status every 2 seconds',
        'Loading screen with real-time progress updates (%, current stock, tips)',
        'Results page with 5 tabs: Summary, Overview, Trades, Attribution, Validation',
        'Plotly.js visualizations: equity curve, drawdown, Monte Carlo cone, heatmaps',
      ],
      dataFlow: [
        '1. User clicks "Run Backtest" → POST config to backend',
        '2. Backend validates config and creates backtest record',
        '3. Background task: SEC data → Signal Engine → Market data → Backtest Executor',
        '4. Results calculated: performance metrics, trade list, attribution, validation',
        '5. Frontend polls status, displays progress, shows results when complete',
        '6. Strategy saved to "My Strategies" for future reference',
      ],
    },
    tips: [
      'Always review the configuration summary before running - small errors compound',
      'Start with no validation to see basic results fast, then re-run with validation',
      'Watch the progress screen - if market data fetching stalls, check AlphaVantage status',
      'Save successful strategies for later comparison and iterative improvement',
      'Export results to CSV for external analysis in Excel/Python',
    ],
  },
};

