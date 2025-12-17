# PathVest - Quick Start with Real Data

## 🎉 You're Now Running with REAL DATA!

### ✅ What's Working

| Component | Status | Data Source |
|-----------|--------|-------------|
| **Backend API** | ✅ Running | Port 8000 |
| **Frontend UI** | ✅ Running | Port 3000 |
| **AlphaVantage** | ✅ Connected | Real market data |
| **SEC EDGAR** | ✅ Connected | Real 13F filings |
| **Mode** | 🟢 REAL DATA | Live APIs |

---

## 🚀 How to Use

### 1. Access the Application

**Frontend**: http://localhost:3000  
**Backend**: http://localhost:8000  
**API Docs**: http://localhost:8000/docs

### 2. Create a Strategy

1. Open http://localhost:3000
2. Click "Create New Strategy"
3. Go through the 8-step wizard:
   - Step 1: Strategy Setup
   - Step 2: Stock Selection
   - Step 3: Entry & Position Sizing
   - Step 4: Entry Scheduling
   - Step 5: Exit Model
   - Step 6: Risk Management
   - Step 7: Parameters
   - Step 8: **Run Backtest** ← Uses REAL DATA!

### 3. View Results

After submitting the backtest, you'll see:
- **Data Mode**: "REAL DATA (AlphaVantage + SEC EDGAR)"
- Real stock prices
- Real SEC filing references
- Authentic performance metrics

---

## 📊 Real Data Examples

### Get Real Stock Price
```bash
curl http://localhost:8000/api/v1/data/stock/AAPL
```

**Response**:
```json
{
    "symbol": "AAPL",
    "price": 274.11,
    "date": "2025-12-15",
    "volume": 49676145
}
```

### Get Historical Data
```bash
curl http://localhost:8000/api/v1/data/stock/AAPL/historical
```

**Returns**: 100 days of real OHLCV data

### Get SEC 13F Filings
```bash
curl http://localhost:8000/api/v1/data/sec/13f
```

**Returns**: Real institutional filings from Berkshire Hathaway, Tiger Global, etc.

---

## ⚠️ Important: Rate Limits

**AlphaVantage Free Tier**:
- 5 API calls per minute
- 500 API calls per day

**To avoid hitting limits**:
- Wait 15 seconds between different stock requests
- Use caching (already implemented)
- Or upgrade to premium ($50/month for unlimited)

---

## 🧪 Quick Test

Run the test script:
```bash
./test_real_data.sh
```

**Expected output**:
- ✅ Health check: REAL DATA mode
- ✅ Stock data: Real AAPL price
- ✅ SEC filings: Real 13F data
- ✅ API docs: Available

---

## 📁 Key Files

| File | Purpose |
|------|---------|
| `/backend/.env` | API keys and configuration |
| `/backend/app/services/real_data_server.py` | Real data server |
| `/frontend/.env` | Frontend API URL |
| `test_real_data.sh` | Quick verification script |
| `REAL_DATA_INTEGRATION_COMPLETE.md` | Full documentation |

---

## 🎯 What You Can Do Now

### ✅ Currently Working:
- Fetch real-time stock quotes
- Get historical OHLCV data
- Access SEC 13F filings
- Submit backtests (prototype mode)
- View results with real data attribution

### ⏸️ Pending (Optional):
- Full LEAN Engine backtesting (requires Docker)
- BigQuery data warehouse (requires GCP)
- Historical bulk data load (requires scripting)

---

## 🔧 Troubleshooting

### Backend not responding?
```bash
# Check if running
curl http://localhost:8000/health

# Restart if needed
cd /Users/riteshambastha/projects/pathvest/backend
source venv/bin/activate
python app/services/real_data_server.py
```

### Frontend not loading?
```bash
# Check if running
curl http://localhost:3000

# Restart if needed
cd /Users/riteshambastha/projects/pathvest/frontend
npm run dev
```

### Rate limit error?
Wait 1 minute and try again. AlphaVantage limits to 5 calls per minute.

---

## 📈 Next Steps

### Option 1: Continue Testing (Recommended)
✅ Current setup is perfect for:
- UI/UX validation
- API integration testing
- Stakeholder demos
- Strategy prototyping

### Option 2: Add Full Backtest Engine
Requires Docker installation:
```bash
docker-compose up
```

This enables:
- Complete LEAN Engine
- Monte Carlo simulations
- Walk-forward optimization
- Full validation framework

### Option 3: Deploy to Production
Requires GCP setup:
- Create GCP project
- Configure BigQuery
- Deploy to Cloud Run
- Setup data ingestion

---

## 💡 Pro Tips

1. **Batch Your Requests**: Fetch historical data once (100 days in 1 API call) instead of 100 individual daily calls

2. **Use Caching**: The server caches responses for 1 hour (configurable in `.env`)

3. **Monitor Usage**: Keep track of your AlphaVantage API calls to stay under 500/day

4. **Start Small**: Test with 2-3 stocks before running full portfolio backtests

5. **Check API Docs**: Visit http://localhost:8000/docs for interactive API testing

---

## 🎉 Summary

**Your PathVest system is now powered by REAL DATA!**

✅ AlphaVantage API: Connected  
✅ SEC EDGAR: Connected  
✅ Real market data: Flowing  
✅ Real 13F filings: Available  
✅ Backend: Running on port 8000  
✅ Frontend: Running on port 3000  

**You're ready to test strategies with authentic market data!** 🚀

---

**Questions?** Check `REAL_DATA_INTEGRATION_COMPLETE.md` for detailed documentation.

