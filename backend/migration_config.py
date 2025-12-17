"""
Migration Configuration for BigQuery -> PostgreSQL
"""

# PostgreSQL connection (local)
POSTGRES_URL = "postgresql://riteshambastha@localhost:5432/pathvest"

# BigQuery configuration
BIGQUERY_PROJECT = "test-for-android-notifn"
BIGQUERY_DATASET = "sec_filings"

# Migration settings
BATCH_SIZE = 1000
BACKUP_DIR = "migration_backups"

# Tables to migrate
TABLES_TO_MIGRATE = [
    "institutional_holdings",
    "sec_filings_13f",
    "sec_holdings_13f",
    "sec_institutions",
    "sec_form4_transactions",
    "sec_cusip_ticker_mapping",
    "market_index_constituents",
    "stock_sector_classification",
    "stock_market_cap_history",
    "stock_liquidity_metrics"
]

print("✅ Migration config loaded")
print(f"   PostgreSQL: {POSTGRES_URL}")
print(f"   BigQuery: {BIGQUERY_PROJECT}.{BIGQUERY_DATASET}")
print(f"   Tables: {len(TABLES_TO_MIGRATE)}")

