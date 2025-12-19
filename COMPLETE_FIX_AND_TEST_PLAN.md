# Complete Fix and Test Plan

## Issues Fixed (In Order)

### 1. ✅ Missing 14 Required Pydantic Fields (Commit: 64a4a22)
**Problem**: `HistoricalBacktestEngine.calculate_metrics()` only returned 8 metrics, schema requires 21  
**Impact**: FastAPI returned 500 error, frontend showed zeros  
**Fix**: Added all 14 missing fields (cagr, volatility, romad, var_95, win_rates, etc.)

### 2. ✅ Response Structure Mismatch (Commit: 64a4a22)
**Problem**: Orchestrator returned metrics at top level, API expected them under `summary` key  
**Impact**: Converter function couldn't find metrics  
**Fix**: Wrapped metrics under `summary` key in orchestrator response

### 3. ✅ Database Retrieval Missing Fields (Commit: 27c7dba)
**Problem**: GET endpoint only returned 7 fields when fetching from DB  
**Impact**: 500 error after server restart when loading cached results  
**Fix**: Updated DB retrieval to include all 21 fields, check `summary_metrics` dict

### 4. ✅ TypeScript Compilation Error (Commit: a9e09a6)
**Problem**: Debug code tried to access non-existent `config.stock_selection` field  
**Impact**: Vercel build failed  
**Fix**: Removed invalid property access

### 5. ✅ Progress Screen Flash (Commit: dfdd71d)
**Problem**: Loading screen disappeared instantly for fast-completing backtests  
**Impact**: Users couldn't see progress details  
**Fix**: Added minimum display time (60s) + manual close button (10s)

### 6. ✅ Enhanced Progress Tracking (Commit: 353db70)
**Problem**: No visibility into what APIs were being called, success/failure status  
**Impact**: Hard to debug API issues  
**Fix**: Added detailed logging with color-coded messages (✅ green, ⚠️ amber, ❌ red)

### 7. ✅ Missing Pydantic Field (Commit: 85741b3)
**Problem**: `SubUniverseFilters` model missing `selected_institutions` field  
**Impact**: **Pydantic silently dropped institutions from requests!**  
**Fix**: Added `selected_institutions: List[str]` to model

### 8. ✅ Wrong SQL Column Names (Commit: 590a08b)
**Problem**: SQL query used `h.ticker_symbol` and `h.shares` which don't exist  
**Impact**: Database query failed with "column does not exist"  
**Fix**: Changed to correct column names: `h.ticker`, `h.shares_or_prn_amt`

---

## Database Schema (Reference)

### Holdings Table
```python
class Holding(Base):
    __tablename__ = "holdings"
    
    id: int
    filing_id: int (FK to filings)
    
    # Correct column names:
    ticker: str  # NOT ticker_symbol
    cusip: str
    name_of_issuer: str
    value: float  # in thousands
    shares_or_prn_amt: int  # NOT shares
    shares_or_prn_amt_type: str  # SH or PRN
    
    # Voting
    investment_discretion: str
    voting_authority_sole: int
    voting_authority_shared: int
    voting_authority_none: int
```

### Filings Table
```python
class Filing(Base):
    __tablename__ = "filings"
    
    id: int
    institution_id: int (FK to institutions)
    accession_no: str
    form_type: str
    filed_at: datetime
    filing_date: date
    period_of_report: str
    
    # URLs
    link_to_txt: str
    link_to_html: str
    link_to_filing_details: str
    
    # Summary
    total_holdings: int
    total_value: float
```

### Institutions Table
```python
class Institution(Base):
    __tablename__ = "institutions"
    
    id: int
    cik: str (unique)
    name: str
    description: str
    is_popular: bool
    aum: int (nullable)
```

---

## Current System Flow

```
1. Frontend (Vercel)
   └─ User selects 2 institutions in Step 2
   └─ config.sub_universe_filters.selected_institutions = ["0001067983", "0001061768"]
   └─ Submits to /api/v1/backtest/run

2. Backend (Render)
   └─ FastAPI receives request
   └─ Pydantic validates and parses
   └─ ✅ selected_institutions field now exists in model
   └─ Creates background task: execute_backtest_task()

3. Background Task
   └─ Extracts institutions from config.sub_universe_filters
   └─ Calls BacktestOrchestrator.run_strategy_backtest()
   
4. Orchestrator
   └─ fetch_sec_signals()
      └─ ✅ Query uses correct column names (ticker, shares_or_prn_amt)
      └─ Fetches holdings from PostgreSQL
      └─ Generates trading signals (BUY/SELL/DOUBLING_DOWN)
   └─ fetch_historical_prices_batch()
      └─ Calls AlphaVantage API (5 calls/min rate limit)
      └─ Fetches daily prices for each ticker
   └─ HistoricalBacktestEngine.run_backtest()
      └─ Simulates portfolio with real prices
      └─ ✅ Returns all 21 metrics
   └─ Wraps response with summary key
   
5. API Response
   └─ ✅ All 21 fields in summary
   └─ Converts to BacktestResponse
   └─ Saves to database
   └─ Returns 200 OK

6. Frontend
   └─ Progress screen displays for 60s minimum
   └─ Shows detailed progress with color-coded messages
   └─ Manual close button at 10s
   └─ Results page displays all metrics
```

