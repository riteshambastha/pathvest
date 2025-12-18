 alembic upgrade head
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
/root/.local/lib/python3.11/site-packages/alembic/script/revision.py:214: UserWarning: Revision f1a2b3c4d5e6 is present more than once
  util.warn(
ERROR [alembic.util.messaging] Multiple head revisions are present for given argument 'head'; please specify a specific target revision, '<branchname>@head' to narrow to a specific head, or 'heads' for all heads
  FAILED: Multiple head revisions are present for given argument 'head'; please specify a specific target revision,
  '<branchname>@head' to narrow to a specific head, or 'heads' for all heads
root@srv-d51eqs63jp1c739ve47g-6d845855d8-z6p94:/app# # Quick Fix for Render Deployment Error

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

# First, remove the duplicate migration file
rm -f alembic/versions/f1a2b3c4d5e6_add_strategies_sqlite.py

# Check current migration state
alembic current

# Now run the migration to the specific revision
alembic upgrade 483ddf2ccfc5
```

**Expected output**:
```
INFO  [alembic.runtime.migration] Running upgrade f1a2b3c4d5e6 -> 483ddf2ccfc5, add_filing_date_column
```

---

## ✅ Test It Works

**From your local terminal** (not Render Shell):

```bash
# Replace with your Render URL
curl https://pathvest-backend.onrender.com/api/v1/data/date-range

# Should return JSON with date range (no errors!)
```

Or open in your browser:
```
https://pathvest-backend.onrender.com/api/v1/data/date-range
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

