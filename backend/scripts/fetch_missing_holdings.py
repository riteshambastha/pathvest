#!/usr/bin/env python3
"""
Fetch missing holdings for institutions that have filings but no holdings data.
"""
import asyncio
import sys
import os
import logging
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from app.db.session import AsyncSessionLocal
from app.services.sec_service import SECService
from app.models.filing import Filing
from sqlalchemy import text, select
from sqlalchemy.orm import selectinload

logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

async def fetch_holdings_for_missing():
    logger.info("🚀 Starting Holdings Fetch for Institutions with Missing Data")
    logger.info("=" * 70)
    
    async with AsyncSessionLocal() as db:
        total_holdings_fetched = 0
        total_filings_processed = 0
        
        # Get all filings that have NO holdings
        result = await db.execute(text("""
            SELECT f.id, f.accession_no, f.filing_date, i.name, i.cik
            FROM filings f
            JOIN institutions i ON f.institution_id = i.id
            WHERE NOT EXISTS (SELECT 1 FROM holdings h WHERE h.filing_id = f.id)
            ORDER BY i.name, f.filing_date DESC
        """))
        
        filings_to_fetch = result.fetchall()
        logger.info(f"📊 Found {len(filings_to_fetch)} filings needing holdings")
        
        current_institution = None
        institution_count = 0
        
        for i, row in enumerate(filings_to_fetch):
            filing_id, accession_no, filing_date, inst_name, cik = row
            
            # Log institution change
            if inst_name != current_institution:
                if current_institution:
                    logger.info(f"   ✅ Completed {current_institution}: {institution_count} filings")
                current_institution = inst_name
                institution_count = 0
                logger.info(f"\n{'='*60}")
                logger.info(f"📊 Processing: {inst_name} (CIK: {cik})")
            
            institution_count += 1
            
            try:
                # Get the filing ORM object properly
                stmt = select(Filing).where(Filing.id == filing_id)
                result = await db.execute(stmt)
                filing = result.scalar_one_or_none()
                
                if not filing:
                    logger.warning(f"   ⚠️ Filing {filing_id} not found in ORM")
                    continue
                
                logger.info(f"   [{institution_count}] Fetching: {accession_no} ({filing_date})")
                
                # Fetch holdings using SEC service
                holdings = await SECService.fetch_and_cache_holdings(db, filing)
                
                if holdings:
                    total_holdings_fetched += len(holdings)
                    logger.info(f"       ✅ Got {len(holdings)} holdings")
                else:
                    logger.info(f"       ⚠️ No holdings found")
                
                total_filings_processed += 1
                
                # Commit every 5 filings
                if total_filings_processed % 5 == 0:
                    await db.commit()
                    logger.info(f"   💾 Committed batch (total: {total_holdings_fetched:,} holdings from {total_filings_processed} filings)")
                
            except Exception as e:
                logger.error(f"       ❌ Error: {str(e)[:150]}")
                import traceback
                traceback.print_exc()
                continue
            
            # Small delay for rate limiting
            await asyncio.sleep(0.2)
        
        # Final commit
        await db.commit()
        
        logger.info(f"\n{'='*70}")
        logger.info(f"🎉 COMPLETE!")
        logger.info(f"   Filings processed: {total_filings_processed}")
        logger.info(f"   Holdings fetched: {total_holdings_fetched:,}")

if __name__ == "__main__":
    asyncio.run(fetch_holdings_for_missing())
