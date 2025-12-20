# 🎯 PathVest Frontend Strategy Creation Testing Guide

## ✅ System Status: READY FOR TESTING

**Backend API**: `http://localhost:8000` ✅ RUNNING
**Frontend App**: `http://localhost:3001` ✅ RUNNING
**Database**: PostgreSQL ✅ CONNECTED
**API Keys**: ✅ CONFIGURED (Mock Data Mode)

---

## 📋 8-Step Strategy Creation Test Plan

### **Prerequisites**
1. Open browser to `http://localhost:3001`
2. Backend server running on port 8000
3. Database populated with SEC data

### **Step 1: Setup** 🏗️
**Location**: `/strategy/new` or Dashboard → "New Strategy"

**Test Actions**:
- [ ] Click "New Strategy" button
- [ ] Enter strategy name: "Test Institutional Strategy"
- [ ] Select backtest period: 2020-01-01 to 2024-12-31
- [ ] Choose backtest engine: "Custom" (recommended for testing)
- [ ] Set initial capital: $100,000
- [ ] Click "Next" to proceed

**Expected Results**:
- [ ] Form validates input fields
- [ ] Navigation to Step 2 works
- [ ] Strategy configuration saved temporarily

### **Step 2: Stock Selection** 📊

**Test Actions**:
- [ ] Select institutions to follow:
  - [ ] Berkshire Hathaway (0001067983)
  - [ ] Renaissance Technologies (0001037389)
  - [ ] Citadel Advisors (0001423053)
- [ ] Choose signals:
  - [ ] ✅ Doubling Down
  - [ ] ✅ Insider Buying
  - [ ] ✅ Institutional Herding
- [ ] Apply universe filters:
  - [ ] Market Cap: > $3B
  - [ ] Index Membership: S&P 1500

**Expected Results**:
- [ ] Institutions load from API
- [ ] Signals can be toggled
- [ ] Filters apply correctly
- [ ] Universe preview shows selected stocks

### **Step 3: Position Sizing** ⚖️

**Test Actions**:
- [ ] Choose sizing method: "Fixed Size (5%)"
- [ ] Set max positions: 20
- [ ] Configure risk constraints:
  - [ ] Min position: 3%
  - [ ] Max position: 7%
- [ ] Enable conviction ranking

**Expected Results**:
- [ ] Position sizing calculator works
- [ ] Risk constraints validate
- [ ] Preview shows sample allocations

### **Step 4: Entry Timing** ⏰

**Test Actions**:
- [ ] Set entry timing: "End of Quarter"
- [ ] Configure signal confirmation:
  - [ ] Price breakout: 10-day high
  - [ ] Trend filter: 50-day SMA
  - [ ] Momentum: RSI > 45

**Expected Results**:
- [ ] Timing options work
- [ ] Technical indicators configure
- [ ] Signal strength scoring displays

### **Step 5-7: Exit Rules** 🚪

**Test Actions**:
- [ ] Enable exit modules:
  - [ ] ✅ Trailing Stop (15%)
  - [ ] ✅ Thesis Drift (4 quarters)
  - [ ] ✅ Insider Reversal
- [ ] Configure stop levels
- [ ] Set take-profit levels

**Expected Results**:
- [ ] Exit modules toggle correctly
- [ ] Parameters save
- [ ] Risk management rules apply

### **Step 8: Review & Run** ✅

**Test Actions**:
- [ ] Review all configuration
- [ ] Click "Run Backtest"
- [ ] Monitor progress in real-time
- [ ] View preliminary results

**Expected Results**:
- [ ] Configuration summary accurate
- [ ] Backtest initiates
- [ ] Progress bar updates
- [ ] Results page loads

---

## 🔍 API Integration Tests

### **Test Backend Connectivity**
```bash
# Health check
curl http://localhost:8000/api/v1/health

# Get institutions
curl "http://localhost:8000/api/v1/sec/institutions?limit=5"

# Test backtest endpoints
curl http://localhost:8000/api/v1/backtest/
```

### **Test Frontend-Backend Communication**
- [ ] Institution dropdown loads data
- [ ] Strategy validation works
- [ ] Backtest submission succeeds
- [ ] Results retrieval works

---

## 🚨 Common Issues & Solutions

### **Issue: Backend Connection Failed**
**Symptoms**: Frontend shows "API Error" or blank dropdowns
**Solution**:
1. Check backend server: `curl http://localhost:8000/api/v1/health`
2. Verify CORS settings in backend
3. Check frontend .env file: `VITE_API_BASE_URL=http://localhost:8000/api/v1`

### **Issue: Strategy Creation Fails**
**Symptoms**: Form validation errors or submission fails
**Solution**:
1. Check required fields are filled
2. Verify date formats
3. Check network tab for API errors
4. Ensure backend database is populated

### **Issue: Backtest Doesn't Start**
**Symptoms**: Progress bar stuck at 0%
**Solution**:
1. Check backtest engine selection
2. Verify LEAN/Custom engine availability
3. Check backend logs for errors
4. Ensure sufficient API calls remaining

---

## 📊 Expected Test Results

### **Performance Benchmarks**
- **Strategy Creation**: < 2 minutes
- **Backtest Execution**: 2-3 minutes (Custom), 5-10 minutes (LEAN)
- **Results Loading**: < 30 seconds
- **Chart Rendering**: < 10 seconds

### **Data Validation**
- [ ] 15+ popular institutions available
- [ ] Stock universe > 500 companies
- [ ] Historical data from 2019+
- [ ] Real-time API connectivity

### **UI/UX Validation**
- [ ] Responsive design works on desktop
- [ ] Help panels provide guidance
- [ ] Progress indicators update correctly
- [ ] Error messages are clear

---

## 🎯 Success Criteria

**✅ MINIMUM VIABLE TEST**: Complete steps 1-3 and run basic backtest
**✅ FULL SUCCESS**: Complete all 8 steps with working backtest results
**✅ PERFECT SCORE**: All features work, results are accurate, UI is polished

---

## 📞 Support & Debugging

**Logs to Check**:
- Backend: Terminal running uvicorn
- Frontend: Browser DevTools Console
- Database: PostgreSQL logs
- API: Browser Network tab

**Key Files**:
- `frontend/.env` - API configuration
- `backend/.env` - Database and API keys
- `backend/app/main.py` - Server setup
- `frontend/src/services/api.ts` - Frontend API client

---

**🚀 Ready to Test! Open `http://localhost:3001` and begin strategy creation.**