---

## Testing Checklist

### Pre-Deployment Checks
- [x] All commits made
- [x] SQL column names verified against models
- [x] Pydantic models include all required fields
- [x] No hardcoded test data
- [ ] Ready to push

### After Deployment (Render + Vercel)

#### Test 1: Basic Backtest Flow
1. [ ] Go to https://pathvest.vercel.app/builder
2. [ ] Open browser console (F12)
3. [ ] Complete all steps, select 2 institutions in Step 2
4. [ ] Check localStorage shows `strategyConfig` with `selected_institutions`
5. [ ] Submit backtest
6. [ ] Progress screen appears
7. [ ] Wait 10 seconds → "View Results Now" button appears
8. [ ] Progress shows: "Querying 2 institutions" (not 0)
9. [ ] View results after 60s or click button
10. [ ] Results show real metrics (not zeros)

#### Test 2: Render Logs Verification
```bash
# Look for these in Render logs:

✅ GOOD SIGNS:
🔍 Config dict keys: [...]
📍 Found institutions in sub_universe_filters: ['0001067983', '0001061768']
📊 Using 2 institutions for custom backtest
🔍 Fetching SEC signals from database...
   Institutions: ['0001061768', '0001067983']... (2 total)
✅ Found X trading signals from Y positions
📊 Fetched prices for X stocks
📊 Backtest Results:
   Return:  X.XX%
   CAGR:    X.XX%

❌ BAD SIGNS (should NOT see):
❌ Could not find institutions anywhere!
⚠️ No institutions selected
column h.ticker_symbol does not exist
ResponseValidationError: 14 validation errors
```

#### Test 3: Progress Screen Visibility
- [ ] Progress screen visible for minimum 60 seconds
- [ ] Shows institution count (not 0)
- [ ] Shows each ticker being fetched
- [ ] Color-coded messages appear
- [ ] Success count increases
- [ ] If API key invalid: Shows ⚠️ warnings

#### Test 4: API Key Validation
If you see in progress log:
```
❌ AAPL: 401 Unauthorized
⚠️ Check ALPHAVANTAGE_API_KEY if many failures
```
→ API key needs to be set in Render environment variables

#### Test 5: Database Persistence
1. [ ] Complete a backtest
2. [ ] Note the backtest ID
3. [ ] In Render, click "Manual Deploy" → restart
4. [ ] Wait for restart
5. [ ] Go to results page with same backtest ID
6. [ ] Results should still load correctly (from database)

---

## Environment Variables to Check

### Render Dashboard
```bash
ALPHAVANTAGE_API_KEY=your_key_here
DATABASE_URL=postgresql://...
PYTHONUNBUFFERED=1
PYTHONDONTWRITEBYTECODE=1
```

### Testing AlphaVantage Key
```bash
curl "https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol=IBM&apikey=YOUR_KEY"
```

Should return JSON with stock prices, not:
```json
{
  "Error Message": "Invalid API call"
}
```

---

## Known Limitations

1. **AlphaVantage Rate Limit**: 5 calls/minute (free tier)
   - For 12 stocks: ~2.4 minutes
   - For 20 stocks: ~4 minutes
   
2. **Minimum Progress Display**: 60 seconds
   - Even if backtest completes in 5 seconds
   - Manual close after 10 seconds
   
3. **Database Must Be Seeded**: 
   - Need SEC 13F filings in database
   - Need ticker mappings for CUSIP→Ticker
   - Without data: "No signals found"

---

## If Something Still Breaks

### Step 1: Check Render Logs
```bash
# Look for the exact error message
# Common issues:
- Import errors → Check PYTHONPATH in start.sh
- Database errors → Check column names vs models
- Pydantic errors → Check all required fields
- API errors → Check environment variables
```

### Step 2: Check Frontend Console
```bash
# Look for:
- Network errors (500, 409, 404)
- Config being sent correctly
- Institutions array not empty
```

### Step 3: Test Locally
```bash
# Backend
cd backend
uvicorn app.main:app --reload

# Check:
- Can import all modules?
- Database connection works?
- Models match schema?
```

---

## Success Criteria

✅ **All of these must be true:**

1. Render logs show: `📊 Using 2 institutions for custom backtest`
2. Render logs show: `✅ Found X trading signals` (X > 0)
3. Render logs show: `✅ Fetched prices for X/Y stocks`
4. No SQL errors (`column does not exist`)
5. No Pydantic errors (`Field required`)
6. Frontend progress screen displays for 60s
7. Frontend shows real metrics (not all zeros)
8. Results persist after server restart

---

## Deployment Command

```bash
git push origin main
```

Then wait 5-7 minutes for both Vercel and Render to deploy.

