# Progress Screen Showing Zeros - Root Cause Analysis

## Problem Statement
The progress/loading screen appears but shows:
- Stocks Fetched: **0**
- Institutions: **0**  
- Actions: **0**
- Progress stays at **0%** indefinitely

## Root Cause Found

The issue is a **cascade of failures**:

### 1. Backend Engine Issues (Primary Problem)
On Render, both LEAN engine and Custom engine are failing to initialize:

```
⚠️ LEAN worker not available: No module named 'lean_engine.worker'; 'lean_engine' is not a package
⚠️ Custom backtest engine not available
```

**Result:** Backend falls back to `_generate_fallback_result()` which creates **instant fake data**.

### 2. Institution Selection Not Being Passed (Secondary Problem)
The fallback result generator checks for institutions:

```python
if not selected_institutions:
    print("⚠️ No institutions selected in fallback mode")
    simulated_sec_filings = 0
    simulated_api_calls = 0
    stocks = []
```

**Result:** Even the fake data shows **zeros** because institutions aren't found.

### 3. Progress Screen Shows Completed Data Instantly
The backtest completes in <1 second with status='completed', so:
- Frontend polls `/backtest/{id}`
- Gets back completed results immediately
- Shows progress screen with the fake data (all zeros)
- Minimum 1.5s loading time displays but with no real progress

## The Data Flow (What's Actually Happening)

```
User clicks "Run Backtest"
    ↓
Frontend sends: { strategy_config: {..., sub_universe_filters: {selected_institutions: [...]} } }
    ↓
Backend receives request
    ↓
Tries to import LEAN engine → FAILS
    ↓
Tries to import Custom engine → FAILS  
    ↓
Falls back to _generate_fallback_result()
    ↓
Tries to extract institutions from config → NOT FOUND (or extraction logic fails)
    ↓
Sets: api_calls=0, sec_filings=0, stocks=[]
    ↓
Saves to database with status='completed'
    ↓
Frontend polls and gets 'completed' immediately
    ↓
Shows progress screen with zeros
```

## Debugging Steps Added

### Frontend (Step8_ReviewBacktest.tsx)
```javascript
console.log('🚀 Submitting backtest with config:', JSON.stringify(config, null, 2));
console.log('📊 Selected institutions:', config.sub_universe_filters?.selected_institutions);
```

### Backend (backtest.py endpoint)
```python
print(f"📊 Backtest {backtest_id} - Received config keys: {list(config_dict.keys())}")
print(f"📊 Extracted {len(selected_institutions)} institutions: {selected_institutions}")
if not selected_institutions:
    print("⚠️ WARNING: No institutions found!")
    print(f"⚠️ sub_universe_filters content: {config_dict.get('sub_universe_filters')}")
```

### Backend (start.sh)
```bash
# Lists lean_engine directory
# Tries to import lean_engine step by step
# Shows full traceback for import errors
```

## What to Check After Deployment

### 1. Check Render Startup Logs
Look for:
```
✅ lean_engine directory exists
✅ lean_engine/__init__.py exists  
✅ lean_engine imports successfully
✅ BacktestOrchestrator imports successfully
```

If you see errors, they'll tell us exactly what's missing.

### 2. Check Backtest Submission Logs (Backend)
When you submit a backtest, look for:
```
📊 Backtest bt_xxx - Received config keys: [...]
📊 Extracted 2 institutions: ['0001067983', '0001364742']
```

If you see:
```
⚠️ WARNING: No institutions found!
⚠️ sub_universe_filters content: {...}
```

Then institutions aren't in the config structure we expect.

### 3. Check Browser Console (Frontend)
When you click "Run Backtest", should see:
```
🚀 Submitting backtest with config: {...}
📊 Selected institutions: ['0001067983', '0001364742']
✅ Backtest submitted successfully. ID: bt_xxx
```

If `Selected institutions: []`, then Step 2 isn't saving selections.

## Expected Fixes in Progress

### Fix 1: LEAN Engine Import (Pending Deployment)
- Added `start.sh` with proper PYTHONPATH
- Added `beautifulsoup4` and `lxml` to requirements.txt
- Should fix: `'lean_engine' is not a package`

### Fix 2: Institution Selection Persistence (Already Deployed)
- Initialize `selectedInstitutions` from config prop
- Sync with config changes via useEffect  
- Save to localStorage as `strategyConfig`
- Should ensure institutions are in config when submitting

## Next Steps

1. **Push all commits:**
   ```bash
   git push origin main
   ```

2. **Wait for Render + Vercel deployment** (~5 minutes)

3. **Test full flow:**
   - Go to /builder
   - Select 2 institutions in Step 2
   - Open browser console
   - Complete strategy and click "Run Backtest"
   - Check console logs
   - Note the backtest ID
   
4. **Check Render logs** for that backtest ID:
   - Look for institution extraction logs
   - Look for which engine was used
   - Look for any import errors

5. **Share findings:**
   - Browser console output
   - Render backend logs
   - Screenshots of progress screen

## Possible Outcomes

### Outcome A: Institutions are passed but engines still fail
**Solution:** Fix the remaining import issues in LEAN/Custom engine

### Outcome B: Institutions still not in config
**Solution:** Fix the config structure or extraction logic

### Outcome C: Everything works!
**Celebration:** You'll see real progress with actual API calls being made

## Files Changed (Ready to Push)

1. `backend/start.sh` - Enhanced debugging
2. `backend/requirements.txt` - Added bs4, lxml
3. `backend/Dockerfile` - Fixed PYTHONPATH
4. `backend/app/api/v1/endpoints/backtest.py` - Added logging
5. `frontend/src/components/strategy/steps/Step8_ReviewBacktest.tsx` - Added logging
6. `frontend/src/components/strategy/steps/Step2_StockSelection.tsx` - Fixed initialization
7. `frontend/src/components/strategy/StrategyWizard.tsx` - Added localStorage
8. `frontend/src/pages/BacktestResultsPage.tsx` - Fixed progress display

All ready to push! 🚀

