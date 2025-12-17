-- Create BigQuery Tables for SEC Data
-- Run this in BigQuery console or using bq command-line tool

-- 1. Institutional Holdings Table (13F Data)
CREATE TABLE IF NOT EXISTS `test-for-android-notifn.sec_filings.institutional_holdings` (
    ticker STRING NOT NULL,
    filing_date DATE NOT NULL,
    report_period_end_date DATE,
    cik STRING NOT NULL,
    institution_name STRING,
    shares_held INT64,
    market_value FLOAT64,
    shares_change INT64,
    shares_change_pct FLOAT64,
    position_type STRING,  -- NEW, INCREASE, DECREASE, CLOSED
    is_new_position BOOL,
    is_doubling_down BOOL,
    conviction_score FLOAT64,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY filing_date
CLUSTER BY ticker, cik
OPTIONS(
    description="SEC 13F Institutional Holdings",
    labels=[("source", "sec_edgar"), ("type", "13f")]
);

-- 2. Insider Transactions Table (Form 4 Data)
CREATE TABLE IF NOT EXISTS `test-for-android-notifn.sec_filings.insider_transactions` (
    ticker STRING NOT NULL,
    filing_date DATE NOT NULL,
    transaction_date DATE,
    insider_name STRING,
    insider_title STRING,
    transaction_code STRING,  -- P, S, A, D, etc.
    shares FLOAT64,
    price_per_share FLOAT64,
    shares_owned_after FLOAT64,
    is_officer BOOL,
    is_director BOOL,
    is_ten_percent_owner BOOL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY filing_date
CLUSTER BY ticker
OPTIONS(
    description="SEC Form 4 Insider Transactions",
    labels=[("source", "sec_edgar"), ("type", "form4")]
);

-- Sample data insertion (for testing)
-- You would replace this with actual SEC data

INSERT INTO `test-for-android-notifn.sec_filings.institutional_holdings` VALUES
('AAPL', '2023-02-14', '2022-12-31', '0001166559', 'Berkshire Hathaway Inc', 1000000, 150000000, 500000, 100.0, 'INCREASE', false, true, 85.5, CURRENT_TIMESTAMP()),
('MSFT', '2023-02-14', '2022-12-31', '0001067983', 'Baupost Group LLC', 500000, 125000000, 250000, 50.0, 'INCREASE', false, false, 70.2, CURRENT_TIMESTAMP()),
('GOOGL', '2023-02-14', '2022-12-31', '0001350694', 'Pershing Square Capital', 300000, 90000000, 150000, 100.0, 'NEW', true, false, 90.8, CURRENT_TIMESTAMP());

INSERT INTO `test-for-android-notifn.sec_filings.insider_transactions` VALUES
('AAPL', '2023-01-15', '2023-01-10', 'Tim Cook', 'CEO', 'P', 10000, 150.50, 100000, true, false, false, CURRENT_TIMESTAMP()),
('MSFT', '2023-01-20', '2023-01-18', 'Satya Nadella', 'CEO', 'P', 5000, 250.00, 50000, true, false, false, CURRENT_TIMESTAMP());

