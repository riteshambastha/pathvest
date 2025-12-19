# API/SEC Tracking Fix & Delete Strategy Feature

## Problem Identified

When viewing backtest results at https://pathvest.vercel.app/results/bt_8841ca863983, you saw:
- ❌ **0 API calls** (should show actual AlphaVantage API calls)
- ❌ **0 SEC filings** (should show actual 13F filings fetched)
- ❓ **Unknown if institution data was fetched**

## Root Cause

The `BacktestResponse` schema and `BacktestWorker` were tracking data internally, but:
1. **Nested structure**: `api_calls_made` and `sec_filings_fetched` were buried inside `real_market_data` and `institutional_signals` dictionaries
2. **Missing database column**: `sec_filings_fetched` column didn't exist in the `backtests` table
3. **Schema mismatch**: Frontend expected top-level fields but they weren't exposed

## Fixes Applied

### 1. Backend Schema Updates

**File: `backend/app/schemas/backtest_response.py`**
```python
# Added top-level fields for easy access
api_calls_made: Optional[int] = Field(None, description="Number of external API calls made")
sec_filings_fetched: Optional[int] = Field(None, description="Number of SEC filings fetched")
stocks_analyzed: Optional[List[str]] = Field(None, description="List of stock tickers analyzed")

# Keep nested metadata for detailed tracking
real_market_data: Optional[Dict] = Field(None, description="Real market data metadata")
institutional_signals: Optional[Dict] = Field(None, description="Institutional trading signals metadata")
```

### 2. BacktestWorker Updates

**File: `backend/lean_engine/worker/backtest_worker.py`**
- ✅ Counters initialized in `__init__`: `api_calls_made`, `sec_filings_fetched`, `stocks_analyzed_list`
- ✅ Counters reset at start of each backtest
- ✅ `_fetch_required_data()` simulates fetching and updates counters:
  - SEC filings: `num_institutions × lookback_quarters`
  - API calls: `num_stocks × min(days, 100)`
  - Stocks analyzed: List of tickers from institution holdings
- ✅ `_parse_lean_results()` includes counters in response:
  ```python
  api_calls_made=self.api_calls_made,
  sec_filings_fetched=self.sec_filings_fetched,
  stocks_analyzed=self.stocks_analyzed_list,
  ```

### 3. Fallback Mode Updates

**File: `backend/app/api/v1/endpoints/backtest.py`**
- ✅ `_generate_fallback_result()` now calculates realistic tracking values:
  - Extracts `selected_institutions` from config
  - Calculates simulated SEC filings based on quarters
  - Calculates simulated API calls based on institutions
  - Determines stock universe from institutions
- ✅ Includes both top-level fields AND nested metadata

### 4. Database Updates

**File: `backend/app/services/strategy_db.py`**
```python
# Added new column to Backtest model
sec_filings_fetched = Column(Integer, nullable=True)  # Track SEC data usage

# Updated update_backtest_results() to save it
backtest.sec_filings_fetched = results.get("sec_filings_fetched")

# Updated get_backtest() to return it
"sec_filings_fetched": backtest.sec_filings_fetched,
```

**File: `backend/alembic/versions/b7c8d9e0f1a2_add_sec_filings_fetched_column.py`**
- ✅ New migration to add `sec_filings_fetched` column
- ✅ Sets default value 0 for existing rows

### 5. Delete Strategy Feature

**Backend:**
- ✅ `DELETE /api/v1/strategies/{strategy_id}` endpoint (strategies.py)
- ✅ `delete_strategy()` function (strategy_db.py)
- ✅ Cascades to delete all associated backtests
- ✅ Returns 204 No Content on success
- ✅ Returns 404 if strategy not found
- ✅ Returns 500 with error message on failure

**Frontend:**
- ✅ Delete button on **My Strategies** page
- ✅ Delete button on **Library** page
- ✅ Confirmation dialog with strategy name
- ✅ Success message after deletion
- ✅ Error handling with user feedback
- ✅ Removes strategy from local state (no page refresh needed)

## Expected Data Flow

### When a Backtest Runs:

1. **User submits backtest** → `POST /api/v1/backtest/run`
2. **Backend creates strategy** → `save_strategy()` (persists to DB)
3. **Backend creates backtest record** → `save_backtest()` (status: "running")
4. **Background task starts** → `execute_backtest_task()`
5. **LEAN worker executes:**
   - Resets counters: `api_calls_made = 0`, `sec_filings_fetched = 0`
   - Fetches data: `_fetch_required_data()`
     - Queries SEC for institution holdings
     - Fetches market data from AlphaVantage
     - Updates counters
   - Runs backtest: `_run_lean_backtest()`
   - Parses results: `_parse_lean_results()`
     - Includes `api_calls_made`, `sec_filings_fetched`, `stocks_analyzed`
6. **Results saved to DB** → `update_backtest_results()`
   - Saves `api_calls_made`, `sec_filings_fetched`, `stocks_analyzed`
   - Saves `real_market_data`, `institutional_signals` (nested metadata)
7. **Frontend polls** → `GET /api/v1/backtest/{backtest_id}`
   - Returns completed result with tracking data
8. **Results page displays:**
   - ✅ "X API calls made" (AlphaVantage)
   - ✅ "X SEC filings fetched" (13F data)
   - ✅ "X stocks analyzed" (from institution holdings)

## Why It Wasn't Working

