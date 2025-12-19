"""
SEC Data API Endpoints
"""

from typing import Optional, Annotated
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.auth import get_current_user
from app.db.session import get_db
from app.schemas.user import User
from app.schemas.institution import Institution
from app.schemas.filing import Filing, FilingWithInstitution
from app.schemas.holding import Holding, HoldingWithPercentage
from app.services.sec_service import SECService

router = APIRouter()


@router.get("/institutions", response_model=list[Institution])
async def get_institutions(
    db: AsyncSession = Depends(get_db),
    popular_only: bool = Query(False, description="Return only popular institutions")
):
    """Get list of institutions (public endpoint)"""
    institutions = await SECService.get_all_institutions(db, popular_only)
    
    # If no institutions, seed popular ones
    if not institutions:
        await SECService.seed_popular_institutions(db)
        institutions = await SECService.get_all_institutions(db, popular_only)
    
    return institutions


@router.post("/institutions/seed", status_code=status.HTTP_201_CREATED)
async def seed_institutions(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db)
):
    """Seed popular institutions into database"""
    await SECService.seed_popular_institutions(db)
    return {"message": "Popular institutions seeded successfully"}


@router.get("/filings/search")
async def search_filings(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
    cik: Optional[str] = Query(None, description="Company CIK"),
    form_type: str = Query("13F-HR", description="Form type"),
    from_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    to_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    size: int = Query(10, ge=1, le=100, description="Number of results"),
    force_refresh: bool = Query(False, description="Force refresh from API")
):
    """
    Search for SEC filings with smart caching
    - First checks database cache
    - Only queries API if not cached (preserves API request count)
    - Stores results for future use
    """
    try:
        filings = await SECService.fetch_and_cache_filings(
            db=db,
            cik=cik,
            form_type=form_type,
            from_date=from_date,
            to_date=to_date,
            size=size,
            force_refresh=force_refresh
        )
        
        # Format response
        return {
            "total": len(filings),
            "filings": [
                {
                    "id": f.id,
                    "accessionNo": f.accession_no,
                    "cik": f.institution.cik,
                    "companyName": f.institution.name,
                    "formType": f.form_type,
                    "filedAt": f.filed_at.isoformat(),
                    "periodOfReport": f.period_of_report,
                    "linkToTxt": f.link_to_txt,
                    "linkToHtml": f.link_to_html,
                    "linkToFilingDetails": f.link_to_filing_details,
                    "totalHoldings": f.total_holdings,
                    "totalValue": f.total_value,
                }
                for f in filings
            ],
            "cached": not force_refresh
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error searching filings: {str(e)}"
        )


@router.get("/filings/{filing_id}", response_model=Filing)
async def get_filing(
    filing_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db)
):
    """Get filing by ID"""
    filing = await SECService.get_filing_with_holdings(db, filing_id)
    
    if not filing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Filing not found"
        )
    
    return filing


@router.get("/filings/{filing_id}/holdings")
async def get_filing_holdings(
    filing_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db)
):
    """Get holdings for a specific filing"""
    filing = await SECService.get_filing_with_holdings(db, filing_id)
    
    if not filing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Filing not found"
        )
    
    # If no holdings cached, try to fetch
    if not filing.holdings:
        holdings = await SECService.fetch_and_cache_holdings(db, filing)
    else:
        holdings = filing.holdings
    
    # Calculate percentages
    total_value = filing.total_value or sum(h.value for h in holdings)
    
    holdings_with_pct = []
    for holding in holdings:
        pct = (holding.value / total_value * 100) if total_value > 0 else 0
        holdings_with_pct.append({
            "id": holding.id,
            "nameOfIssuer": holding.name_of_issuer,
            "cusip": holding.cusip,
            "ticker": holding.ticker,
            "value": holding.value,
            "valueUsd": holding.value * 1000,
            "sharesOrPrnAmt": holding.shares_or_prn_amt,
            "sharesOrPrnAmtType": holding.shares_or_prn_amt_type,
            "percentage": round(pct, 4)
        })
    
    return {
        "filing_id": filing.id,
        "accession_no": filing.accession_no,
        "total_holdings": filing.total_holdings or len(holdings),
        "total_value": total_value,
        "holdings": holdings_with_pct
    }
