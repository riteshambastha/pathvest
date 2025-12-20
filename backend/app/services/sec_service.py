"""
SEC-API.io Service with Database Caching
"""

import json
import httpx
import re
import xml.etree.ElementTree as ET
from typing import List, Dict, Optional
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models.institution import Institution
from app.models.filing import Filing
from app.models.holding import Holding


class SECService:
    """Service for SEC-API.io with database caching to preserve API request counts"""
    
    BASE_URL = "https://api.sec-api.io"
    
    # Popular institutions (pre-seeded)
    POPULAR_INSTITUTIONS = [
        {"name": "Renaissance Technologies", "cik": "0001037389"},
        {"name": "Berkshire Hathaway", "cik": "0001067983"},
        {"name": "Bridgewater Associates", "cik": "0001350694"},
        {"name": "Citadel Advisors", "cik": "0001423053"},
        {"name": "Millennium Management", "cik": "0001149071"},
        {"name": "Two Sigma Investments", "cik": "0001496147"},
        {"name": "D.E. Shaw & Co", "cik": "0001009207"},
        {"name": "Elliott Management", "cik": "0001003520"},
        {"name": "Baupost Group", "cik": "0001061768"},
        {"name": "Tiger Global Management", "cik": "0001167483"},
    ]
    
    @staticmethod
    async def get_or_create_institution(db: AsyncSession, cik: str, name: str = None) -> Institution:
        """Get institution from DB or create if not exists"""
        cik_clean = cik.lstrip('0')
        
        # Try to find existing
        result = await db.execute(
            select(Institution).where(Institution.cik == cik)
        )
        institution = result.scalar_one_or_none()
        
        if not institution:
            # Create new
            institution = Institution(
                cik=cik,
                name=name or f"Institution {cik}",
                is_popular=False
            )
            db.add(institution)
            await db.commit()
            await db.refresh(institution)
        
        return institution
    
    @staticmethod
    async def get_all_institutions(db: AsyncSession, popular_only: bool = False) -> List[Institution]:
        """Get all institutions from database"""
        query = select(Institution)
        
        if popular_only:
            query = query.where(Institution.is_popular == True)
        
        query = query.order_by(Institution.name)
        
        result = await db.execute(query)
        return list(result.scalars().all())
    
    @staticmethod
    async def seed_popular_institutions(db: AsyncSession):
        """Seed popular institutions into database"""
        for inst_data in SECService.POPULAR_INSTITUTIONS:
            result = await db.execute(
                select(Institution).where(Institution.cik == inst_data["cik"])
            )
            existing = result.scalar_one_or_none()
            
            if not existing:
                institution = Institution(
                    cik=inst_data["cik"],
                    name=inst_data["name"],
                    is_popular=True
                )
                db.add(institution)
        
        await db.commit()
    
    @staticmethod
    async def search_filings_from_db(
        db: AsyncSession,
        cik: Optional[str] = None,
        form_type: str = "13F-HR",
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        size: int = 10
    ) -> List[Filing]:
        """Search filings from database cache"""
        query = select(Filing).options(selectinload(Filing.institution))
        
        # Apply filters
        query = query.where(Filing.form_type == form_type)
        
        if cik:
            # Join with institution to filter by CIK
            result = await db.execute(
                select(Institution).where(Institution.cik == cik)
            )
            institution = result.scalar_one_or_none()
            
            if institution:
                query = query.where(Filing.institution_id == institution.id)
        
        if from_date:
            query = query.where(Filing.filed_at >= from_date)
        
        if to_date:
            query = query.where(Filing.filed_at <= to_date)
        
        # Order by filed date descending
        query = query.order_by(Filing.filed_at.desc()).limit(size)
        
        result = await db.execute(query)
        return list(result.scalars().all())
    
    @staticmethod
    async def search_filings_from_api(
        cik: Optional[str] = None,
        form_type: str = "13F-HR",
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        size: int = 10
    ) -> Dict:
        """Search filings from SEC-API.io"""
        
        if not settings.SEC_API_KEY or settings.SEC_API_KEY == "YOUR_API_KEY_HERE":
            raise ValueError("SEC_API_KEY not configured")
        
        query_parts = [f'formType:"{form_type}"']
        
        if cik:
            cik_clean = cik.lstrip('0')  # Remove leading zeros
            query_parts.append(f'cik:{cik_clean}')
        
        if from_date and to_date:
            query_parts.append(f'filedAt:[{from_date} TO {to_date}]')
        
        query = " AND ".join(query_parts)
        
        payload = {
            "query": {"query_string": {"query": query}},
            "from": "0",
            "size": str(size),
            "sort": [{"filedAt": {"order": "desc"}}]
        }
        
        headers = {
            "Authorization": settings.SEC_API_KEY,
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{SECService.BASE_URL}",
                json=payload,
                headers=headers,
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()
    
    @staticmethod
    async def fetch_and_cache_filings(
        db: AsyncSession,
        cik: Optional[str] = None,
        form_type: str = "13F-HR",
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        size: int = 10,
        force_refresh: bool = False
    ) -> List[Filing]:
        """
        Fetch filings from API and cache in database
        Smart caching: only query API if not in DB
        """
        
        # First, check if we have data in DB (unless force refresh)
        if not force_refresh:
            from_dt = datetime.fromisoformat(from_date) if from_date else None
            to_dt = datetime.fromisoformat(to_date) if to_date else None
            
            db_filings = await SECService.search_filings_from_db(
                db, cik, form_type, from_dt, to_dt, size
            )
            
            if db_filings:
                print(f"✅ Serving {len(db_filings)} filings from database cache")
                return db_filings
        
        # Not in DB or force refresh - query API
        print(f"🔄 Querying SEC-API.io (preserving API request count by caching)...")
        api_data = await SECService.search_filings_from_api(
            cik, form_type, from_date, to_date, size
        )
        
        filings_list = []
        
        # Cache the results in database
        for filing_data in api_data.get("filings", []):
            filing_cik = filing_data.get("cik")
            filing_company = filing_data.get("companyName", "Unknown")
            
            # Get or create institution
            institution = await SECService.get_or_create_institution(
                db, filing_cik, filing_company
            )
            
            # Check if filing already exists
            result = await db.execute(
                select(Filing).where(Filing.accession_no == filing_data.get("accessionNo"))
            )
            existing_filing = result.scalar_one_or_none()
            
            if not existing_filing:
                # Create new filing
                # Parse filed_at and convert to timezone-naive UTC
                filed_at_str = filing_data.get("filedAt")
                if filed_at_str:
                    filed_at_dt = datetime.fromisoformat(filed_at_str.replace("Z", "+00:00"))
                    # Convert to UTC and remove timezone info for database
                    filed_at_naive = filed_at_dt.astimezone(timezone.utc).replace(tzinfo=None)
                else:
                    filed_at_naive = datetime.utcnow()
                
                filing = Filing(
                    institution_id=institution.id,
                    accession_no=filing_data.get("accessionNo"),
                    form_type=filing_data.get("formType"),
                    filed_at=filed_at_naive,
                    filing_date=filed_at_naive.date(),
                    period_of_report=filing_data.get("periodOfReport"),
                    link_to_txt=filing_data.get("linkToTxt"),
                    link_to_html=filing_data.get("linkToHtml"),
                    link_to_filing_details=filing_data.get("linkToFilingDetails"),
                    raw_response=json.dumps(filing_data)
                )
                filing.institution = institution  # Set the relationship directly
                db.add(filing)
                await db.commit()
                await db.refresh(filing)
                filings_list.append(filing)
            else:
                filings_list.append(existing_filing)
        
        print(f"✅ Cached {len(filings_list)} filings in database")
        
        # Eagerly load institution relationships for all filings
        for filing in filings_list:
            await db.refresh(filing, ['institution'])
        
        return filings_list
    
    @staticmethod
    async def get_filing_with_holdings(
        db: AsyncSession,
        filing_id: int
    ) -> Optional[Filing]:
        """Get filing with all holdings loaded"""
        result = await db.execute(
            select(Filing)
            .options(
                selectinload(Filing.holdings),
                selectinload(Filing.institution)
            )
            .where(Filing.id == filing_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def _fetch_info_table_xml(filing: Filing) -> Optional[bytes]:
        """
        Fetch information table XML from SEC.gov
        Tries multiple common filename patterns
        """
        # Parse accession number to build base URL
        # Format: 0001037389-25-000064
        parts = filing.accession_no.split('-')
        if len(parts) != 3:
            print(f"⚠️  Invalid accession number format: {filing.accession_no}")
            return None
        
        cik = parts[0].lstrip('0')
        base_url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{filing.accession_no.replace('-', '')}"
        
        sec_headers = {
            'User-Agent': 'Pathvest Backtesting Engine research@pathvest.com',
            'Accept-Encoding': 'gzip, deflate',
            'Host': 'www.sec.gov'
        }
        
        # Try common info table file patterns
        filenames_to_try = [
            f"{filing.accession_no}.txt",  # Main SGML filing
            "form13fInfoTable.xml",
            "informationTable.xml",
            "infotable.xml"
        ]
        
        async with httpx.AsyncClient() as client:
            for filename in filenames_to_try:
                url = f"{base_url}/{filename}"
                
                try:
                    response = await client.get(url, headers=sec_headers, timeout=30.0)
                    
                    if response.status_code == 200:
                        print(f"   ✅ Found: {filename}")
                        return response.content
                        
                except Exception as e:
                    continue
        
        return None
    
    @staticmethod
    def _parse_info_tables(content: bytes) -> List[Dict]:
        """
        Parse infoTable elements from XML/SGML content
        Returns list of holding dictionaries
        """
        holdings = []
        
        try:
            # First, try to decode as text to check if it's SGML (.txt file)
            content_str = content.decode('utf-8')
            
            # Strategy 1: Try to find <informationTable> wrapper (some filings have this)
            if '<informationTable>' in content_str:
                # Extract the informationTable section
                match = re.search(
                    r'<informationTable>(.*?)</informationTable>',
                    content_str,
                    re.DOTALL | re.IGNORECASE
                )
                
                if match:
                    table_xml = f"<informationTable>{match.group(1)}</informationTable>"
                    content = table_xml.encode('utf-8')
            
            # Strategy 2: No wrapper, but multiple <infoTable> tags (Renaissance Technologies format)
            # Find all infoTable sections and wrap them
            elif '<infoTable>' in content_str or '<infotable>' in content_str.lower():
                print(f"   Found <infoTable> tags without wrapper, extracting all...")
                
                # Find all infoTable sections using regex
                info_tables_matches = re.findall(
                    r'<infoTable>(.*?)</infoTable>',
                    content_str,
                    re.DOTALL | re.IGNORECASE
                )
                
                if info_tables_matches:
                    print(f"   Found {len(info_tables_matches)} <infoTable> sections via regex")
                    # Wrap all infoTables in a root element for parsing
                    xml_content = "<root>"
                    for table_content in info_tables_matches:
                        xml_content += f"<infoTable>{table_content}</infoTable>"
                    xml_content += "</root>"
                    content = xml_content.encode('utf-8')
                else:
                    print(f"   ⚠️  Regex found no <infoTable> sections")
                    return []
            
            # Parse as XML
            try:
                root = ET.fromstring(content)
            except ET.ParseError as e:
                print(f"   ⚠️  XML Parse Error: {e}")
                print(f"   Content preview (first 500 chars): {content[:500]}")
                return []
            
            # Find all infoTable elements (try different approaches)
            info_tables = root.findall('.//infoTable')
            
            # If not found, try with namespace
            if not info_tables:
                ns = {'n': 'http://www.sec.gov/edgar/document/thirteenf/informationtable'}
                info_tables = root.findall('.//n:infoTable', ns)
            
            # If still not found, iterate through all elements
            if not info_tables:
                info_tables = [elem for elem in root.iter() if 'infoTable' in elem.tag.lower()]
            
            print(f"   Found {len(info_tables)} infoTable elements")
            
            # Parse each infoTable element
            for info_table in info_tables:
                holding = {}
                
                # Helper function to find element with or without namespace
                def find_elem(parent, tag_name):
                    # Try direct
                    elem = parent.find(f'.//{tag_name}')
                    if elem is not None:
                        return elem
                    
                    # Try with namespace
                    elem = parent.find(f'.//{{http://www.sec.gov/edgar/document/thirteenf/informationtable}}{tag_name}')
                    if elem is not None:
                        return elem
                    
                    # Try lowercase
                    elem = parent.find(f'.//{tag_name.lower()}')
                    return elem
                
                # Extract nameOfIssuer
                name_elem = find_elem(info_table, 'nameOfIssuer')
                holding['nameOfIssuer'] = name_elem.text.strip() if name_elem is not None and name_elem.text else None
                
                # Extract CUSIP
                cusip_elem = find_elem(info_table, 'cusip')
                holding['cusip'] = cusip_elem.text.strip() if cusip_elem is not None and cusip_elem.text else None
                
                # Extract value (in thousands)
                value_elem = find_elem(info_table, 'value')
                if value_elem is not None and value_elem.text:
                    try:
                        holding['value'] = float(value_elem.text.strip())
                    except (ValueError, AttributeError):
                        holding['value'] = None
                else:
                    holding['value'] = None
                
                # Extract shares/principal amount
                sshPrnamt_elem = find_elem(info_table, 'sshPrnamt')
                sshPrnamtType_elem = find_elem(info_table, 'sshPrnamtType')
                
                if sshPrnamt_elem is not None and sshPrnamt_elem.text:
                    try:
                        holding['sharesOrPrnAmt'] = int(float(sshPrnamt_elem.text.strip()))
                    except (ValueError, AttributeError):
                        holding['sharesOrPrnAmt'] = None
                else:
                    holding['sharesOrPrnAmt'] = None
                
                holding['sharesOrPrnAmtType'] = sshPrnamtType_elem.text.strip() if sshPrnamtType_elem is not None and sshPrnamtType_elem.text else None
                
                # Extract investment discretion
                discretion_elem = find_elem(info_table, 'investmentDiscretion')
                holding['investmentDiscretion'] = discretion_elem.text.strip() if discretion_elem is not None and discretion_elem.text else None
                
                # Extract voting authority
                voting_sole_elem = find_elem(info_table, 'Sole')
                voting_shared_elem = find_elem(info_table, 'Shared')
                voting_none_elem = find_elem(info_table, 'None')
                
                if voting_sole_elem is not None and voting_sole_elem.text:
                    try:
                        holding['votingAuthoritySole'] = int(float(voting_sole_elem.text.strip()))
                    except (ValueError, AttributeError):
                        holding['votingAuthoritySole'] = None
                else:
                    holding['votingAuthoritySole'] = None
                
                if voting_shared_elem is not None and voting_shared_elem.text:
                    try:
                        holding['votingAuthorityShared'] = int(float(voting_shared_elem.text.strip()))
                    except (ValueError, AttributeError):
                        holding['votingAuthorityShared'] = None
                else:
                    holding['votingAuthorityShared'] = None
                
                if voting_none_elem is not None and voting_none_elem.text:
                    try:
                        holding['votingAuthorityNone'] = int(float(voting_none_elem.text.strip()))
                    except (ValueError, AttributeError):
                        holding['votingAuthorityNone'] = None
                else:
                    holding['votingAuthorityNone'] = None
                
                # Only add if we have at least name and CUSIP
                if holding.get('nameOfIssuer') and holding.get('cusip'):
                    holdings.append(holding)
            
            return holdings
            
        except Exception as e:
            print(f"   ⚠️  Error parsing XML: {e}")
            return []
    
    @staticmethod
    async def _save_holdings_to_db(
        db: AsyncSession,
        filing: Filing,
        holdings_data: List[Dict]
    ):
        """Bulk insert holdings into database"""
        
        if not holdings_data:
            return
        
        print(f"   Saving {len(holdings_data)} holdings to database...")
        
        holdings_objects = []
        total_value = 0
        
        for h_data in holdings_data:
            # Skip if missing required fields
            if not h_data.get('nameOfIssuer') or not h_data.get('cusip'):
                continue
            
            # Skip if value is None or invalid
            value = h_data.get('value')
            if value is None or value <= 0:
                continue
            
            total_value += value
            
            holding = Holding(
                filing_id=filing.id,
                name_of_issuer=h_data['nameOfIssuer'][:255],  # Truncate if needed
                cusip=h_data['cusip'][:20],
                ticker=None,  # Not in XML, could be enriched later
                value=value,
                shares_or_prn_amt=h_data.get('sharesOrPrnAmt'),
                shares_or_prn_amt_type=h_data.get('sharesOrPrnAmtType'),
                investment_discretion=h_data.get('investmentDiscretion'),
                voting_authority_sole=h_data.get('votingAuthoritySole'),
                voting_authority_shared=h_data.get('votingAuthorityShared'),
                voting_authority_none=h_data.get('votingAuthorityNone')
            )
            holdings_objects.append(holding)
        
        # Bulk insert
        if holdings_objects:
            db.add_all(holdings_objects)
            
            # Update filing summary if not already set
            if not filing.total_holdings:
                filing.total_holdings = len(holdings_objects)
            if not filing.total_value:
                filing.total_value = total_value
            
            await db.commit()
            print(f"   ✅ Saved {len(holdings_objects)} holdings (Total AUM: ${total_value:,.0f}K)")
    
    @staticmethod
    async def fetch_and_cache_holdings(
        db: AsyncSession,
        filing: Filing
    ) -> List[Holding]:
        """
        Fetch holdings for a filing and cache in database
        Full implementation with XML parsing
        """
        
        # Check if holdings already cached (safely for async)
        # Instead of accessing filing.holdings directly which triggers lazy load
        stmt = select(Holding).where(Holding.filing_id == filing.id).limit(1)
        result = await db.execute(stmt)
        if result.scalar_one_or_none():
            # Holdings exist, load them all
            stmt = select(Holding).where(Holding.filing_id == filing.id)
            result = await db.execute(stmt)
            holdings = result.scalars().all()
            print(f"✅ Serving {len(holdings)} holdings from database cache")
            return list(holdings)
        
        print(f"🔄 Fetching holdings from SEC.gov for filing {filing.accession_no}...")
        
        # Parse the filing URL to get base path
        if not filing.link_to_filing_details:
            raise ValueError("Filing URL not available")
        
        try:
            sec_headers = {
                'User-Agent': 'Pathvest Backtesting Engine research@pathvest.com',
                'Accept-Encoding': 'gzip, deflate',
                'Host': 'www.sec.gov'
            }
            
            # Step 1: Try to fetch primary_doc.xml to get summary (but don't fail if it has issues)
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        filing.link_to_filing_details,
                        headers=sec_headers,
                        timeout=30.0
                    )
                    response.raise_for_status()
                    
                    # Parse XML for summary
                    root = ET.fromstring(response.content)
                    ns = {'n': 'http://www.sec.gov/edgar/thirteenffiler'}
                    
                    # Extract summary data from cover page
                    form_data = root.find('.//n:formData', ns)
                    if form_data:
                        summary_page = form_data.find('.//n:summaryPage', ns)
                        if summary_page:
                            table_entry_total = summary_page.find('.//n:tableEntryTotal', ns)
                            table_value_total = summary_page.find('.//n:tableValueTotal', ns)
                            
                            if table_entry_total is not None and table_entry_total.text:
                                filing.total_holdings = int(table_entry_total.text)
                                print(f"   Total holdings from summary: {filing.total_holdings:,}")
                            
                            if table_value_total is not None and table_value_total.text:
                                filing.total_value = float(table_value_total.text)
                                print(f"   Total AUM from summary: ${filing.total_value:,.0f}K")
            except ET.ParseError as e:
                print(f"   ⚠️  Could not parse primary_doc.xml (malformed XML): {e}")
                print(f"   Continuing with info table extraction...")
            except Exception as e:
                print(f"   ⚠️  Could not fetch summary from primary_doc.xml: {e}")
                print(f"   Continuing with info table extraction...")
            
            # Step 2: Fetch information table with detailed holdings
            print(f"   Fetching detailed holdings...")
            info_table_content = await SECService._fetch_info_table_xml(filing)
            
            if info_table_content:
                # Step 3: Parse holdings from XML
                holdings_data = SECService._parse_info_tables(info_table_content)
                
                if holdings_data:
                    print(f"   Parsed {len(holdings_data)} holdings from XML")
                    
                    # Step 4: Save to database
                    await SECService._save_holdings_to_db(db, filing, holdings_data)
                    
                    # Refresh filing with holdings
                    await db.refresh(filing, ['holdings'])
                    
                    print(f"✅ Cached {len(filing.holdings)} holdings in database")
                    return filing.holdings
                else:
                    print(f"   ⚠️  No holdings found in info table XML")
            else:
                print(f"   ⚠️  Could not fetch info table XML")
            
            # Even if we couldn't get holdings, save the summary
            await db.commit()
            
            # Return empty list but with updated summary
            print(f"✅ Updated filing summary: {filing.total_holdings or 0} holdings, ${filing.total_value or 0:,.0f}K total value")
            print(f"   (Individual holdings data not available)")
            return []
            
        except Exception as e:
            print(f"⚠️  Error fetching holdings: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    @staticmethod
    async def get_filing_by_accession(db: AsyncSession, accession_no: str) -> Optional[Filing]:
        """Get filing by accession number"""
        result = await db.execute(
            select(Filing)
            .options(selectinload(Filing.institution))
            .where(Filing.accession_no == accession_no)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def search_holdings_by_ticker(
        db: AsyncSession,
        ticker: str,
        limit: int = 100
    ) -> List[Holding]:
        """Search holdings by ticker symbol"""
        result = await db.execute(
            select(Holding)
            .options(selectinload(Holding.filing))
            .where(Holding.ticker == ticker.upper())
            .order_by(Holding.value.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
