#!/usr/bin/env python3
"""
Quick Ticker Backfill - Use Name Matching
Converts issuer names to tickers for common/obvious companies
"""

from app.services.strategy_db import SessionLocal
from sqlalchemy import text

# Simple name → ticker mapping for common companies
COMMON_MAPPINGS = {
    "APPLE INC": "AAPL",
    "MICROSOFT CORP": "MSFT",
    "AMAZON COM INC": "AMZN",
    "ALPHABET INC": "GOOGL",
    "TESLA INC": "TSLA",
    "NVIDIA CORP": "NVDA",
    "META PLATFORMS INC": "META",
    "BERKSHIRE HATHAWAY": "BRK.B",
    "JPMORGAN CHASE": "JPM",
    "JOHNSON & JOHNSON": "JNJ",
    "VISA INC": "V",
    "WALMART INC": "WMT",
    "EXXON MOBIL CORP": "XOM",
    "PROCTER & GAMBLE": "PG",
    "MASTERCARD INC": "MA",
    "UNITEDHEALTH GROUP": "UNH",
    "HOME DEPOT INC": "HD",
    "CHEVRON CORP": "CVX",
    "ABBVIE INC": "ABBV",
    "COCA-COLA CO": "KO",
    "MERCK & CO": "MRK",
    "PEPSICO INC": "PEP",
    "COSTCO WHOLESALE": "COST",
    "ADOBE INC": "ADBE",
    "CISCO SYSTEMS": "CSCO",
    "THERMO FISHER": "TMO",
    "INTEL CORP": "INTC",
    "ACCENTURE PLC": "ACN",
    "NETFLIX INC": "NFLX",
    "WALT DISNEY CO": "DIS",
    "SALESFORCE INC": "CRM",
    "BOEING CO": "BA",
    "GENERAL ELECTRIC": "GE",
    "MCDONALD'S CORP": "MCD",
    "BANK OF AMERICA": "BAC",
    "PFIZER INC": "PFE",
    "ORACLE CORP": "ORCL",
    "AMD": "AMD",
    "QUALCOMM INC": "QCOM",
    "AMGEN INC": "AMGN",
    "BROADCOM INC": "AVGO",
    "TEXAS INSTRUMENTS": "TXN",
    "STARBUCKS CORP": "SBUX",
    "LILLY ELI & CO": "LLY",
    "BRISTOL MYERS SQUIBB": "BMY",
    "T-MOBILE US INC": "TMUS",
}

def backfill_common_tickers():
    """Backfill tickers using name matching"""
    
    print("\n" + "="*60)
    print("🔄 QUICK TICKER BACKFILL (Name Matching)")
    print("="*60)
    
    db = SessionLocal()
    
    try:
        total_mapped = 0
        
        for company_name, ticker in COMMON_MAPPINGS.items():
            # Find holdings with similar names
            result = db.execute(text("""
                UPDATE holdings
                SET ticker = :ticker
                WHERE ticker IS NULL 
                    AND UPPER(name_of_issuer) LIKE :pattern
            """), {
                "ticker": ticker,
                "pattern": f"%{company_name}%"
            })
            
            if result.rowcount > 0:
                print(f"✅ {company_name} → {ticker}: {result.rowcount} holdings")
                total_mapped += result.rowcount
        
        db.commit()
        
        print("\n" + "="*60)
        print(f"✅ Mapped {total_mapped} holdings")
        print("="*60)
        
        # Show stats
        total_with_ticker = db.execute(text("""
            SELECT COUNT(DISTINCT ticker) 
            FROM holdings 
            WHERE ticker IS NOT NULL
        """)).scalar()
        
        total_holdings = db.execute(text("SELECT COUNT(*) FROM holdings")).scalar()
        holdings_with_ticker = db.execute(text("""
            SELECT COUNT(*) FROM holdings WHERE ticker IS NOT NULL
        """)).scalar()
        
        print(f"\n📊 Stats:")
        print(f"   Total holdings: {total_holdings}")
        print(f"   Holdings with ticker: {holdings_with_ticker}")
        print(f"   Unique tickers: {total_with_ticker}")
        print(f"   Coverage: {holdings_with_ticker/total_holdings*100:.1f}%")
        
    finally:
        db.close()

if __name__ == "__main__":
    backfill_common_tickers()

