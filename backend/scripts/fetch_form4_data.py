"""
Form 4 (Insider Trading) Data Fetcher
Per SRS FR-3.1.A.2 and FR-3.1.C.11.2 (Insider Reversal Exit)

Fetches insider transaction data from SEC EDGAR and SEC-API.io
"""

import asyncio
import sys
import os
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import httpx

# Add parent directory to path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# SEC-API.io configuration
SEC_API_KEY = os.getenv("SEC_API_KEY")
SEC_API_BASE = "https://api.sec-api.io"

# Popular stocks to track insider activity for
POPULAR_STOCKS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK.B",
    "JPM", "JNJ", "V", "PG", "UNH", "HD", "MA", "DIS", "PYPL", "NFLX",
    "ADBE", "CRM", "INTC", "VZ", "T", "KO", "PEP", "MRK", "ABT", "TMO",
    "COST", "NKE", "LLY", "ORCL", "ACN", "TXN", "QCOM", "AMD", "AVGO",
    "IBM", "HON", "GE", "BA", "CAT", "MMM", "GS", "MS", "BLK", "C"
]


async def fetch_form4_from_sec_api(
    ticker: str,
    from_date: str,
    to_date: str,
    size: int = 50
) -> List[Dict]:
    """
    Fetch Form 4 filings from SEC-API.io
    
    Args:
        ticker: Stock ticker symbol
        from_date: Start date (YYYY-MM-DD)
        to_date: End date (YYYY-MM-DD)
        size: Number of filings to fetch
    
    Returns:
        List of Form 4 filing data
    """
    if not SEC_API_KEY:
        logger.warning("SEC_API_KEY not set, skipping API call")
        return []
    
    query = {
        "query": {
            "query_string": {
                "query": f'formType:"4" AND ticker:"{ticker}"'
            }
        },
        "from": "0",
        "size": str(size),
        "sort": [{"filedAt": {"order": "desc"}}]
    }
    
    headers = {
        "Authorization": SEC_API_KEY,
        "Content-Type": "application/json"
    }
    
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{SEC_API_BASE}",
                json=query,
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("filings", [])
            else:
                logger.error(f"SEC-API error for {ticker}: {response.status_code}")
                return []
                
    except Exception as e:
        logger.error(f"Error fetching Form 4 for {ticker}: {e}")
        return []


async def parse_form4_filing(filing: Dict) -> List[Dict]:
    """
    Parse a Form 4 filing into transaction records
    
    Args:
        filing: Raw filing data from SEC-API
    
    Returns:
        List of parsed transaction records
    """
    transactions = []
    
    # Extract basic info
    ticker = filing.get("ticker", "")
    filing_date = filing.get("filedAt", "")[:10]  # YYYY-MM-DD
    company = filing.get("companyName", "")
    cik = filing.get("cik", "")
    
    # Parse the Form 4 specific data
    form4_data = filing.get("form4", {})
    
    # Get reporter (insider) info
    reporting_owner = form4_data.get("reportingOwner", {})
    insider_name = reporting_owner.get("name", "Unknown")
    
    # Relationship
    relationship = reporting_owner.get("relationship", {})
    is_director = relationship.get("isDirector", False)
    is_officer = relationship.get("isOfficer", False)
    is_ten_percent_owner = relationship.get("isTenPercentOwner", False)
    officer_title = relationship.get("officerTitle", "")
    
    # Transactions (non-derivative)
    non_derivative_txns = form4_data.get("nonDerivativeTransaction", [])
    if not isinstance(non_derivative_txns, list):
        non_derivative_txns = [non_derivative_txns] if non_derivative_txns else []
    
    for txn in non_derivative_txns:
        try:
            # Transaction details
            txn_date = txn.get("transactionDate", {}).get("value", filing_date)
            txn_code = txn.get("transactionCoding", {}).get("transactionCode", "")
            
            # Shares and price
            amounts = txn.get("transactionAmounts", {})
            shares = float(amounts.get("transactionShares", {}).get("value", 0) or 0)
            price = float(amounts.get("transactionPricePerShare", {}).get("value", 0) or 0)
            
            # Acquired or disposed
            acquired_disposed = amounts.get("transactionAcquiredDisposedCode", {}).get("value", "")
            
            # Calculate transaction value
            txn_value = shares * price if price > 0 else 0
            
            # Determine if buy or sell
            if txn_code in ["P", "A", "M", "G", "I"]:  # Purchase codes
                txn_type = "BUY"
            elif txn_code in ["S", "D", "F"]:  # Sale codes
                txn_type = "SELL"
            else:
                txn_type = "OTHER"
            
            # Post-transaction shares
            post_txn = txn.get("postTransactionAmounts", {})
            shares_after = float(post_txn.get("sharesOwnedFollowingTransaction", {}).get("value", 0) or 0)
            
            transactions.append({
                "ticker": ticker,
                "company_name": company,
                "cik": cik,
                "filing_date": filing_date,
                "transaction_date": txn_date,
                "insider_name": insider_name,
                "title": officer_title,
                "is_director": is_director,
                "is_officer": is_officer,
                "is_ten_percent_owner": is_ten_percent_owner,
                "transaction_code": txn_code,
                "transaction_type": txn_type,
                "shares": shares,
                "price": price,
                "transaction_value": txn_value,
                "shares_after": shares_after,
                "is_10b51_plan": form4_data.get("is10b51Plan", False)
            })
            
        except Exception as e:
            logger.warning(f"Error parsing transaction: {e}")
            continue
    
    return transactions


