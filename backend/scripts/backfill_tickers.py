#!/usr/bin/env python3
"""
Backfill Ticker Symbols for Holdings
Converts CUSIP → Ticker for all holdings in the database
"""

import asyncio
from app.services.strategy_db import SessionLocal
from app.services.cusip_mapping_service import get_cusip_mapping_service
from sqlalchemy import text
from datetime import date

async def backfill_tickers():
    """Backfill ticker symbols for all holdings"""
    
    print("\n" + "="*60)
    print("🔄 BACKFILLING TICKER SYMBOLS")
    print("="*60)
    
    db = SessionLocal()
    mapping_service = get_cusip_mapping_service()
    
    try:
        # Get all unique CUSIPs that need mapping
        result = db.execute(text("""
            SELECT DISTINCT cusip, name_of_issuer
            FROM holdings
            WHERE ticker IS NULL 
                AND cusip IS NOT NULL 
                AND cusip != ''
            LIMIT 100
        """))
        
        holdings_to_map = result.fetchall()
        total = len(holdings_to_map)
        
        print(f"\n📊 Found {total} unique CUSIPs to map (processing first 100)")
        
        if total == 0:
            print("✅ All holdings already have tickers!")
            return
        
        # Map CUSIPs to tickers
        mapped_count = 0
        failed_cusips = []
        
        for i, row in enumerate(holdings_to_map, 1):
            cusip = row.cusip
            issuer_name = row.name_of_issuer
            
            print(f"\n[{i}/{total}] Mapping {cusip} ({issuer_name})...", end=" ")
            
            try:
                ticker = await mapping_service.get_ticker_for_cusip(cusip)
                
                if ticker:
                    # Update holdings with this CUSIP
                    db.execute(text("""
                        UPDATE holdings 
                        SET ticker = :ticker
                        WHERE cusip = :cusip AND ticker IS NULL
                    """), {"ticker": ticker, "cusip": cusip})
                    
                    db.commit()
                    mapped_count += 1
                    print(f"✅ {ticker}")
                else:
                    failed_cusips.append((cusip, issuer_name))
                    print(f"❌ Not found")
                
                # Rate limiting
                await asyncio.sleep(0.2)
                
            except Exception as e:
                print(f"❌ Error: {e}")
                failed_cusips.append((cusip, issuer_name))
        
        print("\n" + "="*60)
        print(f"✅ Successfully mapped: {mapped_count}/{total}")
        print(f"❌ Failed to map: {len(failed_cusips)}")
        print("="*60)
        
        if failed_cusips:
            print("\n⚠️  CUSIPs that couldn't be mapped:")
            for cusip, name in failed_cusips[:10]:
                print(f"   - {cusip}: {name}")
            if len(failed_cusips) > 10:
                print(f"   ... and {len(failed_cusips) - 10} more")
        
        # Show final stats
        total_with_ticker = db.execute(text("""
            SELECT COUNT(DISTINCT ticker) 
            FROM holdings 
            WHERE ticker IS NOT NULL
        """)).scalar()
        
        print(f"\n📊 Total unique tickers in database: {total_with_ticker}")
        
    finally:
        db.close()

if __name__ == "__main__":
    print("\n⚠️  NOTE: This script requires OpenFIGI API key")
    print("   Set OPENFIGI_API_KEY in your environment variables")
    print("   Get a free key at: https://www.openfigi.com/api")
    
    asyncio.run(backfill_tickers())

