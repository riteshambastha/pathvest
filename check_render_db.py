#!/usr/bin/env python3
"""
Check Render Database Status
Run this in Render shell to verify SEC data is seeded
"""

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
        print("="*60)
    else:
        print("⚠️  DATABASE IS EMPTY - Need to seed data!")
        print("="*60)
        print("\n💡 To seed data, run:")
        print("   python3 scripts/seed_sec_data.py")
        
except Exception as e:
    print(f"\n❌ Error: {e}")
finally:
    db.close()