async def save_transactions_to_db(transactions: List[Dict]):
    """
    Save insider transactions to PostgreSQL database
    """
    from app.db.session import AsyncSessionLocal
    from sqlalchemy import text
    
    if not transactions:
        return 0
    
    saved_count = 0
    
    async with AsyncSessionLocal() as db:
        for txn in transactions:
            try:
                # Check if transaction already exists
                check_query = text("""
                    SELECT id FROM insider_transactions 
                    WHERE ticker = :ticker 
                    AND transaction_date = :transaction_date
                    AND insider_name = :insider_name
                    AND shares = :shares
                    LIMIT 1
                """)
                
                result = await db.execute(check_query, {
                    "ticker": txn["ticker"],
                    "transaction_date": txn["transaction_date"],
                    "insider_name": txn["insider_name"],
                    "shares": txn["shares"]
                })
                
                existing = result.fetchone()
                
                if not existing:
                    # Insert new transaction
                    insert_query = text("""
                        INSERT INTO insider_transactions (
                            ticker, company_name, filing_date, transaction_date,
                            insider_name, title, is_director, is_officer,
                            is_ten_percent_owner, transaction_code, transaction_type,
                            shares, price, transaction_value, shares_after,
                            is_10b51_plan, created_at
                        ) VALUES (
                            :ticker, :company_name, :filing_date, :transaction_date,
                            :insider_name, :title, :is_director, :is_officer,
                            :is_ten_percent_owner, :transaction_code, :transaction_type,
                            :shares, :price, :transaction_value, :shares_after,
                            :is_10b51_plan, NOW()
                        )
                    """)
                    
                    await db.execute(insert_query, txn)
                    saved_count += 1
                    
            except Exception as e:
                logger.warning(f"Error saving transaction: {e}")
                continue
        
        await db.commit()
    
    return saved_count


async def ensure_table_exists():
    """
    Ensure the insider_transactions table exists
    """
    from app.db.session import AsyncSessionLocal
    from sqlalchemy import text
    
    create_table_sql = text("""
        CREATE TABLE IF NOT EXISTS insider_transactions (
            id SERIAL PRIMARY KEY,
            ticker VARCHAR(20) NOT NULL,
            company_name VARCHAR(255),
            filing_date DATE,
            transaction_date DATE NOT NULL,
            insider_name VARCHAR(255) NOT NULL,
            title VARCHAR(255),
            is_director BOOLEAN DEFAULT FALSE,
            is_officer BOOLEAN DEFAULT FALSE,
            is_ten_percent_owner BOOLEAN DEFAULT FALSE,
            transaction_code VARCHAR(10),
            transaction_type VARCHAR(10),
            shares DECIMAL(20, 4),
            price DECIMAL(20, 4),
            transaction_value DECIMAL(20, 2),
            shares_after DECIMAL(20, 4),
            is_10b51_plan BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT NOW(),
            
            -- Indexes for common queries
            CONSTRAINT idx_insider_ticker_date UNIQUE (ticker, transaction_date, insider_name, shares)
        );
        
        CREATE INDEX IF NOT EXISTS idx_insider_ticker ON insider_transactions(ticker);
        CREATE INDEX IF NOT EXISTS idx_insider_date ON insider_transactions(transaction_date);
        CREATE INDEX IF NOT EXISTS idx_insider_type ON insider_transactions(transaction_type);
    """)
    
    async with AsyncSessionLocal() as db:
        try:
            await db.execute(create_table_sql)
            await db.commit()
            logger.info("✅ insider_transactions table ready")
        except Exception as e:
            logger.error(f"Error creating table: {e}")
            # Table might already exist with different constraint
            await db.rollback()


async def fetch_all_form4_data():
    """
    Main function to fetch Form 4 data for all tracked stocks
    """
    logger.info("🚀 Starting Form 4 Data Fetcher...")
    
    # Ensure table exists
    await ensure_table_exists()
    
    # Date range: last 2 years
    to_date = datetime.now().strftime("%Y-%m-%d")
    from_date = (datetime.now() - timedelta(days=730)).strftime("%Y-%m-%d")
    
    logger.info(f"📅 Date range: {from_date} to {to_date}")
    logger.info(f"📋 Stocks to process: {len(POPULAR_STOCKS)}")
    
    total_filings = 0
    total_transactions = 0
    
    for i, ticker in enumerate(POPULAR_STOCKS):
        logger.info(f"\n🔄 [{i+1}/{len(POPULAR_STOCKS)}] Processing {ticker}...")
        
        try:
            # Fetch Form 4 filings
            filings = await fetch_form4_from_sec_api(ticker, from_date, to_date, size=50)
            logger.info(f"   📄 Found {len(filings)} Form 4 filings")
            
            if filings:
                total_filings += len(filings)
                
                # Parse each filing
                all_transactions = []
                for filing in filings:
                    transactions = await parse_form4_filing(filing)
                    all_transactions.extend(transactions)
                
                logger.info(f"   📊 Parsed {len(all_transactions)} transactions")
                
                # Save to database
                saved = await save_transactions_to_db(all_transactions)
                total_transactions += saved
                logger.info(f"   ✅ Saved {saved} new transactions to database")
            
            # Rate limiting: wait 0.5 seconds between API calls
            await asyncio.sleep(0.5)
            
        except Exception as e:
            logger.error(f"   ❌ Error processing {ticker}: {e}")
            continue
    
    logger.info(f"\n{'='*60}")
    logger.info(f"✨ Form 4 Data Fetch Complete!")
    logger.info(f"   📄 Total filings processed: {total_filings}")
    logger.info(f"   📊 Total transactions saved: {total_transactions}")
    logger.info(f"{'='*60}")


if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    asyncio.run(fetch_all_form4_data())

