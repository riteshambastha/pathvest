# 🔍 How to Check Render Database for SEC Data

## Method 1: Via Render Dashboard (Easiest)

### Step 1: Access Render Shell
1. Go to https://dashboard.render.com/
2. Click on your **pathvest-backend** service
3. Click the **"Shell"** tab at the top (next to "Logs", "Events", etc.)
4. Wait for shell to connect (shows `root@srv-xxxxx:/app#`)

### Step 2: Run Database Check

Copy and paste this command into the Render shell:

```bash
python3 << 'EOF'
from app.services.strategy_db import SessionLocal
from sqlalchemy import text

db = SessionLocal()

print("\n" + "="*60)
print("📊 RENDER DATABASE STATUS CHECK")
print("="*60)

try:
    # Check institutions
    institutions = db.execute(text("SELECT COUNT(*) FROM sec_institutions")).scalar()
    print(f"\n✅ SEC Institutions: {institutions}")
    
    if institutions > 0:
        popular = db.execute(text("SELECT COUNT(*) FROM institutions WHERE is_popular = TRUE")).scalar()
        print(f"   └─ Popular institutions: {popular}")
    
    # Check filings
    filings = db.execute(text("SELECT COUNT(*) FROM sec_filings_13f")).scalar()
    print(f"\n✅ SEC Filings (13F): {filings}")
    
    if filings > 0:
        latest = db.execute(text("SELECT MAX(filing_date) FROM sec_filings_13f")).scalar()
        oldest = db.execute(text("SELECT MIN(filing_date) FROM sec_filings_13f")).scalar()
        print(f"   └─ Date range: {oldest} to {latest}")
    
    # Check holdings
    holdings = db.execute(text("SELECT COUNT(*) FROM sec_holdings_13f")).scalar()
    print(f"\n✅ SEC Holdings (13F): {holdings}")
    
    if holdings > 0:
        unique_stocks = db.execute(text("SELECT COUNT(DISTINCT ticker) FROM sec_holdings_13f WHERE ticker IS NOT NULL")).scalar()
        print(f"   └─ Unique stocks: {unique_stocks}")
    
    # Overall status
    print("\n" + "="*60)
    if holdings > 0 and filings > 0 and institutions > 0:
        print("✅ DATABASE IS SEEDED - Ready for backtesting!")
    else:
        print("⚠️  DATABASE IS EMPTY - Need to seed data!")
        print("\n💡 To seed data:")
        print("   1. Check if scripts/seed_sec_data.py exists")
        print("   2. Or import data from BigQuery")
    print("="*60)
        
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    db.close()
EOF
```

### Step 3: Interpret Results

#### ✅ Good Output (Database is seeded):
```
============================================================
📊 RENDER DATABASE STATUS CHECK
============================================================

✅ SEC Institutions: 10
   └─ Popular institutions: 10

✅ SEC Filings (13F): 247
   └─ Date range: 2021-09-02 to 2025-11-13

✅ SEC Holdings (13F): 5834
   └─ Unique stocks: 352

============================================================
✅ DATABASE IS SEEDED - Ready for backtesting!
============================================================
```

#### ⚠️ Bad Output (Database is empty):
```
============================================================
📊 RENDER DATABASE STATUS CHECK
============================================================

✅ SEC Institutions: 0

✅ SEC Filings (13F): 0

✅ SEC Holdings (13F): 0

============================================================
⚠️  DATABASE IS EMPTY - Need to seed data!
============================================================
```

---

## Method 2: Via API (Quick Check)

You can also check from your terminal without SSH:

```bash
# Check if institutions exist
curl https://pathvest-backend.onrender.com/api/v1/sec/institutions | python3 -c "import sys, json; data=json.load(sys.stdin); print(f'Found {len(data)} institutions')"

# Get date range
curl https://pathvest-backend.onrender.com/api/v1/data/date-range
```

Expected output:
```
Found 10 institutions
{"min_date":"2021-09-02","max_date":"2025-11-13"}
```

---

## Method 3: Create Test Backtest

The fastest way to verify data:

1. Go to https://pathvest.vercel.app/builder
2. Select 2-3 institutions in Step 2
3. Complete all steps and run backtest
4. Check results page:
   - If **0 API calls, 0 SEC filings** → Database is empty
   - If **20+ API calls, 40+ SEC filings** → Database has data!

---

## 🔧 If Database is Empty - How to Seed

### Option A: Check for Seeding Script

In Render shell:
```bash
ls -la scripts/
# Look for: seed_sec_data.py or similar
```

If it exists:
```bash
python3 scripts/seed_sec_data.py
```

### Option B: Import from BigQuery (if configured)

Check if BigQuery is configured:
```bash
python3 -c "from app.core.config import settings; print(f'BigQuery: {settings.USE_BIGQUERY}')"
```

If `True`, the backend should auto-fetch from BigQuery when needed.

### Option C: Manual Data Entry (Quick Test)

For testing, you can manually insert a few records:

```bash
python3 << 'EOF'
from app.services.strategy_db import SessionLocal
from sqlalchemy import text

db = SessionLocal()

try:
    # Insert Berkshire Hathaway as test
    db.execute(text("""
        INSERT INTO sec_institutions (cik, name) 
        VALUES ('0001067983', 'Berkshire Hathaway Inc')
        ON CONFLICT (cik) DO NOTHING
    """))
    
    db.execute(text("""
        INSERT INTO institutions (cik, name, is_popular, aum) 
        VALUES ('0001067983', 'Berkshire Hathaway', true, 350000000000)
        ON CONFLICT (cik) DO NOTHING
    """))
    
    db.commit()
    print("✅ Test institution added!")
except Exception as e:
    db.rollback()
    print(f"❌ Error: {e}")
finally:
    db.close()
EOF
```

---

## 📝 Summary

**Easiest way**: Render Dashboard → Shell tab → Paste the Python check script

**Result tells you**:
- ✅ Database is ready → You're good to go!
- ⚠️ Database is empty → Need to seed data first

Let me know what the output shows! 🚀

