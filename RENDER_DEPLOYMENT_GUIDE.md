# Render Deployment Guide - PathVest

## ✅ Fixes Applied

### 1. Fixed Alembic Model Imports
**File**: `backend/alembic/env.py`
- Now imports all models: `User`, `Portfolio`, `Institution`, `Filing`, `Holding`
- This ensures Alembic can detect all database tables

### 2. Added `filing_date` Column
**File**: `backend/app/models/filing.py`
- Added `filing_date: Mapped[date]` column (Date type)
- This column is used throughout the codebase for queries
- Automatically populated from `filed_at` datetime field

### 3. Created Migration
**File**: `backend/alembic/versions/483ddf2ccfc5_add_filing_date_column.py`
- Adds `filing_date` column
- Populates it from existing `filed_at` data
- Creates index for query performance

---

## 🚀 Deploy to Render

### Step 1: Commit and Push Changes

```bash
cd /Users/riteshambastha/projects/pathvest

# Add all changes
git add backend/alembic/env.py
git add backend/app/models/filing.py
git add backend/alembic/versions/483ddf2ccfc5_add_filing_date_column.py

# Commit
git commit -m "Fix: Add filing_date column and update alembic imports"

# Push to trigger Render auto-deploy
git push origin main
```

### Step 2: Run Migration on Render

Once the deployment completes (check Render Dashboard):

**Option A: Via Render Shell (Recommended)**

1. Go to Render Dashboard: https://dashboard.render.com
2. Click on your `pathvest-backend` service
3. Click the **"Shell"** tab
4. Run:

```bash
cd backend
alembic upgrade head
```

**Option B: Update Start Command (Automatic)**

In Render Dashboard → `pathvest-backend` → **Settings** → **Start Command**:

Change from:
```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

To:
```bash
cd backend && alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

This runs migrations automatically on every deploy.

### Step 3: Verify Fix

Test the API endpoint that was failing:

```bash
# Get your Render backend URL
BACKEND_URL="https://pathvest-backend.onrender.com"

# Test the endpoint that was failing
curl "$BACKEND_URL/api/v1/data/date-range"

# Should return date range without errors
```

---

## 📋 What Was Fixed

### The Problem
1. **Alembic wasn't importing SEC models** → Tables not created
2. **Code uses `filing_date`** but model only had `filed_at` → SQL errors

### The Solution
1. ✅ Import all models in `alembic/env.py`
2. ✅ Add `filing_date` column to Filing model
3. ✅ Create migration to add column and populate data
4. ✅ Applied locally and tested

---

## 🔍 Verify Database Schema

After running migration on Render, verify the schema:

```bash
# In Render Shell
psql $DATABASE_URL

# Check filings table structure
\d filings

# Should see both columns:
# - filed_at (timestamp)
# - filing_date (date)

# Check data
SELECT id, filed_at, filing_date FROM filings LIMIT 5;

# Exit
\q
```

---

## 🎯 Next Steps

1. **Commit and push** the fixes
2. **Wait for Render auto-deploy** (~2-3 minutes)
3. **Run migration** via Render Shell or auto-start command
4. **Test your app** - the error should be gone!

---

## 🆘 Troubleshooting

### If migration fails on Render:

**Error: "column already exists"**
```bash
# Skip this migration (it already ran)
alembic stamp 483ddf2ccfc5
```

**Error: "relation does not exist"**
```bash
# Run all migrations from scratch
alembic upgrade head
```

**Error: "cannot import name X"**
- Check that all model files exist in `backend/app/models/`
- Verify `__init__.py` exports all models

---

## 📊 Migration Details

**Migration ID**: `483ddf2ccfc5`  
**Description**: Add filing_date column to filings table  
**Dependencies**: Requires migration `f1a2b3c4d5e6` (strategies and backtests)

**What it does**:
1. Adds `filing_date DATE` column (nullable)
2. Populates from `filed_at`: `UPDATE filings SET filing_date = DATE(filed_at)`
3. Makes column NOT NULL
4. Creates index: `ix_filings_filing_date`

---

## ✅ Success Criteria

- ✅ No import errors in alembic
- ✅ `filing_date` column exists in database
- ✅ API endpoints return data without SQL errors
- ✅ Queries using `filing_date` work correctly

---

**Status**: Ready to deploy to Render  
**Tested**: Locally ✅  
**Next**: Push to GitHub → Auto-deploy to Render → Run migration

