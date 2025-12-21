# 🚀 Deployment Checklist: Staging → Main

**Created:** December 21, 2025  
**Commits to Deploy:** 10 commits from staging branch

---

## ⚠️ Pre-Deployment Risks & Mitigations

### 1. API Keys (CRITICAL)

| Variable | Current (Local) | Action Required |
|----------|----------------|-----------------|
| `ALPHAVANTAGE_API_KEY` | `L3UFYZPJ5YTC2ETK` (Premium) | ✅ Update on Render |
| `SEC_API_KEY` | `47d09b04...` (Premium) | ✅ Update on Render |

**Risk:** If old API keys are used, backtest will fail to fetch data.

**Action:**
```bash
# On Render Dashboard → Environment Variables:
ALPHAVANTAGE_API_KEY=L3UFYZPJ5YTC2ETK
SEC_API_KEY=47d09b04f375b7573f5d34ee02326a9e9e5a3bd984d53f8eba4dcc90d3a5e266
```

---

### 2. Database (MEDIUM RISK)

**Status:** ✅ Already synced!
- Render PostgreSQL has 741 filings, 2.5M holdings
- Schema is identical between local and production

**No migration needed** - all tables already exist.

---

### 3. CORS Origins (LOW RISK)

Current production CORS should include your Vercel domain:
```
BACKEND_CORS_ORIGINS=["https://your-app.vercel.app","https://pathvest.vercel.app"]
```

---

### 4. Frontend Environment (CRITICAL)

Vercel needs these environment variables:
```
VITE_API_BASE_URL=https://your-render-backend.onrender.com
VITE_ENVIRONMENT=production
VITE_DEBUG=false
```

**Risk:** Wrong API URL will break all functionality.

---

### 5. New Dependencies (NONE)

✅ No new npm or pip packages were added.

---

## 📋 Step-by-Step Deployment

### Phase 1: Backend (Render)

1. **Update Environment Variables on Render:**
   ```
   ALPHAVANTAGE_API_KEY=L3UFYZPJ5YTC2ETK
   SEC_API_KEY=47d09b04f375b7573f5d34ee02326a9e9e5a3bd984d53f8eba4dcc90d3a5e266
   ENABLE_MOCK_DATA=false
   ```

2. **Verify Current Production Works:**
   ```bash
   curl https://your-render-backend.onrender.com/api/v1/health
   ```

3. **Merge staging to main:**
   ```bash
   git checkout main
   git merge staging
   git push origin main
   ```

4. **Wait for Render auto-deploy** (usually 2-5 minutes)

5. **Verify Backend Health:**
   ```bash
   curl https://your-render-backend.onrender.com/api/v1/health
   ```

### Phase 2: Frontend (Vercel)

1. **Verify Vercel Environment Variables:**
   - `VITE_API_BASE_URL` points to correct backend

2. **Vercel auto-deploys on main push** (no action needed)

3. **Verify Frontend:**
   - Open your Vercel URL
   - Navigate to Step 2 → Check institutions list (should be deduplicated)
   - Navigate to Step 8 → Run a backtest

---

## 🔄 Rollback Plan

If something breaks:

### Quick Rollback:
```bash
git checkout main
git revert HEAD --no-edit
git push origin main
```

### Full Rollback to Previous State:
```bash
# Find the last working commit
git log --oneline main | head -10

# Reset to that commit
git checkout main
git reset --hard <commit-hash>
git push origin main --force
```

---

## ✅ Post-Deployment Verification

### 1. Backend Health Check
```bash
curl https://your-backend.onrender.com/api/v1/health
# Expected: {"status":"healthy","message":"API is running"}
```

### 2. Database Connection
```bash
curl https://your-backend.onrender.com/api/v1/sec/institutions
# Expected: List of ~20 institutions
```

### 3. Frontend Tests
- [ ] Step 1: Date picker works
- [ ] Step 2: Institutions load (no duplicates)
- [ ] Step 8: "Run Backtest" submits successfully
- [ ] Success modal: "View Live Results" navigates correctly
- [ ] Results page: Overview tab shows new corporate design

### 4. Full Backtest Test
- Run a 1-year backtest with Berkshire Hathaway
- Verify real data is fetched (not mock)
- Verify trades are displayed

---

## 📊 Changes Summary

| Category | Files Changed | Risk |
|----------|--------------|------|
| Backend Logic | 15 | Medium |
| Frontend UI | 12 | Low |
| API Endpoints | 0 | None |
| Database Schema | 0 | None |
| Dependencies | 0 | None |
| Documentation | 5 | None |

**Total:** 55 files changed, 7,399 insertions, 1,671 deletions

---

## 🎯 Key Features Being Deployed

1. **Exit Signals** (Stop-loss, Take-profit, Trailing stop)
2. **Rebalancing Rules** (Weekly, Monthly, Quarterly, Threshold)
3. **T+1 Execution Timing**
4. **Technical Confirmation Filters**
5. **Advanced Visualizations** (Monte Carlo, Heatmap, Walk-Forward, Stress Test)
6. **Corporate Overview Tab UI**
7. **200+ CUSIP Mappings**
8. **SEC Data from 2015-2025**
9. **Duplicate Institution Fix**
10. **Navigation Fix in Step 8**

