import asyncio
import sys
import os
import logging
from datetime import datetime, timedelta

# Add parent directory to path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import AsyncSessionLocal
from app.services.sec_service import SECService
from app.models.institution import Institution
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Additional popular funds to track
ADDITIONAL_FUNDS = [
    {"name": "BlackRock", "cik": "0001364742"},
    {"name": "Vanguard Group", "cik": "0000102909"},
    {"name": "State Street Corp", "cik": "0000093751"},
    {"name": "Geode Capital Management", "cik": "0001261654"},
    {"name": "Fidelity (FMR LLC)", "cik": "0000315066"},
    {"name": "JPMorgan Chase", "cik": "0000019617"},
    {"name": "Morgan Stanley", "cik": "0000895421"},
    {"name": "Goldman Sachs", "cik": "0000886982"},
    {"name": "Bill & Melinda Gates Foundation", "cik": "0001166559"},
    {"name": "TCI Fund Management", "cik": "0001646331"}
]

async def fetch_data():
    logger.info("🚀 Starting SEC Data Fetcher...")
    
    async with AsyncSessionLocal() as db:
        # Combine default popular institutions with additional ones
        all_institutions = SECService.POPULAR_INSTITUTIONS + ADDITIONAL_FUNDS
        
        # Unique by CIK
        unique_institutions = {inst['cik']: inst for inst in all_institutions}.values()
        
        logger.info(f"📋 Target Institutions: {len(unique_institutions)}")
        
        for i, inst_data in enumerate(unique_institutions):
            cik = inst_data['cik']
            name = inst_data['name']
            
            logger.info(f"\n🔄 [{i+1}/{len(unique_institutions)}] Processing {name} (CIK: {cik})...")
            
            try:
                # 1. Fetch Filings (Metadata)
                # Fetch last 3 years of data
                from_date = "2021-01-01"
                to_date = datetime.now().strftime("%Y-%m-%d")
                
                logger.info(f"   📅 Fetching filings from {from_date} to {to_date}...")
                
                filings = await SECService.fetch_and_cache_filings(
                    db=db,
                    cik=cik,
                    form_type="13F-HR",
                    from_date=from_date,
                    to_date=to_date,
                    size=20, # Fetch up to 20 filings (5 years quarterly)
                    force_refresh=True
                )
                
                logger.info(f"   ✅ Found {len(filings)} filings")
                
                # 2. Fetch Holdings (Detailed Data)
                for j, filing in enumerate(filings):
                    logger.info(f"      📄 [{j+1}/{len(filings)}] Processing filing {filing.accession_no} ({filing.period_of_report})")
                    
                    try:
                        holdings = await SECService.fetch_and_cache_holdings(db, filing)
                        logger.info(f"         ✅ Holdings: {len(holdings)}")
                    except Exception as e:
                        logger.error(f"         ❌ Failed to fetch holdings: {e}")
                        
            except Exception as e:
                logger.error(f"❌ Error processing {name}: {e}")
                
        logger.info("\n✨ Data fetch complete!")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    asyncio.run(fetch_data())

