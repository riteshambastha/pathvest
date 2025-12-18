"""
Data endpoints for date ranges and market data
"""

from fastapi import APIRouter, HTTPException
from sqlalchemy import text
from app.db.session import get_db

router = APIRouter()


@router.get("/date-range")
async def get_available_date_range():
    """Get the available date range from PostgreSQL data"""
    try:
        async for db in get_db():
            query = text("""
                SELECT 
                    MIN(filing_date) as min_date,
                    MAX(filing_date) as max_date
                FROM filings
                WHERE filing_date IS NOT NULL
            """)
            
            result = await db.execute(query)
            row = result.fetchone()
            
            if row and row.min_date and row.max_date:
                return {
                    "min_date": row.min_date.strftime("%Y-%m-%d"),
                    "max_date": row.max_date.strftime("%Y-%m-%d"),
                    "years_covered": row.max_date.year - row.min_date.year + 1,
                    "source": "postgresql"
                }
        
        # Fallback if no data
        return {
            "min_date": "2019-02-14",
            "max_date": "2024-12-31",
            "years_covered": 6,
            "source": "fallback"
        }
        
    except Exception as e:
        print(f"Error fetching date range: {e}")
        # Return fallback range
        return {
            "min_date": "2019-02-14",
            "max_date": "2024-12-31",
            "years_covered": 6,
            "source": "fallback_error"
        }

