-- BigQuery Schema for PathVest SEC Data Warehouse
-- Dataset: pathvest_sec_data

-- ==================== Institutions Table ====================
CREATE TABLE IF NOT EXISTS `pathvest_sec_data.sec_institutions` (
    cik STRING NOT NULL,
    name STRING NOT NULL,
    metadata JSON,  -- Additional metadata (AUM, filing frequency, etc.)
    last_updated TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY DATE(created_at)
CLUSTER BY cik
OPTIONS(
    description="SEC institutional investors (filers of 13F forms)",
    labels=[("source", "sec_edgar"), ("data_type", "institutions")]
);

-- ==================== 13F Filings Table ====================
CREATE TABLE IF NOT EXISTS `pathvest_sec_data.sec_filings_13f` (
    filing_id STRING NOT NULL,  -- Unique identifier (accession_number or generated ID)
    cik STRING NOT NULL,  -- Filing institution CIK
    filing_date DATE NOT NULL,  -- Date filing was made public (PIT key date)
    period_end_date DATE NOT NULL,  -- Quarter end date
    accession_number STRING NOT NULL,  -- SEC accession number
    form_type STRING DEFAULT '13F-HR',  -- Form type (13F-HR, 13F-HR/A for amendments)
    total_value FLOAT64,  -- Total portfolio value in thousands
    holdings_count INT64,  -- Number of holdings in filing
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
    -- Metadata
    is_amendment BOOL DEFAULT FALSE,
    amendment_number INT64,
    source_url STRING
)
PARTITION BY filing_date
CLUSTER BY cik, period_end_date
OPTIONS(
    description="13F filing metadata - quarterly institutional holdings reports",
    labels=[("source", "sec_edgar"), ("data_type", "filings_13f")]
);

-- ==================== 13F Holdings Table ====================
CREATE TABLE IF NOT EXISTS `pathvest_sec_data.sec_holdings_13f` (
    holding_id STRING NOT NULL,  -- Unique identifier
    filing_id STRING NOT NULL,  -- Foreign key to sec_filings_13f
    
    -- Security identification
    cusip STRING NOT NULL,
    ticker STRING,  -- Mapped ticker (can be NULL if mapping fails)
    name_of_issuer STRING NOT NULL,
    
    -- Position details
    value FLOAT64 NOT NULL,  -- Position value in thousands (x$1000)
    shares_or_prn_amt INT64,  -- Share count or principal amount
    shares_or_prn_amt_type STRING,  -- 'SH' for shares, 'PRN' for principal amount
    
    -- Investment details
    investment_discretion STRING,  -- SOLE, SHARED, OTHER
    voting_authority_sole INT64 DEFAULT 0,
    voting_authority_shared INT64 DEFAULT 0,
    voting_authority_none INT64 DEFAULT 0,
    
    -- Options details (if applicable)
    put_call STRING,  -- PUT or CALL
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY DATE(created_at)
CLUSTER BY cusip, filing_id
OPTIONS(
    description="Individual holdings from 13F filings - stock positions held by institutions",
    labels=[("source", "sec_edgar"), ("data_type", "holdings_13f")]
);

-- ==================== Form 4 Insider Transactions Table ====================
CREATE TABLE IF NOT EXISTS `pathvest_sec_data.sec_form4_transactions` (
    transaction_id STRING NOT NULL,  -- Unique identifier
    accession_number STRING NOT NULL,  -- SEC accession number
    filing_date DATE NOT NULL,  -- Date Form 4 was filed (PIT key date)
    
    -- Issuer (company) information
    issuer_cik STRING NOT NULL,
    issuer_name STRING NOT NULL,
    ticker STRING,  -- Stock ticker
    
    -- Reporting owner (insider) information
    reporting_owner_name STRING NOT NULL,
    reporting_owner_cik STRING,
    relationship STRING,  -- JSON or comma-separated: director, officer, 10% owner, other
    is_director BOOL DEFAULT FALSE,
    is_officer BOOL DEFAULT FALSE,
    officer_title STRING,  -- CEO, CFO, COO, President, etc.
    is_ten_percent_owner BOOL DEFAULT FALSE,
    is_other BOOL DEFAULT FALSE,
    
    -- Transaction details
    transaction_code STRING NOT NULL,  -- P=Purchase, S=Sale, A=Award, etc.
    transaction_date DATE NOT NULL,  -- Actual transaction date
    deemed_execution_date DATE,  -- Optional deemed execution date
    shares FLOAT64 NOT NULL,  -- Number of shares transacted
    price_per_share FLOAT64,  -- Price per share
    acquired_disposed_code STRING,  -- 'A' for acquired, 'D' for disposed
    
    -- Ownership information
    ownership_nature STRING DEFAULT 'direct',  -- 'direct' or 'indirect'
    
    -- 10b5-1 plan flag (if available in filing)
    is_10b51_plan BOOL DEFAULT FALSE,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
    source_url STRING
)
PARTITION BY transaction_date
CLUSTER BY ticker, transaction_code, filing_date
OPTIONS(
    description="Form 4 insider trading transactions - buys and sells by company insiders",
    labels=[("source", "sec_edgar"), ("data_type", "form4_transactions")]
);

-- ==================== CUSIP to Ticker Mapping Table ====================
CREATE TABLE IF NOT EXISTS `pathvest_sec_data.sec_cusip_ticker_mapping` (
    cusip STRING NOT NULL,
    ticker STRING NOT NULL,
    company_name STRING,
    effective_date DATE NOT NULL,  -- Date this mapping became effective
    end_date DATE,  -- Date this mapping ended (NULL if still active)
    mapping_source STRING,  -- 'openfigi', 'sec_api', 'manual', etc.
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY effective_date
CLUSTER BY cusip, ticker
OPTIONS(
    description="Historical CUSIP to ticker mappings with PIT accuracy for handling ticker changes",
    labels=[("source", "multiple"), ("data_type", "reference_data")]
);

-- ==================== Market Index Constituents Table ====================
CREATE TABLE IF NOT EXISTS `pathvest_sec_data.market_index_constituents` (
    index_name STRING NOT NULL,  -- 'SP500', 'SP400', 'SP600', 'SP1500', etc.
    ticker STRING NOT NULL,
    company_name STRING,
    sector STRING,
    industry STRING,
    effective_date DATE NOT NULL,  -- Date stock was added to index
    end_date DATE,  -- Date stock was removed from index (NULL if still in index)
    market_cap FLOAT64,  -- Market cap at time of addition
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY effective_date
CLUSTER BY index_name, ticker
OPTIONS(
    description="Historical index membership for universe filtering with PIT accuracy",
    labels=[("source", "market_data"), ("data_type", "reference_data")]
);

-- ==================== Views for Common Queries ====================

-- View: Latest 13F filings by institution
CREATE OR REPLACE VIEW `pathvest_sec_data.view_latest_filings_by_institution` AS
SELECT 
    i.cik,
    i.name as institution_name,
    f.filing_id,
    f.filing_date,
    f.period_end_date,
    f.total_value as aum_thousands,
    f.holdings_count,
    ROW_NUMBER() OVER (PARTITION BY i.cik ORDER BY f.filing_date DESC) as recency_rank
FROM `pathvest_sec_data.sec_institutions` i
JOIN `pathvest_sec_data.sec_filings_13f` f
    ON i.cik = f.cik;

-- View: Holdings with institution and filing context
CREATE OR REPLACE VIEW `pathvest_sec_data.view_holdings_enriched` AS
SELECT 
    h.*,
    f.cik,
    f.filing_date,
    f.period_end_date,
    i.name as institution_name,
    f.total_value as institution_aum_thousands
FROM `pathvest_sec_data.sec_holdings_13f` h
JOIN `pathvest_sec_data.sec_filings_13f` f
    ON h.filing_id = f.filing_id
JOIN `pathvest_sec_data.sec_institutions` i
    ON f.cik = i.cik;

-- View: Insider purchases (Form 4 - only buys)
CREATE OR REPLACE VIEW `pathvest_sec_data.view_insider_purchases` AS
SELECT 
    *,
    shares * price_per_share as transaction_value
FROM `pathvest_sec_data.sec_form4_transactions`
WHERE transaction_code IN ('P', 'A', 'M')  -- P=Purchase, A=Award+Purchase, M=Exercise
    AND acquired_disposed_code = 'A'
    AND is_10b51_plan = FALSE;

-- View: Insider sales (Form 4 - only sells)
CREATE OR REPLACE VIEW `pathvest_sec_data.view_insider_sales` AS
SELECT 
    *,
    shares * price_per_share as transaction_value
FROM `pathvest_sec_data.sec_form4_transactions`
WHERE transaction_code IN ('S', 'D', 'F')  -- S=Sale, D=Disposition, F=Payment of tax
    AND acquired_disposed_code = 'D';

-- View: Active CUSIP mappings (current)
CREATE OR REPLACE VIEW `pathvest_sec_data.view_active_cusip_mappings` AS
SELECT DISTINCT
    cusip,
    ticker,
    company_name,
    effective_date,
    mapping_source
FROM `pathvest_sec_data.sec_cusip_ticker_mapping`
WHERE end_date IS NULL
ORDER BY cusip;

-- View: Current S&P 1500 constituents
CREATE OR REPLACE VIEW `pathvest_sec_data.view_sp1500_current` AS
SELECT DISTINCT
    ticker,
    company_name,
    sector,
    industry,
    effective_date
FROM `pathvest_sec_data.market_index_constituents`
WHERE index_name = 'SP1500'
    AND end_date IS NULL
ORDER BY ticker;

-- ==================== Indexes for Performance ====================

-- Note: BigQuery automatically creates indexes based on CLUSTER BY clauses
-- Additional optimization can be done through:
-- 1. Partitioning by date columns (already done above)
-- 2. Clustering by frequently queried columns (already done above)
-- 3. Materialized views for complex aggregations (can be added later)

-- ==================== Data Quality Checks ====================

-- Check for duplicate filings
CREATE OR REPLACE VIEW `pathvest_sec_data.quality_check_duplicate_filings` AS
SELECT 
    accession_number,
    COUNT(*) as duplicate_count
FROM `pathvest_sec_data.sec_filings_13f`
GROUP BY accession_number
HAVING COUNT(*) > 1;

-- Check for holdings with invalid CUSIPs (not 9 characters)
CREATE OR REPLACE VIEW `pathvest_sec_data.quality_check_invalid_cusips` AS
SELECT 
    holding_id,
    cusip,
    LENGTH(cusip) as cusip_length
FROM `pathvest_sec_data.sec_holdings_13f`
WHERE LENGTH(cusip) != 9
LIMIT 1000;

-- Check for holdings without ticker mappings
CREATE OR REPLACE VIEW `pathvest_sec_data.quality_check_unmapped_tickers` AS
SELECT 
    h.cusip,
    h.name_of_issuer,
    COUNT(DISTINCT h.holding_id) as holdings_count,
    MAX(f.filing_date) as latest_filing_date
FROM `pathvest_sec_data.sec_holdings_13f` h
JOIN `pathvest_sec_data.sec_filings_13f` f
    ON h.filing_id = f.filing_id
WHERE h.ticker IS NULL
GROUP BY h.cusip, h.name_of_issuer
ORDER BY holdings_count DESC
LIMIT 1000;

-- Check for Form 4 transactions with invalid transaction codes
CREATE OR REPLACE VIEW `pathvest_sec_data.quality_check_invalid_transaction_codes` AS
SELECT 
    transaction_code,
    COUNT(*) as occurrences
FROM `pathvest_sec_data.sec_form4_transactions`
WHERE transaction_code NOT IN ('P', 'S', 'A', 'D', 'F', 'G', 'M', 'C', 'J', 'W', 'X', 'I', 'L', 'U', 'Z')
GROUP BY transaction_code;

-- ==================== Analytics-Ready Tables (Materialized Views) ====================

-- Quarterly institutional ownership changes by stock
CREATE MATERIALIZED VIEW IF NOT EXISTS `pathvest_sec_data.mat_quarterly_institutional_changes`
PARTITION BY filing_date
CLUSTER BY ticker
AS
SELECT 
    h.ticker,
    h.cusip,
    f.filing_date,
    f.period_end_date,
    COUNT(DISTINCT f.cik) as num_institutions,
    SUM(h.shares_or_prn_amt) as total_institutional_shares,
    SUM(h.value) as total_institutional_value_thousands,
    AVG(h.value) as avg_position_value_thousands
FROM `pathvest_sec_data.sec_holdings_13f` h
JOIN `pathvest_sec_data.sec_filings_13f` f
    ON h.filing_id = f.filing_id
WHERE h.ticker IS NOT NULL
    AND h.shares_or_prn_amt_type = 'SH'
GROUP BY h.ticker, h.cusip, f.filing_date, f.period_end_date;

-- Insider buying/selling aggregates by stock
CREATE MATERIALIZED VIEW IF NOT EXISTS `pathvest_sec_data.mat_insider_activity_summary`
PARTITION BY transaction_date
CLUSTER BY ticker
AS
SELECT 
    ticker,
    DATE_TRUNC(transaction_date, MONTH) as month,
    transaction_code,
    COUNT(*) as transaction_count,
    COUNT(DISTINCT reporting_owner_cik) as unique_insiders,
    SUM(shares) as total_shares,
    SUM(shares * price_per_share) as total_value,
    AVG(price_per_share) as avg_price
FROM `pathvest_sec_data.sec_form4_transactions`
WHERE ticker IS NOT NULL
    AND price_per_share > 0
GROUP BY ticker, month, transaction_code;

