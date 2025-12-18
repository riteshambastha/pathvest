# Quick Fix for Render Deployment Error

## ✅ Problem Solved

**Error**: `column "filing_date" does not exist`

**Root Cause**: 
1. Alembic wasn't importing SEC models → tables not fully created
2. Code uses `filing_date` but model only had `filed_at`

---

## 🚀 Deploy the Fix (3 Steps)

### 1. Commit Changes

```bash
cd /Users/riteshambastha/projects/pathvest

git add .
git commit -m "Fix: Add filing_date column and update alembic imports"
git push origin main
```

### 2. Wait for Render Auto-Deploy

- Go to: https://dashboard.render.com
- Watch your `pathvest-backend` service deploy (~2-3 minutes)
- Wait for "Live" status

### 3. Run Migration on Render

**In Render Dashboard**:
1. Click your `pathvest-backend` service
2. Click **"Shell"** tab (top right)
3. Run these commands:

```bash
cd backend
alembic upgrade head
```

**Expected output**:
```
INFO  [alembic.runtime.migration] Running upgrade f1a2b3c4d5e6 -> 483ddf2ccfc5, add_filing_date_column
```

---

## ✅ Test It Works

```bash
# Replace with your Render URL
curl https://pathvest-backend.onrender.com/api/v1/data/date-range

# Should return JSON with date range (no errors!)
```

---

## 📝 What Changed

### Files Modified:
1. **`backend/alembic/env.py`** - Now imports all models
2. **`backend/app/models/filing.py`** - Added `filing_date` column
3. **`backend/alembic/versions/483ddf2ccfc5_add_filing_date_column.py`** - New migration

### Database Changes:
- Added `filing_date DATE` column to `filings` table
- Populated from existing `filed_at` data
- Created index for performance

---

## 🎯 That's It!

After these 3 steps, your Render deployment should work perfectly.

**Questions?** Check the full guide: `RENDER_DEPLOYMENT_GUIDE.md`

