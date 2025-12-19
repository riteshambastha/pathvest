# 🔧 Fix: Institutions Not Being Extracted from Strategy Config

## Issue Summary

**Problem**: Backtests were showing:
- ✅ API Calls: **0**
- ✅ SEC Filings: **0**  
- ✅ Stocks: **N/A**
- ✅ Institutions tracked: **0**

Even when users **selected institutions** in Step 2 of the Strategy Builder.

## Root Cause Analysis

### 🎯 The Mismatch

**Frontend stores institutions at:**
```typescript
// Step2_StockSelection.tsx (line 49-54)
updateConfig({
  sub_universe_filters: {
    ...config.sub_universe_filters,
    selected_institutions: newSelection  // ← HERE!
  }
});
```

**Backend was looking in:**
```python
# backend/app/api/v1/endpoints/backtest.py
# ❌ Only checked these two locations:
if 'stock_selection' in config_dict:
    selected_institutions = config_dict['stock_selection'].get('selected_institutions', [])
elif 'selected_institutions' in config_dict:
    selected_institutions = config_dict['selected_institutions']

# ✅ Never checked 'sub_universe_filters'!
```

### 📊 Evidence from API

**Strategy saved to database:**
```json
{
  "id": 10,
  "name": "My Strategy",
  "selected_institutions": [],  // ← EMPTY!
  "strategy_config": {
    "sub_universe_filters": {
      "selected_institutions": ["0001067983", "0001350694"]  // ← ACTUAL DATA HERE!
    }
  }
}
```

**Result:**
- Backend extracted `[]` (empty array)
- Queries like `WHERE cik IN ()` returned 0 results
- No stocks, no filings, no API calls

---

## ✅ The Fix

### Files Modified

1. **`backend/app/api/v1/endpoints/backtest.py`**
   - Function: `run_backtest()` (line ~91-110)
   - Function: `_generate_fallback_result()` (line ~570-583)

2. **`backend/lean_engine/worker/backtest_worker.py`**
   - Function: `_fetch_required_data()` (line ~261-274)

### Changes Made

Added check for `sub_universe_filters` in the institution extraction logic:

```python
# Extract selected institutions from the request
selected_institutions = []
config_dict = request.strategy_config.dict()

# Try multiple locations where institutions might be stored:
# 1. In stock_selection
if 'stock_selection' in config_dict and isinstance(config_dict['stock_selection'], dict):
    selected_institutions = config_dict['stock_selection'].get('selected_institutions', [])
# 2. In sub_universe_filters (frontend stores here!) ✨ NEW
elif 'sub_universe_filters' in config_dict and isinstance(config_dict['sub_universe_filters'], dict):
    selected_institutions = config_dict['sub_universe_filters'].get('selected_institutions', [])
# 3. Directly in config
elif 'selected_institutions' in config_dict:
    selected_institutions = config_dict['selected_institutions']

print(f"📊 Extracted {len(selected_institutions)} institutions from config: {selected_institutions}")
```

---

## 🧪 Testing the Fix

### Step 1: Deploy to Render

```bash
git add -A
git commit -m "Fix: Extract institutions from sub_universe_filters"
git push origin main
```

Wait for Render auto-deployment (~3-5 minutes).

### Step 2: Create New Backtest

1. Go to https://pathvest.vercel.app/builder
2. Complete Step 1 (strategy name, dates, capital)
3. **Step 2**: Click checkboxes to select 2-3 institutions:
   - ✅ Berkshire Hathaway
   - ✅ Bridgewater Associates
   - ✅ Renaissance Technologies
4. Complete Steps 3-8
5. Click "Run Backtest"

### Step 3: Expected Results

After deployment, you should see:

```
✅ API Calls: 25-50 (depending on stocks and date range)
✅ SEC Filings: 40-80 (quarterly 13F filings)
✅ Stocks: 30-60 (top holdings from selected institutions)
✅ Institutions tracked: 3
```

**Backend logs should show:**
```
📊 Extracted 3 institutions from config: ['0001067983', '0001350694', '0001037389']
📊 Fetching REAL data for 3 institutions from database...
✅ Found 47 REAL SEC filings in database
✅ Extracted 38 REAL stocks from institutional holdings
✅ Would make ~42 API calls for price data
```

---

## ⚠️ Important Note: Database Must Have Data

The fix enables proper institution extraction, but **you still need SEC data in the database**.

### Check if Database Has Data

Run in Render shell:
```bash
# SSH into Render shell
# In your backend container:
python3 -c "
from app.services.strategy_db import SessionLocal
from sqlalchemy import text

db = SessionLocal()
holdings = db.execute(text('SELECT COUNT(*) FROM sec_holdings_13f')).scalar()
filings = db.execute(text('SELECT COUNT(*) FROM sec_filings_13f')).scalar()
institutions = db.execute(text('SELECT COUNT(*) FROM sec_institutions')).scalar()

print(f'Institutions: {institutions}')
print(f'Filings: {filings}')
print(f'Holdings: {holdings}')
db.close()
"
```

**Expected output:**
```
Institutions: 10-50
Filings: 100-500
Holdings: 1000-10000
```

If all are **0**, you need to seed the database first. See `DEPLOYMENT_GUIDE.md` for seeding instructions.

---

## 📝 Related Files

- Frontend: `frontend/src/components/strategy/steps/Step2_StockSelection.tsx`
- Backend API: `backend/app/api/v1/endpoints/backtest.py`
- Worker: `backend/lean_engine/worker/backtest_worker.py`
- Database Models: `backend/app/services/strategy_db.py`

---

## 🎯 Commit

```bash
git commit: aa3dfa8
Message: "Fix: Extract institutions from sub_universe_filters"
```

---

## ✅ Checklist

- [x] Identified root cause (frontend/backend mismatch)
- [x] Fixed `run_backtest()` in backtest.py
- [x] Fixed `_generate_fallback_result()` in backtest.py
- [x] Fixed `_fetch_required_data()` in backtest_worker.py
- [x] Committed changes
- [ ] Pushed to GitHub
- [ ] Verified Render deployment
- [ ] Tested with new backtest
- [ ] Confirmed real data appears (not 0s)

---

**Status**: ✅ Fix complete, ready for deployment and testing

