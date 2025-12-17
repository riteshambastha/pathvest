"""
Google BigQuery Service for SEC Data Warehouse
"""

from typing import List, Dict, Optional, Any
from datetime import datetime, date
from google.cloud import bigquery
from google.oauth2 import service_account
import os
import json

from app.core.config import settings


class BigQueryService:
    """Service for Google BigQuery operations on SEC data warehouse"""
    
    def __init__(self):
        """Initialize BigQuery client"""
        self.project_id = getattr(settings, 'GCP_PROJECT_ID', None)
        self.dataset_id = getattr(settings, 'BIGQUERY_DATASET_ID', 'pathvest_sec_data')
        
        # Initialize client based on available credentials
        credentials_path = getattr(settings, 'GCP_CREDENTIALS_PATH', None)
        
        if credentials_path and os.path.exists(credentials_path):
            credentials = service_account.Credentials.from_service_account_file(
                credentials_path,
                scopes=["https://www.googleapis.com/auth/bigquery"]
            )
            self.client = bigquery.Client(
                credentials=credentials,
                project=self.project_id
            )
        elif self.project_id:
            # Use default credentials (for GCP environment)
            self.client = bigquery.Client(project=self.project_id)
        else:
            # Mock mode for development without GCP setup
            self.client = None
            print("WARNING: BigQuery client not initialized. Running in mock mode.")
    
    def _get_table_ref(self, table_name: str) -> str:
        """Get fully qualified table reference"""
        return f"{self.project_id}.{self.dataset_id}.{table_name}"
    
    # ==================== Institution Operations ====================
    
    async def insert_institution(self, cik: str, name: str, metadata: Dict[str, Any] = None) -> bool:
        """Insert or update institution record"""
        if not self.client:
            return False
        
        table_ref = self._get_table_ref("sec_institutions")
        
        row = {
            "cik": cik,
            "name": name,
            "metadata": json.dumps(metadata) if metadata else None,
            "last_updated": datetime.utcnow().isoformat()
        }
        
        try:
            errors = self.client.insert_rows_json(table_ref, [row])
            return len(errors) == 0
        except Exception as e:
            print(f"Error inserting institution: {e}")
            return False
    
    async def get_institution_by_cik(self, cik: str) -> Optional[Dict[str, Any]]:
        """Get institution by CIK"""
        if not self.client:
            return None
        
        query = f"""
            SELECT *
            FROM `{self._get_table_ref('sec_institutions')}`
            WHERE cik = @cik
            LIMIT 1
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("cik", "STRING", cik)
            ]
        )
        
        try:
            query_job = self.client.query(query, job_config=job_config)
            results = list(query_job.result())
            
            if results:
                return dict(results[0])
            return None
        except Exception as e:
            print(f"Error querying institution: {e}")
            return None
    
    async def get_qualified_institutions(
        self,
        min_aum: float = 1_000_000_000,
        min_track_record_quarters: int = 8,
        as_of_date: Optional[date] = None
    ) -> List[Dict[str, Any]]:
        """
        Get institutions meeting qualification criteria
        
        Args:
            min_aum: Minimum AUM in dollars
            min_track_record_quarters: Minimum consecutive quarters of filings
            as_of_date: Point-in-time date for filtering
        """
        if not self.client:
            return []
        
        as_of_filter = ""
        if as_of_date:
            as_of_filter = f"AND filing_date <= '{as_of_date.isoformat()}'"
        
        query = f"""
            WITH institution_stats AS (
                SELECT 
                    i.cik,
                    i.name,
                    COUNT(DISTINCT f.period_end_date) as quarters_filed,
                    MAX(f.total_value) as latest_aum
                FROM `{self._get_table_ref('sec_institutions')}` i
                JOIN `{self._get_table_ref('sec_filings_13f')}` f
                    ON i.cik = f.cik
                WHERE 1=1
                    {as_of_filter}
                GROUP BY i.cik, i.name
            )
            SELECT *
            FROM institution_stats
            WHERE latest_aum >= @min_aum
                AND quarters_filed >= @min_track_record_quarters
            ORDER BY latest_aum DESC
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("min_aum", "FLOAT64", min_aum),
                bigquery.ScalarQueryParameter("min_track_record_quarters", "INT64", min_track_record_quarters)
            ]
        )
        
        try:
            query_job = self.client.query(query, job_config=job_config)
            return [dict(row) for row in query_job.result()]
        except Exception as e:
            print(f"Error querying qualified institutions: {e}")
            return []
    
    # ==================== 13F Filing Operations ====================
    
    async def insert_filing_13f(self, filing_data: Dict[str, Any]) -> bool:
        """Insert 13F filing record"""
        if not self.client:
            return False
        
        table_ref = self._get_table_ref("sec_filings_13f")
        
        row = {
            "filing_id": filing_data.get("filing_id"),
            "cik": filing_data.get("cik"),
            "filing_date": filing_data.get("filing_date"),
            "period_end_date": filing_data.get("period_end_date"),
            "accession_number": filing_data.get("accession_number"),
            "form_type": filing_data.get("form_type", "13F-HR"),
            "total_value": filing_data.get("total_value", 0),
            "holdings_count": filing_data.get("holdings_count", 0),
            "created_at": datetime.utcnow().isoformat()
        }
        
        try:
            errors = self.client.insert_rows_json(table_ref, [row])
            return len(errors) == 0
        except Exception as e:
            print(f"Error inserting 13F filing: {e}")
            return False
    
    async def get_filings_by_cik(
        self,
        cik: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[Dict[str, Any]]:
        """Get all filings for a given CIK within date range"""
        if not self.client:
            return []
        
        date_filter = ""
        params = [bigquery.ScalarQueryParameter("cik", "STRING", cik)]
        
        if start_date:
            date_filter += " AND filing_date >= @start_date"
            params.append(bigquery.ScalarQueryParameter("start_date", "DATE", start_date))
        
        if end_date:
            date_filter += " AND filing_date <= @end_date"
            params.append(bigquery.ScalarQueryParameter("end_date", "DATE", end_date))
        
        query = f"""
            SELECT *
            FROM `{self._get_table_ref('sec_filings_13f')}`
            WHERE cik = @cik
                {date_filter}
            ORDER BY filing_date DESC
        """
        
        job_config = bigquery.QueryJobConfig(query_parameters=params)
        
        try:
            query_job = self.client.query(query, job_config=job_config)
            return [dict(row) for row in query_job.result()]
        except Exception as e:
            print(f"Error querying filings: {e}")
            return []
    
    # ==================== Holdings Operations ====================
    
    async def insert_holding_13f(self, holding_data: Dict[str, Any]) -> bool:
        """Insert 13F holding record"""
        if not self.client:
            return False
        
        table_ref = self._get_table_ref("sec_holdings_13f")
        
        row = {
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
            "created_at": datetime.utcnow().isoformat()
        }
        
        try:
            errors = self.client.insert_rows_json(table_ref, [row])
            return len(errors) == 0
        except Exception as e:
            print(f"Error inserting holding: {e}")
            return False
    
    async def bulk_insert_holdings(self, holdings: List[Dict[str, Any]]) -> bool:
        """Bulk insert holdings for better performance"""
        if not self.client or not holdings:
            return False
        
        table_ref = self._get_table_ref("sec_holdings_13f")
        
        rows = []
        for holding in holdings:
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
                "created_at": datetime.utcnow().isoformat()
            })
        
        try:
            # Insert in batches of 500
            batch_size = 500
            for i in range(0, len(rows), batch_size):
                batch = rows[i:i + batch_size]
                errors = self.client.insert_rows_json(table_ref, batch)
                if errors:
                    print(f"Errors in batch {i // batch_size}: {errors}")
                    return False
            return True
        except Exception as e:
            print(f"Error bulk inserting holdings: {e}")
            return False
    
    async def get_holdings_by_filing_id(self, filing_id: str) -> List[Dict[str, Any]]:
        """Get all holdings for a specific filing"""
        if not self.client:
            return []
        
        query = f"""
            SELECT *
            FROM `{self._get_table_ref('sec_holdings_13f')}`
            WHERE filing_id = @filing_id
            ORDER BY value DESC
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("filing_id", "STRING", filing_id)
            ]
        )
        
        try:
            query_job = self.client.query(query, job_config=job_config)
            return [dict(row) for row in query_job.result()]
        except Exception as e:
            print(f"Error querying holdings: {e}")
            return []
    
    async def get_institutional_activity_for_stock(
        self,
        cusip: str,
        start_date: date,
        end_date: date
    ) -> List[Dict[str, Any]]:
        """
        Get all institutional activity for a specific stock (by CUSIP)
        within a date range - critical for herding and doubling down signals
        """
        if not self.client:
            return []
        
        query = f"""
            SELECT 
                h.*,
                f.cik,
                f.filing_date,
                f.period_end_date,
                i.name as institution_name
            FROM `{self._get_table_ref('sec_holdings_13f')}` h
            JOIN `{self._get_table_ref('sec_filings_13f')}` f
                ON h.filing_id = f.filing_id
            JOIN `{self._get_table_ref('sec_institutions')}` i
                ON f.cik = i.cik
            WHERE h.cusip = @cusip
                AND f.filing_date BETWEEN @start_date AND @end_date
            ORDER BY f.filing_date ASC
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("cusip", "STRING", cusip),
                bigquery.ScalarQueryParameter("start_date", "DATE", start_date),
                bigquery.ScalarQueryParameter("end_date", "DATE", end_date)
            ]
        )
        
        try:
            query_job = self.client.query(query, job_config=job_config)
            return [dict(row) for row in query_job.result()]
        except Exception as e:
            print(f"Error querying institutional activity: {e}")
            return []
    
    # ==================== Form 4 Insider Trading Operations ====================
    
    async def insert_form4_transaction(self, transaction_data: Dict[str, Any]) -> bool:
        """Insert Form 4 insider transaction"""
        if not self.client:
            return False
        
        table_ref = self._get_table_ref("sec_form4_transactions")
        
        row = {
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
            "created_at": datetime.utcnow().isoformat()
        }
        
        try:
            errors = self.client.insert_rows_json(table_ref, [row])
            return len(errors) == 0
        except Exception as e:
            print(f"Error inserting Form 4 transaction: {e}")
            return False
    
    async def get_insider_activity_for_stock(
        self,
        ticker: str,
        start_date: date,
        end_date: date,
        transaction_codes: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get insider trading activity for a stock
        
        Args:
            ticker: Stock ticker symbol
            start_date: Start date for activity
            end_date: End date for activity
            transaction_codes: Filter by transaction codes (e.g., ['P', 'S'])
                              P = Purchase, S = Sale
        """
        if not self.client:
            return []
        
        code_filter = ""
        params = [
            bigquery.ScalarQueryParameter("ticker", "STRING", ticker),
            bigquery.ScalarQueryParameter("start_date", "DATE", start_date),
            bigquery.ScalarQueryParameter("end_date", "DATE", end_date)
        ]
        
        if transaction_codes:
            code_filter = "AND transaction_code IN UNNEST(@transaction_codes)"
            params.append(bigquery.ArrayQueryParameter("transaction_codes", "STRING", transaction_codes))
        
        query = f"""
            SELECT *
            FROM `{self._get_table_ref('sec_form4_transactions')}`
            WHERE ticker = @ticker
                AND transaction_date BETWEEN @start_date AND @end_date
                {code_filter}
            ORDER BY transaction_date DESC
        """
        
        job_config = bigquery.QueryJobConfig(query_parameters=params)
        
        try:
            query_job = self.client.query(query, job_config=job_config)
            return [dict(row) for row in query_job.result()]
        except Exception as e:
            print(f"Error querying insider activity: {e}")
            return []
    
    # ==================== CUSIP Mapping Operations ====================
    
    async def insert_cusip_ticker_mapping(
        self,
        cusip: str,
        ticker: str,
        effective_date: date,
        end_date: Optional[date] = None
    ) -> bool:
        """Insert CUSIP to ticker mapping with effective dates"""
        if not self.client:
            return False
        
        table_ref = self._get_table_ref("sec_cusip_ticker_mapping")
        
        row = {
            "cusip": cusip,
            "ticker": ticker,
            "effective_date": effective_date.isoformat(),
            "end_date": end_date.isoformat() if end_date else None,
            "created_at": datetime.utcnow().isoformat()
        }
        
        try:
            errors = self.client.insert_rows_json(table_ref, [row])
            return len(errors) == 0
        except Exception as e:
            print(f"Error inserting CUSIP mapping: {e}")
            return False
    
    async def get_ticker_for_cusip(self, cusip: str, as_of_date: date) -> Optional[str]:
        """Get ticker for a CUSIP as of a specific date (PIT accuracy)"""
        if not self.client:
            return None
        
        query = f"""
            SELECT ticker
            FROM `{self._get_table_ref('sec_cusip_ticker_mapping')}`
            WHERE cusip = @cusip
                AND effective_date <= @as_of_date
                AND (end_date IS NULL OR end_date > @as_of_date)
            ORDER BY effective_date DESC
            LIMIT 1
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("cusip", "STRING", cusip),
                bigquery.ScalarQueryParameter("as_of_date", "DATE", as_of_date)
            ]
        )
        
        try:
            query_job = self.client.query(query, job_config=job_config)
            results = list(query_job.result())
            
            if results:
                return results[0].ticker
            return None
        except Exception as e:
            print(f"Error querying ticker for CUSIP: {e}")
            return None
    
    # ==================== Index Constituents Operations ====================
    
    async def insert_index_constituent(
        self,
        index_name: str,
        ticker: str,
        effective_date: date,
        end_date: Optional[date] = None
    ) -> bool:
        """Insert index constituent membership with effective dates"""
        if not self.client:
            return False
        
        table_ref = self._get_table_ref("market_index_constituents")
        
        row = {
            "index_name": index_name,
            "ticker": ticker,
            "effective_date": effective_date.isoformat(),
            "end_date": end_date.isoformat() if end_date else None,
            "created_at": datetime.utcnow().isoformat()
        }
        
        try:
            errors = self.client.insert_rows_json(table_ref, [row])
            return len(errors) == 0
        except Exception as e:
            print(f"Error inserting index constituent: {e}")
            return False
    
    async def get_index_constituents(
        self,
        index_name: str,
        as_of_date: date
    ) -> List[str]:
        """Get list of tickers in an index as of a specific date (PIT accuracy)"""
        if not self.client:
            return []
        
        query = f"""
            SELECT DISTINCT ticker
            FROM `{self._get_table_ref('market_index_constituents')}`
            WHERE index_name = @index_name
                AND effective_date <= @as_of_date
                AND (end_date IS NULL OR end_date > @as_of_date)
            ORDER BY ticker
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("index_name", "STRING", index_name),
                bigquery.ScalarQueryParameter("as_of_date", "DATE", as_of_date)
            ]
        )
        
        try:
            query_job = self.client.query(query, job_config=job_config)
            return [row.ticker for row in query_job.result()]
        except Exception as e:
            print(f"Error querying index constituents: {e}")
            return []
    
    # ==================== Utility Methods ====================
    
    def is_available(self) -> bool:
        """Check if BigQuery client is available"""
        return self.client is not None
    
    async def execute_query(self, query: str, params: Optional[List] = None) -> List[Dict[str, Any]]:
        """Execute a custom SQL query"""
        if not self.client:
            return []
        
        job_config = None
        if params:
            job_config = bigquery.QueryJobConfig(query_parameters=params)
        
        try:
            query_job = self.client.query(query, job_config=job_config)
            return [dict(row) for row in query_job.result()]
        except Exception as e:
            print(f"Error executing query: {e}")
            return []


# Singleton instance
_bigquery_service = None


def get_bigquery_service() -> BigQueryService:
    """Get or create BigQuery service instance"""
    global _bigquery_service
    if _bigquery_service is None:
        _bigquery_service = BigQueryService()
    return _bigquery_service