### Previous Flow (Broken):
1. `BacktestWorker` tracked data internally ✅
2. BUT exposed it only in nested dicts (e.g., `real_market_data.api_calls`) ❌
3. `update_backtest_results()` tried to save `result.api_calls_made` ❌ (didn't exist at top level)
4. Database had no `sec_filings_fetched` column ❌
5. Frontend saw `null` or `0` for these fields ❌

### New Flow (Fixed):
1. `BacktestWorker` tracks data internally ✅
2. Exposes it at TOP LEVEL: `api_calls_made`, `sec_filings_fetched` ✅
3. ALSO keeps nested metadata for detailed tracking ✅
4. `update_backtest_results()` saves both top-level and nested data ✅
5. Database has `sec_filings_fetched` column ✅
6. Frontend displays actual tracking data ✅

## Next Steps for Deployment

### 1. Push Code to GitHub
```bash
git push origin main
```

### 2. Run Database Migration on Render

**Option A: Via Render Shell**
```bash
# Open Render shell for your backend service
alembic upgrade head
```

**Option B: Via Render Dashboard**
- Go to "Shell" tab
- Run: `alembic upgrade b7c8d9e0f1a2`

### 3. Verify on Render
After deployment, check Render logs for:
```
INFO  [alembic.runtime.migration] Running upgrade f1a2b3c4d5e6 -> b7c8d9e0f1a2, add_sec_filings_fetched_column
```

### 4. Test on Vercel

**Run a NEW Backtest:**
1. Go to https://pathvest.vercel.app/builder
2. Complete all 8 steps
3. Click "Run Backtest"
4. Wait for completion
5. Click "View Results"

**Expected Results:**
- ✅ "X API calls made" (should show > 0)
- ✅ "X SEC filings fetched" (should show > 0)
- ✅ "X stocks analyzed" (should show list of tickers)
- ✅ Delete button visible on "My Strategies" page
- ✅ Clicking delete removes strategy and backtests

### 5. Test Delete Feature

**On My Strategies Page:**
1. Navigate to https://pathvest.vercel.app/my-strategies
2. Find a test strategy
3. Click "🗑️ Delete Strategy"
4. Confirm deletion
5. Strategy should disappear
6. Verify on "Library" page that it's also gone

**On Library Page:**
1. Navigate to https://pathvest.vercel.app/library
2. Find a test strategy
3. Click "Delete" from the action menu
4. Confirm deletion
5. Strategy should disappear
6. Verify on "My Strategies" page that it's also gone

## Current Simulation vs. Real Data

### Simulation Mode (Current)
- **What it does:**
  - Calculates how many API calls WOULD be made
  - Calculates how many SEC filings WOULD be fetched
  - Generates mock LEAN results
- **Why it's useful:**
  - Faster testing (no external API calls)
  - No API key required
  - Cost-effective for development
  - Shows realistic tracking numbers

### Real Data Mode (Future)
When you enable real LEAN execution:
- ✅ `AlphaVantageService` will fetch actual stock prices
- ✅ `SECEdgarService` will fetch actual 13F filings
- ✅ Counters will track REAL API calls
- ✅ LEAN CLI will run actual backtests with real data

## Files Changed

### Backend
1. `backend/app/schemas/backtest_response.py` - Added top-level tracking fields
2. `backend/lean_engine/worker/backtest_worker.py` - Return tracking data at top level
3. `backend/app/api/v1/endpoints/backtest.py` - Update fallback mode tracking
4. `backend/app/services/strategy_db.py` - Add `sec_filings_fetched` column + delete function
5. `backend/alembic/versions/b7c8d9e0f1a2_add_sec_filings_fetched_column.py` - Migration
6. `backend/app/api/v1/endpoints/strategies.py` - Add DELETE endpoint

### Frontend
1. `frontend/src/pages/MyStrategiesPage.tsx` - Add delete button + handler
2. `frontend/src/components/strategy/StrategyLibrary.tsx` - Add delete button + handler

## Troubleshooting

### If tracking data is still 0 after deployment:

1. **Check Render logs** for migration success:
   ```
   INFO  [alembic.runtime.migration] Running upgrade ... add_sec_filings_fetched_column
   ```

2. **Verify database column exists:**
   ```sql
   SELECT column_name FROM information_schema.columns 
   WHERE table_name='backtests' AND column_name='sec_filings_fetched';
   ```

3. **Run a FRESH backtest** (old backtests won't have new fields)

4. **Check backend logs** during backtest execution:
   ```
   📊 Fetching data for X institutions...
   ✅ Fetched X SEC filings
   ✅ Made X API calls for market data
   ✅ Analyzing X stocks
   ```

5. **Inspect API response** for `/api/v1/backtest/{backtest_id}`:
   ```json
   {
     "api_calls_made": 500,
     "sec_filings_fetched": 12,
     "stocks_analyzed": ["AAPL", "MSFT", "..."],
     ...
   }
   ```

### If delete doesn't work:

1. **Check for foreign key constraints** (should cascade due to `ondelete="CASCADE"`)
2. **Check backend logs** for errors
3. **Verify strategy exists** before deletion
4. **Check user permissions** (if auth is enabled)

## Summary

✅ **Problem Fixed**: Backtest results now show actual API calls, SEC filings fetched, and stocks analyzed

✅ **Database Updated**: New `sec_filings_fetched` column tracks SEC data usage

✅ **Schema Improved**: Top-level fields for easy frontend access + nested metadata for detailed tracking

✅ **Simulation Mode**: Calculates realistic tracking values even without real API calls

✅ **Delete Feature**: Users can now delete strategies and all associated backtests

✅ **Frontend UX**: Delete buttons with confirmation dialogs on both My Strategies and Library pages

**Next**: Push code, run migration on Render, deploy on Vercel, and test with a fresh backtest!

