#!/usr/bin/env python3
"""
Fetch holdings using SEC-API.io Query API (includes holdings in response)
"""
import asyncio
import sys
import os
import logging
import httpx
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from app.db.session import AsyncSessionLocal
from app.models.holding import Holding
from app.core.config import settings
from sqlalchemy import text

logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

SEC_API_KEY = settings.SEC_API_KEY
SEC_API_BASE = "https://api.sec-api.io"

async def fetch_filing_with_holdings(accession_no: str, cik: str) -> dict:
    """Fetch filing with holdings from SEC-API.io"""
    
    # Clean accession number
    accession_clean = accession_no.replace("-", "")
    
    query = {
        "query": {
            "query_string": {
                "query": f"accessionNo:\"{accession_no}\" AND formType:\"13F-HR\""
            }
        },
        "from": "0",
        "size": "1"
    }
    
    headers = {
        "Authorization": SEC_API_KEY,
        "Content-Type": "application/json"
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            SEC_API_BASE,
            headers=headers,
            json=query,
            timeout=30.0
        )
        
        if response.status_code == 200:
            data = response.json()
            filings = data.get("filings", [])
            if filings:
                return filings[0]
        else:
            logger.warning(f"API returned {response.status_code}")
        
        return {}

async def main():
    logger.info("🚀 Fetching Holdings via SEC-API.io (Premium)")
    logger.info("=" * 70)
    logger.info(f"API Key: {SEC_API_KEY[:10]}...")
    
    async with AsyncSessionLocal() as db:
        total_holdings_fetched = 0
        total_filings_processed = 0
        filings_with_holdings = 0
        
        # Get filings without holdings (limit to recent ones first)
        result = await db.execute(text("""
            SELECT f.id, f.accession_no, f.filing_date, i.name, i.cik
            FROM filings f
            JOIN institutions i ON f.institution_id = i.id
            WHERE NOT EXISTS (SELECT 1 FROM holdings h WHERE h.filing_id = f.id)
            ORDER BY f.filing_date DESC
            LIMIT 500
        """))
        
        filings = result.fetchall()
        logger.info(f"📊 Processing {len(filings)} filings without holdings\n")
        
        for i, row in enumerate(filings):
            filing_id, accession_no, filing_date, inst_name, cik = row
            
            if i % 20 == 0:
                logger.info(f"\n📈 Progress: {i}/{len(filings)} | Holdings: {total_holdings_fetched:,} | With Data: {filings_with_holdings}")
            
            try:
                # Fetch filing with holdings from API
                filing_data = await fetch_filing_with_holdings(accession_no, cik)
                
                if filing_data:
                    holdings_list = filing_data.get("holdings", [])
                    
                    if holdings_list:
                        logger.info(f"[{i+1}] ✅ {inst_name[:25]:25} | {filing_date} | {len(holdings_list):5} holdings")
                        
                        # Save holdings to database
                        for h in holdings_list:
                            shares_data = h.get("shrsOrPrnAmt", {})
                            voting = h.get("votingAuthority", {})
                            
                            holding = Holding(
                                filing_id=filing_id,
                                name_of_issuer=h.get("nameOfIssuer", ""),
                                cusip=h.get("cusip", ""),
                                ticker=h.get("ticker", ""),
                                value=float(h.get("value", 0)),
                                shares_or_prn_amt=int(shares_data.get("sshPrnamt", 0) or 0),
                                shares_or_prn_amt_type=shares_data.get("sshPrnamtType", "SH"),
                                investment_discretion=h.get("investmentDiscretion", ""),
                                voting_authority_sole=int(voting.get("Sole", 0) or 0),
                                voting_authority_shared=int(voting.get("Shared", 0) or 0),
                                voting_authority_none=int(voting.get("None", 0) or 0),
                            )
                            db.add(holding)
                        
                        total_holdings_fetched += len(holdings_list)
                        filings_with_holdings += 1
                    else:
                        logger.info(f"[{i+1}] ⚠️  {inst_name[:25]:25} | {filing_date} | No holdings in response")
                else:
                    logger.info(f"[{i+1}] ⚠️  {inst_name[:25]:25} | {filing_date} | No data from API")
                
                total_filings_processed += 1
                
                # Commit every 20 filings
                if total_filings_processed % 20 == 0:
                    await db.commit()
                    logger.info(f"   💾 Committed batch | Total: {total_holdings_fetched:,} holdings")
                
            except Exception as e:
                logger.error(f"[{i+1}] ❌ Error for {inst_name}: {str(e)[:100]}")
                continue
            
            # Rate limit - SEC-API allows 10 req/sec on premium
            await asyncio.sleep(0.15)
        
        await db.commit()
        
        logger.info(f"\n{'='*70}")
        logger.info(f"🎉 COMPLETE!")
        logger.info(f"   Filings processed: {total_filings_processed}")
        logger.info(f"   Filings with data: {filings_with_holdings}")
        logger.info(f"   Holdings fetched:  {total_holdings_fetched:,}")

if __name__ == "__main__":
    asyncio.run(main())
