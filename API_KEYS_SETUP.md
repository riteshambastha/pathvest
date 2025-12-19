# 🔑 API Keys Setup Guide

## Overview

Pathvest LEAN integration requires API keys for fetching real market data and SEC filings. This guide will help you set them up.

---

## Required API Keys

### 1. **AlphaVantage API Key** (Market Data)
- **Purpose**: Fetch real-time and historical stock prices
- **Cost**: Free tier available (5 requests/minute, 500 requests/day)
- **Upgrade**: Premium plans for unlimited requests

#### Get Your Key:
1. Go to https://www.alphavantage.co/support/#api-key
2. Enter your email
3. Click "GET FREE API KEY"
4. Copy your API key

#### Free Tier Limits:
```
✅ 5 API calls per minute
✅ 500 API calls per day
⚠️ Sufficient for testing, may need upgrade for production
```

---

### 2. **SEC EDGAR API** (No Key Required!)
- **Purpose**: Fetch institutional 13F filings
- **Cost**: **FREE** (no API key needed)
- **Limits**: 10 requests per second
- **Documentation**: https://www.sec.gov/edgar/sec-api-documentation

#### Requirements:
```
✅ User-Agent header (already configured)
✅ Rate limiting (10 req/sec - already implemented)
✅ No registration needed
```

---

## Setup Instructions

### For Local Development:

1. **Create `.env` file** in `/backend/` directory:
```bash
cd /Users/riteshambastha/projects/pathvest/backend
touch .env
```

2. **Add API keys** to `.env`:
```bash
# Market Data API
ALPHAVANTAGE_API_KEY=your_alphavantage_key_here

# SEC EDGAR (no key needed, but set User-Agent in code)
# Already configured in sec_edgar_service.py

# Other required vars
SECRET_KEY=your-secret-key-here
DATABASE_URL=postgresql://user:pass@localhost:5432/pathvest
```

3. **Test configuration**:
```bash
python -c "from app.core.config import settings; print(f'AlphaVantage: {settings.ALPHAVANTAGE_API_KEY[:10]}...')"
```

---

### For Render Deployment:

1. **Go to Render Dashboard**:
   - Navigate to your backend service
   - Click "Environment" tab

2. **Add Environment Variables**:
```
ALPHAVANTAGE_API_KEY = your_alphavantage_key_here
```

3. **Save and Redeploy**:
   - Render will automatically redeploy with new variables
   - Check logs for confirmation

---

## Verification

### Test AlphaVantage Connection:
```python
from app.services.alphavantage_service import AlphaVantageService
import asyncio

async def test():
    service = AlphaVantageService()
    data = await service.get_daily_ohlcv("AAPL", "2024-01-01", "2024-01-31")
    print(f"✅ Fetched {len(data)} days of AAPL data")

asyncio.run(test())
```

### Test SEC EDGAR Connection:
```python
from app.services.sec_edgar_service import SECEdgarService

service = SECEdgarService()
institutions = service.search_institutions(min_aum=1e9)
print(f"✅ Found {len(institutions)} institutions")
```

---

## Current Implementation

### What Works WITHOUT API Keys:
- ✅ SEC EDGAR (free access, no key needed)
- ✅ Simulated data tracking
- ✅ All UI/UX features

### What Requires AlphaVantage Key:
- 📊 Real historical stock prices
- 📊 Intraday price data
- 📊 Technical indicators (SMA, RSI, etc.)

### Fallback Behavior:
If AlphaVantage key is missing:
- ⚠️ System will use simulated price data
- ⚠️ Backtests will still run
- ⚠️ Results will be marked as "simulated"

---

## Cost Estimation

### Free Tier (AlphaVantage):
```
Strategy with:
- 3 institutions
- 4 quarters lookback
- 8 stocks analyzed
- 250 trading days

Estimated API calls per backtest:
= 8 stocks × 250 days / 5 (batch requests)
= ~400 API calls

Free tier limit: 500/day
✅ Can run 1-2 backtests per day
```

### Premium Tier ($50/month):
```
✅ Unlimited API calls
✅ No rate limits
✅ Intraday data
✅ Real-time quotes
```

---

## Security Best Practices

### ✅ DO:
- Store keys in environment variables
- Use `.env` file for local development
- Add `.env` to `.gitignore`
- Use Render environment variables for production
- Rotate keys periodically

### ❌ DON'T:
- Commit API keys to GitHub
- Share keys in public channels
- Hardcode keys in source code
- Use production keys in development

---

## Troubleshooting

### Error: "AlphaVantage API limit reached"
```
Solution: Wait until daily limit resets (midnight UTC)
Alternative: Upgrade to premium tier
```

### Error: "Invalid API key"
```
Check:
1. Key is correctly copied (no extra spaces)
2. Environment variable is set correctly
3. Application has been restarted after adding key
```

### Error: "SEC rate limit exceeded"
```
This is rare (10 req/sec is high)
Built-in rate limiting should prevent this
Check for infinite loops in code
```

---

## Next Steps

1. ✅ Get AlphaVantage API key (5 minutes)
2. ✅ Add to `.env` file locally
3. ✅ Add to Render environment variables
4. ✅ Test with a backtest
5. ✅ Monitor API usage in logs

---

## Support

- **AlphaVantage Support**: https://www.alphavantage.co/support/
- **SEC EDGAR Docs**: https://www.sec.gov/edgar/sec-api-documentation
- **Render Environment Vars**: https://render.com/docs/environment-variables

---

*Last Updated: December 19, 2025*

