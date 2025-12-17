"""
PostgreSQL Service for SEC Data Warehouse
Drop-in replacement for BigQueryService using PostgreSQL
"""

from typing import List, Dict, Optional, Any
from datetime import datetime, date
from sqlalchemy import create_engine, text, MetaData, Table, Column, String, Integer, Float, Date, DateTime, Boolean, Text, BigInteger
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
import os
import json

from app.core.config import settings


class PostgresService:
    """Service for PostgreSQL operations on SEC data warehouse - mirrors BigQueryService interface"""
    
    def __init__(self):
        """Initialize PostgreSQL client"""
        self.database_url = settings.DATABASE_URL
        
        if not self.database_url or not self.database_url.startswith('postgresql'):
            print("WARNING: PostgreSQL client not initialized. Running in mock mode.")
            self.engine = None
            self.SessionLocal = None
            return
        
        # Create engine with connection pooling
        self.engine = create_engine(
            self.database_url,
            poolclass=QueuePool,
            pool_size=settings.DATABASE_POOL_SIZE,
            max_overflow=settings.DATABASE_MAX_OVERFLOW,
            pool_pre_ping=True,  # Verify connections before using
            echo=False
        )
        
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        # Create tables if they don't exist
        self._create_tables_if_not_exist()
    
    def _create_tables_if_not_exist(self):
        """Create all required tables if they don't exist"""
        if not self.engine:
            return
        
        metadata = MetaData()
        
        # SEC Institutions table
        Table('sec_institutions', metadata,
            Column('id', Integer, primary_key=True, autoincrement=True),
            Column('cik', String(20), unique=True, nullable=False, index=True),
            Column('name', String(255), nullable=False),
            Column('metadata_json', Text),
            Column('last_updated', DateTime, default=datetime.utcnow),
            Column('created_at', DateTime, default=datetime.utcnow)
        )
        
        # SEC 13F Filings table
        Table('sec_filings_13f', metadata,
            Column('id', Integer, primary_key=True, autoincrement=True),
            Column('filing_id', String(100), unique=True, nullable=False, index=True),
            Column('cik', String(20), nullable=False, index=True),
            Column('filing_date', Date, nullable=False, index=True),
            Column('period_end_date', Date, nullable=False),
            Column('accession_number', String(50)),
            Column('form_type', String(20), default='13F-HR'),
            Column('total_value', BigInteger, default=0),
            Column('holdings_count', Integer, default=0),
            Column('created_at', DateTime, default=datetime.utcnow)
        )
        
        # SEC 13F Holdings table
        Table('sec_holdings_13f', metadata,
            Column('id', Integer, primary_key=True, autoincrement=True),
            Column('holding_id', String(100), unique=True, nullable=False),
            Column('filing_id', String(100), nullable=False, index=True),
            Column('cusip', String(9), nullable=False, index=True),
            Column('ticker', String(10), index=True),
            Column('name_of_issuer', String(255)),
            Column('value', BigInteger, default=0),
            Column('shares_or_prn_amt', BigInteger, default=0),
            Column('shares_or_prn_amt_type', String(20)),
            Column('investment_discretion', String(10)),
            Column('voting_authority_sole', BigInteger, default=0),
            Column('voting_authority_shared', BigInteger, default=0),
            Column('voting_authority_none', BigInteger, default=0),
            Column('created_at', DateTime, default=datetime.utcnow)
        )
        
        # Form 4 Insider Transactions table
        Table('sec_form4_transactions', metadata,
            Column('id', Integer, primary_key=True, autoincrement=True),
            Column('transaction_id', String(100), unique=True, nullable=False),
            Column('accession_number', String(50)),
            Column('filing_date', Date, nullable=False, index=True),
            Column('issuer_cik', String(20), index=True),
            Column('issuer_name', String(255)),
            Column('ticker', String(10), index=True),
            Column('reporting_owner_name', String(255)),
            Column('reporting_owner_cik', String(20)),
            Column('relationship', String(255)),
            Column('is_director', Boolean, default=False),
            Column('is_officer', Boolean, default=False),
            Column('officer_title', String(255)),
            Column('is_ten_percent_owner', Boolean, default=False),
            Column('transaction_code', String(10), index=True),
            Column('transaction_date', Date, nullable=False, index=True),
            Column('deemed_execution_date', Date),
            Column('shares', BigInteger, default=0),
            Column('price_per_share', Float, default=0),
            Column('acquired_disposed_code', String(1)),
            Column('ownership_nature', String(20), default='direct'),
            Column('created_at', DateTime, default=datetime.utcnow)
        )
        
        # CUSIP Ticker Mapping table
        Table('sec_cusip_ticker_mapping', metadata,
            Column('id', Integer, primary_key=True, autoincrement=True),
            Column('cusip', String(9), nullable=False, index=True),
            Column('ticker', String(10), nullable=False, index=True),
            Column('effective_date', Date, nullable=False),
            Column('end_date', Date),
            Column('created_at', DateTime, default=datetime.utcnow)
        )
        
        # Market Index Constituents table
        Table('market_index_constituents', metadata,
            Column('id', Integer, primary_key=True, autoincrement=True),
            Column('index_name', String(50), nullable=False, index=True),
            Column('ticker', String(10), nullable=False, index=True),
            Column('effective_date', Date, nullable=False),
            Column('end_date', Date),
            Column('created_at', DateTime, default=datetime.utcnow)
        )
        
        # Stock Sector Classification table
        Table('stock_sector_classification', metadata,
            Column('id', Integer, primary_key=True, autoincrement=True),
            Column('ticker', String(10), nullable=False, unique=True, index=True),
            Column('sector', String(100)),
            Column('industry', String(200)),
            Column('created_at', DateTime, default=datetime.utcnow)
        )
        
        # Stock Market Cap History table
        Table('stock_market_cap_history', metadata,
            Column('id', Integer, primary_key=True, autoincrement=True),
            Column('ticker', String(10), nullable=False, index=True),
            Column('date', Date, nullable=False, index=True),
            Column('market_cap', BigInteger),
            Column('created_at', DateTime, default=datetime.utcnow)
        )
        
        # Stock Liquidity Metrics table
        Table('stock_liquidity_metrics', metadata,
            Column('id', Integer, primary_key=True, autoincrement=True),
            Column('ticker', String(10), nullable=False, index=True),
            Column('date', Date, nullable=False, index=True),
            Column('avg_daily_volume', BigInteger),
            Column('avg_daily_value', BigInteger),
            Column('created_at', DateTime, default=datetime.utcnow)
        )
        
        # Institutional Holdings (legacy table)
        Table('institutional_holdings', metadata,
            Column('id', Integer, primary_key=True, autoincrement=True),
            Column('cik', String(20), nullable=False, index=True),
            Column('institution', String(255)),
            Column('filing_date', Date, nullable=False, index=True),
            Column('report_period', Date),
            Column('ticker', String(10), nullable=False, index=True),
            Column('cusip', String(9)),
            Column('shares', BigInteger),
            Column('value', BigInteger),
            Column('percent_portfolio', Float),
            Column('created_at', DateTime, default=datetime.utcnow)
        )
        
        # Create all tables
        metadata.create_all(self.engine)
        print("✅ PostgreSQL tables created/verified")
    
    def _get_session(self) -> Session:
        """Get database session"""
        if not self.SessionLocal:
            raise Exception("PostgreSQL not initialized")
        return self.SessionLocal()
    
    # ==================== Institution Operations ====================
    
    async def insert_institution(self, cik: str, name: str, metadata: Dict[str, Any] = None) -> bool:
        """Insert or update institution record"""
        if not self.engine:
            return False
        
        session = self._get_session()
        try:
            # Upsert logic
            result = session.execute(
                text("""
                    INSERT INTO sec_institutions (cik, name, metadata_json, last_updated, created_at)
                    VALUES (:cik, :name, :metadata_json, :last_updated, :created_at)
                    ON CONFLICT (cik) DO UPDATE
                    SET name = EXCLUDED.name,
                        metadata_json = EXCLUDED.metadata_json,
                        last_updated = EXCLUDED.last_updated
                """),
                {
                    "cik": cik,
                    "name": name,
                    "metadata_json": json.dumps(metadata) if metadata else None,
                    "last_updated": datetime.utcnow(),
                    "created_at": datetime.utcnow()
                }
            )
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            print(f"Error inserting institution: {e}")
            return False
        finally:
            session.close()
    
    async def get_institution_by_cik(self, cik: str) -> Optional[Dict[str, Any]]:
        """Get institution by CIK"""
        if not self.engine:
            return None
        
        session = self._get_session()
        try:
            result = session.execute(
                text("SELECT * FROM sec_institutions WHERE cik = :cik LIMIT 1"),
                {"cik": cik}
            )
            row = result.fetchone()
            if row:
                return dict(row._mapping)
            return None
        except Exception as e:
            print(f"Error querying institution: {e}")
            return None
        finally:
            session.close()
    
    async def get_qualified_institutions(
        self,
        min_aum: float = 1_000_000_000,
        min_track_record_quarters: int = 8,
        as_of_date: Optional[date] = None
    ) -> List[Dict[str, Any]]:
        """Get institutions meeting qualification criteria"""
        if not self.engine:
            return []
        
        as_of_filter = ""
        params = {"min_aum": min_aum, "min_track_record_quarters": min_track_record_quarters}
        
        if as_of_date:
            as_of_filter = "AND f.filing_date <= :as_of_date"
            params["as_of_date"] = as_of_date
        
        session = self._get_session()
        try:
            query = text(f"""
                WITH institution_stats AS (
                    SELECT 
                        i.cik,
                        i.name,
                        COUNT(DISTINCT f.period_end_date) as quarters_filed,
                        MAX(f.total_value) as latest_aum
                    FROM sec_institutions i
                    JOIN sec_filings_13f f ON i.cik = f.cik
                    WHERE 1=1 {as_of_filter}
                    GROUP BY i.cik, i.name
                )
                SELECT *
                FROM institution_stats
                WHERE latest_aum >= :min_aum
                    AND quarters_filed >= :min_track_record_quarters
                ORDER BY latest_aum DESC
            """)
            
            result = session.execute(query, params)
            return [dict(row._mapping) for row in result]
        except Exception as e:
            print(f"Error querying qualified institutions: {e}")
            return []
        finally:
            session.close()
    
    # ==================== 13F Filing Operations ====================
    
    async def insert_filing_13f(self, filing_data: Dict[str, Any]) -> bool:
        """Insert 13F filing record"""
        if not self.engine:
            return False
        
        session = self._get_session()
        try:
            session.execute(
                text("""
                    INSERT INTO sec_filings_13f 
                    (filing_id, cik, filing_date, period_end_date, accession_number, 
                     form_type, total_value, holdings_count, created_at)
                    VALUES (:filing_id, :cik, :filing_date, :period_end_date, :accession_number,
                            :form_type, :total_value, :holdings_count, :created_at)
                    ON CONFLICT (filing_id) DO NOTHING
                """),
                {
                    "filing_id": filing_data.get("filing_id"),
                    "cik": filing_data.get("cik"),
                    "filing_date": filing_data.get("filing_date"),
                    "period_end_date": filing_data.get("period_end_date"),
                    "accession_number": filing_data.get("accession_number"),
                    "form_type": filing_data.get("form_type", "13F-HR"),
                    "total_value": filing_data.get("total_value", 0),
                    "holdings_count": filing_data.get("holdings_count", 0),
                    "created_at": datetime.utcnow()
                }
            )
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            print(f"Error inserting 13F filing: {e}")
            return False
        finally:
            session.close()
    
    async def get_filings_by_cik(
        self,
        cik: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[Dict[str, Any]]:
        """Get all filings for a given CIK within date range"""
        if not self.engine:
            return []
        
        where_clauses = ["cik = :cik"]
        params = {"cik": cik}
        
        if start_date:
            where_clauses.append("filing_date >= :start_date")
            params["start_date"] = start_date
        
        if end_date:
            where_clauses.append("filing_date <= :end_date")
            params["end_date"] = end_date
        
        where_clause = " AND ".join(where_clauses)
        
        session = self._get_session()
        try:
            query = text(f"""
                SELECT * FROM sec_filings_13f
                WHERE {where_clause}
                ORDER BY filing_date DESC
            """)
            
            result = session.execute(query, params)
            return [dict(row._mapping) for row in result]
        except Exception as e:
            print(f"Error querying filings: {e}")
            return []
        finally:
            session.close()
    
    # ==================== Holdings Operations ====================
    
    async def insert_holding_13f(self, holding_data: Dict[str, Any]) -> bool:
        """Insert 13F holding record"""
        if not self.engine:
            return False
        
        session = self._get_session()
        try:
            session.execute(
                text("""
                    INSERT INTO sec_holdings_13f 
                    (holding_id, filing_id, cusip, ticker, name_of_issuer, value, 
                     shares_or_prn_amt, shares_or_prn_amt_type, investment_discretion,
                     voting_authority_sole, voting_authority_shared, voting_authority_none, created_at)
                    VALUES (:holding_id, :filing_id, :cusip, :ticker, :name_of_issuer, :value,
                            :shares_or_prn_amt, :shares_or_prn_amt_type, :investment_discretion,
                            :voting_authority_sole, :voting_authority_shared, :voting_authority_none, :created_at)
                    ON CONFLICT (holding_id) DO NOTHING
                """),
                {
                    "holding_id": holding_data.get("holding_id"),
                    "filing_id": holding_data.get("filing_id"),
                    "cusip": holding_data.get("cusip"),
                    "ticker": holding_data.get("ticker"),
                    "name_of_issuer": holding_data.get("name_of_issuer"),
                    "value": holding_data.get("value", 0),
                    "shares_or_prn_amt": holding_data.get("shares_or_prn_amt", 0),
                    "shares_or_prn_amt_type": holding_data.get("shares_or_prn_amt_type"),
                    "investment_discretion": holding_data.get("investment_discretion"),
                    "voting_authority_sole": holding_data.get("voting_authority_sole", 0),
                    "voting_authority_shared": holding_data.get("voting_authority_shared", 0),
                    "voting_authority_none": holding_data.get("voting_authority_none", 0),
                    "created_at": datetime.utcnow()
                }
            )
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            print(f"Error inserting holding: {e}")
            return False
        finally:
            session.close()
    
    async def bulk_insert_holdings(self, holdings: List[Dict[str, Any]]) -> bool:
        """Bulk insert holdings for better performance"""
        if not self.engine or not holdings:
            return False
        
        session = self._get_session()
        try:
            # Bulk insert using executemany
            batch_size = 500
            for i in range(0, len(holdings), batch_size):
                batch = holdings[i:i + batch_size]
                rows = []
                for holding in batch:
                    rows.append({
                        "holding_id": holding.get("holding_id"),
                        "filing_id": holding.get("filing_id"),
                        "cusip": holding.get("cusip"),
                        "ticker": holding.get("ticker"),
                        "name_of_issuer": holding.get("name_of_issuer"),
                        "value": holding.get("value", 0),
                        "shares_or_prn_amt": holding.get("shares_or_prn_amt", 0),
                        "shares_or_prn_amt_type": holding.get("shares_or_prn_amt_type"),
                        "investment_discretion": holding.get("investment_discretion"),
                        "voting_authority_sole": holding.get("voting_authority_sole", 0),
                        "voting_authority_shared": holding.get("voting_authority_shared", 0),
                        "voting_authority_none": holding.get("voting_authority_none", 0),
                        "created_at": datetime.utcnow()
                    })
                
                session.execute(
                    text("""
                        INSERT INTO sec_holdings_13f 
                        (holding_id, filing_id, cusip, ticker, name_of_issuer, value, 
                         shares_or_prn_amt, shares_or_prn_amt_type, investment_discretion,
                         voting_authority_sole, voting_authority_shared, voting_authority_none, created_at)
                        VALUES (:holding_id, :filing_id, :cusip, :ticker, :name_of_issuer, :value,
                                :shares_or_prn_amt, :shares_or_prn_amt_type, :investment_discretion,
                                :voting_authority_sole, :voting_authority_shared, :voting_authority_none, :created_at)
                        ON CONFLICT (holding_id) DO NOTHING
                    """),
                    rows
                )
            
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            print(f"Error bulk inserting holdings: {e}")
            return False
        finally:
            session.close()
    
    async def get_holdings_by_filing_id(self, filing_id: str) -> List[Dict[str, Any]]:
        """Get all holdings for a specific filing"""
        if not self.engine:
            return []
        
        session = self._get_session()
        try:
            result = session.execute(
                text("""
                    SELECT * FROM sec_holdings_13f
                    WHERE filing_id = :filing_id
                    ORDER BY value DESC
                """),
                {"filing_id": filing_id}
            )
            return [dict(row._mapping) for row in result]
        except Exception as e:
            print(f"Error querying holdings: {e}")
            return []
        finally:
            session.close()
    
    async def get_institutional_activity_for_stock(
        self,
        cusip: str,
        start_date: date,
        end_date: date
    ) -> List[Dict[str, Any]]:
        """Get all institutional activity for a specific stock (by CUSIP) within a date range"""
        if not self.engine:
            return []
        
        session = self._get_session()
        try:
            result = session.execute(
                text("""
                    SELECT 
                        h.*,
                        f.cik,
                        f.filing_date,
                        f.period_end_date,
                        i.name as institution_name
                    FROM sec_holdings_13f h
                    JOIN sec_filings_13f f ON h.filing_id = f.filing_id
                    JOIN sec_institutions i ON f.cik = i.cik
                    WHERE h.cusip = :cusip
                        AND f.filing_date BETWEEN :start_date AND :end_date
                    ORDER BY f.filing_date ASC
                """),
                {"cusip": cusip, "start_date": start_date, "end_date": end_date}
            )
            return [dict(row._mapping) for row in result]
        except Exception as e:
            print(f"Error querying institutional activity: {e}")
            return []
        finally:
            session.close()
    
    # ==================== Form 4 Insider Trading Operations ====================
    
    async def insert_form4_transaction(self, transaction_data: Dict[str, Any]) -> bool:
        """Insert Form 4 insider transaction"""
        if not self.engine:
            return False
        
        session = self._get_session()
        try:
            session.execute(
                text("""
                    INSERT INTO sec_form4_transactions 
                    (transaction_id, accession_number, filing_date, issuer_cik, issuer_name, ticker,
                     reporting_owner_name, reporting_owner_cik, relationship, is_director, is_officer,
                     officer_title, is_ten_percent_owner, transaction_code, transaction_date,
                     deemed_execution_date, shares, price_per_share, acquired_disposed_code,
                     ownership_nature, created_at)
                    VALUES (:transaction_id, :accession_number, :filing_date, :issuer_cik, :issuer_name, :ticker,
                            :reporting_owner_name, :reporting_owner_cik, :relationship, :is_director, :is_officer,
                            :officer_title, :is_ten_percent_owner, :transaction_code, :transaction_date,
                            :deemed_execution_date, :shares, :price_per_share, :acquired_disposed_code,
                            :ownership_nature, :created_at)
                    ON CONFLICT (transaction_id) DO NOTHING
                """),
                {
                    "transaction_id": transaction_data.get("transaction_id"),
                    "accession_number": transaction_data.get("accession_number"),
                    "filing_date": transaction_data.get("filing_date"),
                    "issuer_cik": transaction_data.get("issuer_cik"),
                    "issuer_name": transaction_data.get("issuer_name"),
                    "ticker": transaction_data.get("ticker"),
                    "reporting_owner_name": transaction_data.get("reporting_owner_name"),
                    "reporting_owner_cik": transaction_data.get("reporting_owner_cik"),
                    "relationship": transaction_data.get("relationship"),
                    "is_director": transaction_data.get("is_director", False),
                    "is_officer": transaction_data.get("is_officer", False),
                    "officer_title": transaction_data.get("officer_title"),
                    "is_ten_percent_owner": transaction_data.get("is_ten_percent_owner", False),
                    "transaction_code": transaction_data.get("transaction_code"),
                    "transaction_date": transaction_data.get("transaction_date"),
                    "deemed_execution_date": transaction_data.get("deemed_execution_date"),
                    "shares": transaction_data.get("shares", 0),
                    "price_per_share": transaction_data.get("price_per_share", 0),
                    "acquired_disposed_code": transaction_data.get("acquired_disposed_code"),
                    "ownership_nature": transaction_data.get("ownership_nature", "direct"),
                    "created_at": datetime.utcnow()
                }
            )
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            print(f"Error inserting Form 4 transaction: {e}")
            return False
        finally:
            session.close()
    
    async def get_insider_activity_for_stock(
        self,
        ticker: str,
        start_date: date,
        end_date: date,
        transaction_codes: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Get insider trading activity for a stock"""
        if not self.engine:
            return []
        
        where_clauses = [
            "ticker = :ticker",
            "transaction_date BETWEEN :start_date AND :end_date"
        ]
        params = {"ticker": ticker, "start_date": start_date, "end_date": end_date}
        
        if transaction_codes:
            placeholders = ",".join([f":code{i}" for i in range(len(transaction_codes))])
            where_clauses.append(f"transaction_code IN ({placeholders})")
            for i, code in enumerate(transaction_codes):
                params[f"code{i}"] = code
        
        where_clause = " AND ".join(where_clauses)
        
        session = self._get_session()
        try:
            query = text(f"""
                SELECT * FROM sec_form4_transactions
                WHERE {where_clause}
                ORDER BY transaction_date DESC
            """)
            
            result = session.execute(query, params)
            return [dict(row._mapping) for row in result]
        except Exception as e:
            print(f"Error querying insider activity: {e}")
            return []
        finally:
            session.close()
    
    # ==================== CUSIP Mapping Operations ====================
    
    async def insert_cusip_ticker_mapping(
        self,
        cusip: str,
        ticker: str,
        effective_date: date,
        end_date: Optional[date] = None
    ) -> bool:
        """Insert CUSIP to ticker mapping with effective dates"""
        if not self.engine:
            return False
        
        session = self._get_session()
        try:
            session.execute(
                text("""
                    INSERT INTO sec_cusip_ticker_mapping 
                    (cusip, ticker, effective_date, end_date, created_at)
                    VALUES (:cusip, :ticker, :effective_date, :end_date, :created_at)
                """),
                {
                    "cusip": cusip,
                    "ticker": ticker,
                    "effective_date": effective_date,
                    "end_date": end_date,
                    "created_at": datetime.utcnow()
                }
            )
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            print(f"Error inserting CUSIP mapping: {e}")
            return False
        finally:
            session.close()
    
    async def get_ticker_for_cusip(self, cusip: str, as_of_date: date) -> Optional[str]:
        """Get ticker for a CUSIP as of a specific date (PIT accuracy)"""
        if not self.engine:
            return None
        
        session = self._get_session()
        try:
            result = session.execute(
                text("""
                    SELECT ticker
                    FROM sec_cusip_ticker_mapping
                    WHERE cusip = :cusip
                        AND effective_date <= :as_of_date
                        AND (end_date IS NULL OR end_date > :as_of_date)
                    ORDER BY effective_date DESC
                    LIMIT 1
                """),
                {"cusip": cusip, "as_of_date": as_of_date}
            )
            row = result.fetchone()
            if row:
                return row[0]
            return None
        except Exception as e:
            print(f"Error querying ticker for CUSIP: {e}")
            return None
        finally:
            session.close()
    
    # ==================== Index Constituents Operations ====================
    
    async def insert_index_constituent(
        self,
        index_name: str,
        ticker: str,
        effective_date: date,
        end_date: Optional[date] = None
    ) -> bool:
        """Insert index constituent membership with effective dates"""
        if not self.engine:
            return False
        
        session = self._get_session()
        try:
            session.execute(
                text("""
                    INSERT INTO market_index_constituents 
                    (index_name, ticker, effective_date, end_date, created_at)
                    VALUES (:index_name, :ticker, :effective_date, :end_date, :created_at)
                """),
                {
                    "index_name": index_name,
                    "ticker": ticker,
                    "effective_date": effective_date,
                    "end_date": end_date,
                    "created_at": datetime.utcnow()
                }
            )
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            print(f"Error inserting index constituent: {e}")
            return False
        finally:
            session.close()
    
    async def get_index_constituents(
        self,
        index_name: str,
        as_of_date: date
    ) -> List[str]:
        """Get list of tickers in an index as of a specific date (PIT accuracy)"""
        if not self.engine:
            return []
        
        session = self._get_session()
        try:
            result = session.execute(
                text("""
                    SELECT DISTINCT ticker
                    FROM market_index_constituents
                    WHERE index_name = :index_name
                        AND effective_date <= :as_of_date
                        AND (end_date IS NULL OR end_date > :as_of_date)
                    ORDER BY ticker
                """),
                {"index_name": index_name, "as_of_date": as_of_date}
            )
            return [row[0] for row in result]
        except Exception as e:
            print(f"Error querying index constituents: {e}")
            return []
        finally:
            session.close()
    
    # ==================== Utility Methods ====================
    
    def is_available(self) -> bool:
        """Check if PostgreSQL client is available"""
        return self.engine is not None
    
    async def execute_query(self, query: str, params: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """Execute a custom SQL query"""
        if not self.engine:
            return []
        
        session = self._get_session()
        try:
            result = session.execute(text(query), params or {})
            return [dict(row._mapping) for row in result]
        except Exception as e:
            print(f"Error executing query: {e}")
            return []
        finally:
            session.close()


# Singleton instance
_postgres_service = None


def get_postgres_service() -> PostgresService:
    """Get or create PostgreSQL service instance"""
    global _postgres_service
    if _postgres_service is None:
        _postgres_service = PostgresService()
    return _postgres_service

