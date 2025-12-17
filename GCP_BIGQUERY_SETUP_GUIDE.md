# Google Cloud Platform & BigQuery Setup Guide

## 🎯 **Overview: Why BigQuery?**

BigQuery is Google's data warehouse designed for **storing and querying massive datasets**. For PathVest, it's perfect for:

### **What BigQuery Enables:**
- ✅ **Historical SEC Data**: Store years of 13F filings (not just recent)
- ✅ **Fast Queries**: Analyze millions of records in seconds
- ✅ **Point-in-Time Accuracy**: Query data as it existed at any past date
- ✅ **Scalability**: Handle growing data without performance issues
- ✅ **Cost-Effective**: Pay only for storage + queries used

### **Without BigQuery (Current State):**
- ⚠️ Data stored in-memory (lost on restart)
- ⚠️ Limited to recent filings only
- ⚠️ No historical analysis
- ⚠️ Manual data refresh required

### **With BigQuery (Future State):**
- ✅ Persistent data warehouse
- ✅ Full 13F history (10+ years)
- ✅ Automated daily ingestion
- ✅ Sub-second queries on millions of records

---

## 💰 **Cost Breakdown**

### **Free Tier (Generous!):**
- **Storage**: First 10 GB free, then $0.02/GB/month
- **Queries**: First 1 TB free per month, then $5/TB
- **Typical Usage**: ~$5-10/month for PathVest

### **Example Costs:**
| Component | Usage | Cost |
|-----------|-------|------|
| **SEC Data Storage** | 50 GB (5 years of filings) | $1.00/month |
| **Query Processing** | 100 GB/month | Free (under 1 TB limit) |
| **Backtest Results** | 10 GB | Free (under 10 GB limit) |
| **TOTAL** | | **~$1-2/month** |

---

## 📋 **Prerequisites**

Before you start, you need:
- [ ] Google account (Gmail)
- [ ] Credit card (for GCP billing, won't be charged on free tier)
- [ ] 30 minutes of time

---

## 🚀 **Step-by-Step Setup**

---

## **PART 1: Create Google Cloud Project**

### **Step 1.1: Go to GCP Console**

Open: https://console.cloud.google.com/

If first time:
1. Click "Get started for free"
2. Sign in with your Google account
3. Accept terms of service
4. Enter billing information (required, but won't charge on free tier)
5. Get $300 free credit for 90 days

---

### **Step 1.2: Create New Project**

```
1. Click on project dropdown (top left, next to "Google Cloud")
2. Click "New Project"
3. Fill in:
   - Project name: "pathvest-prod"
   - Project ID: "pathvest-prod-XXXXX" (auto-generated)
   - Location: "No organization"
4. Click "Create"
5. Wait ~30 seconds
6. Select the new project from dropdown
```

**Note your Project ID** - you'll need it later!

---

## **PART 2: Enable Required APIs**

### **Step 2.1: Enable BigQuery API**

```
1. In GCP Console, go to: "APIs & Services" > "Library"
   OR visit: https://console.cloud.google.com/apis/library
   
2. Search for "BigQuery API"
3. Click on "BigQuery API"
4. Click "Enable"
5. Wait ~10 seconds
```

### **Step 2.2: Enable Other APIs (Optional but Recommended)**

Enable these for full PathVest functionality:

```
- Cloud Storage API (for file storage)
- Cloud Run API (for deployment)
- Secret Manager API (for API keys)
- Cloud Build API (for CI/CD)
```

---

## **PART 3: Create BigQuery Dataset**

### **Step 3.1: Navigate to BigQuery**

```
1. In GCP Console, search for "BigQuery" in top search bar
2. Click "BigQuery" (or visit: https://console.cloud.google.com/bigquery)
3. You'll see the BigQuery Studio interface
```

---

### **Step 3.2: Create Dataset for SEC Filings**

```
1. In the Explorer panel (left side):
   - Find your project "pathvest-prod"
   - Click the 3 dots next to it
   - Select "Create dataset"

2. Dataset Configuration:
   ┌─────────────────────────────────────────┐
   │ Dataset ID: sec_filings                 │
   │ Data location: US (multi-region)        │
   │ Default table expiration: Never         │
   │ Encryption: Google-managed key          │
   └─────────────────────────────────────────┘

3. Click "Create Dataset"
```

---

### **Step 3.3: Create Dataset for Backtest Results**

```
1. Click 3 dots next to your project again
2. Select "Create dataset"
3. Dataset Configuration:
   ┌─────────────────────────────────────────┐
   │ Dataset ID: backtest_results            │
   │ Data location: US (multi-region)        │
   │ Default table expiration: Never         │
   │ Encryption: Google-managed key          │
   └─────────────────────────────────────────┘

4. Click "Create Dataset"
```

---

### **Step 3.4: Create Tables**

Now create the tables inside `sec_filings` dataset:

#### **Table 1: form_13f_holdings**

```sql
-- Copy this SQL and paste into BigQuery Query Editor
CREATE TABLE `pathvest-prod.sec_filings.form_13f_holdings` (
  -- Filing identifiers
  accession_number STRING NOT NULL,
  filing_date DATE NOT NULL,
  report_period_date DATE NOT NULL,
  
  -- Institutional investor info
  cik STRING NOT NULL,
  filer_name STRING,
  filer_type STRING,
  
  -- Holding details
  cusip STRING NOT NULL,
  ticker STRING,
  issuer_name STRING,
  security_type STRING,
  
  -- Position info
  shares FLOAT64,
  value_usd FLOAT64,
  percentage_of_portfolio FLOAT64,
  
  -- Voting authority
  voting_authority_sole FLOAT64,
  voting_authority_shared FLOAT64,
  voting_authority_none FLOAT64,
  
  -- Investment discretion
  investment_discretion STRING,
  
  -- Metadata
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY filing_date
CLUSTER BY cik, ticker, filing_date
OPTIONS(
  description="13F institutional holdings data from SEC EDGAR",
  labels=[("source", "sec_edgar"), ("type", "13f")]
);
```

**How to run:**
1. Click "+ Compose new query" button
2. Paste the SQL above
3. Replace `pathvest-prod` with YOUR project ID
4. Click "Run"

---

#### **Table 2: form_4_insider_transactions**

```sql
CREATE TABLE `pathvest-prod.sec_filings.form_4_insider_transactions` (
  -- Filing identifiers
  accession_number STRING NOT NULL,
  filing_date DATE NOT NULL,
  transaction_date DATE,
  deemed_execution_date DATE,
  
  -- Company info
  issuer_cik STRING NOT NULL,
  issuer_name STRING,
  ticker STRING,
  
  -- Reporting person (insider)
  reporting_owner_cik STRING,
  reporting_owner_name STRING,
  reporting_owner_relationship STRING, -- Director, Officer, 10% Owner, Other
  officer_title STRING,
  
  -- Transaction details
  transaction_code STRING, -- P=Purchase, S=Sale, A=Award, D=Disposal
  transaction_shares FLOAT64,
  transaction_price_per_share FLOAT64,
  transaction_value FLOAT64,
  shares_owned_after FLOAT64,
  ownership_type STRING, -- Direct or Indirect
  
  -- Metadata
  is_10b5_1_plan BOOLEAN,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY filing_date
CLUSTER BY issuer_cik, ticker, filing_date
OPTIONS(
  description="Form 4 insider transaction data from SEC EDGAR",
  labels=[("source", "sec_edgar"), ("type", "form4")]
);
```

---

#### **Table 3: backtest_runs**

```sql
CREATE TABLE `pathvest-prod.backtest_results.backtest_runs` (
  -- Backtest identifiers
  backtest_id STRING NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  status STRING, -- running, completed, failed
  
  -- Strategy config
  strategy_name STRING,
  strategy_config JSON,
  
  -- Backtest period
  start_date DATE,
  end_date DATE,
  initial_capital FLOAT64,
  
  -- Performance metrics
  total_return FLOAT64,
  cagr FLOAT64,
  volatility FLOAT64,
  sharpe_ratio FLOAT64,
  sortino_ratio FLOAT64,
  max_drawdown FLOAT64,
  
  -- Trade statistics
  total_trades INT64,
  winning_trades INT64,
  losing_trades INT64,
  win_rate FLOAT64,
  
  -- Data sources
  data_sources JSON,
  
  -- Full results (JSON)
  results_json JSON
)
PARTITION BY DATE(created_at)
CLUSTER BY backtest_id, strategy_name
OPTIONS(
  description="Backtest execution results and performance metrics",
  labels=[("type", "backtest_results")]
);
```

---

## **PART 4: Create Service Account (Authentication)**

Your backend needs credentials to access BigQuery.

### **Step 4.1: Create Service Account**

```
1. Go to: "IAM & Admin" > "Service Accounts"
   OR: https://console.cloud.google.com/iam-admin/serviceaccounts

2. Click "+ Create Service Account"

3. Service Account Details:
   ┌─────────────────────────────────────────────────────┐
   │ Name: pathvest-backend                              │
   │ ID: pathvest-backend@pathvest-prod.iam...          │
   │ Description: Service account for PathVest backend   │
   └─────────────────────────────────────────────────────┘
   
4. Click "Create and Continue"
```

---

### **Step 4.2: Grant Permissions**

```
5. Grant roles:
   Select role: "BigQuery Admin"
   Select role: "BigQuery Data Editor"
   Select role: "BigQuery Job User"
   
6. Click "Continue"
7. Click "Done"
```

---

### **Step 4.3: Create and Download Key**

```
8. Find your new service account in the list
9. Click on it
10. Go to "Keys" tab
11. Click "Add Key" > "Create new key"
12. Select "JSON" format
13. Click "Create"
14. Save the downloaded file as:
    /Users/riteshambastha/projects/pathvest/backend/gcp-credentials.json
```

**⚠️ IMPORTANT: Keep this file secure! It's like a password.**

---

## **PART 5: Configure PathVest Backend**

### **Step 5.1: Update .env File**

```bash
cd /Users/riteshambastha/projects/pathvest/backend
```

Add these lines to your `.env` file:

```bash
# Google Cloud Configuration
GCP_PROJECT_ID=pathvest-prod-XXXXX  # ← YOUR PROJECT ID
GOOGLE_APPLICATION_CREDENTIALS=./gcp-credentials.json
BIGQUERY_DATASET_SEC=sec_filings
BIGQUERY_DATASET_BACKTEST=backtest_results
BIGQUERY_LOCATION=US

# Enable BigQuery
ENABLE_BIGQUERY=True
```

---

### **Step 5.2: Secure the Credentials File**

```bash
# Move credentials to backend directory
mv ~/Downloads/pathvest-prod-*.json /Users/riteshambastha/projects/pathvest/backend/gcp-credentials.json

# Make it read-only
chmod 600 /Users/riteshambastha/projects/pathvest/backend/gcp-credentials.json

# Add to .gitignore (so it's never committed)
echo "gcp-credentials.json" >> /Users/riteshambastha/projects/pathvest/backend/.gitignore
```

---

## **PART 6: Install Python Dependencies**

```bash
cd /Users/riteshambastha/projects/pathvest/backend
source venv/bin/activate

# Install BigQuery client library
pip install google-cloud-bigquery google-cloud-storage

# Save to requirements
pip freeze | grep google-cloud > requirements-bigquery.txt
```

---

## **PART 7: Test BigQuery Connection**

### **Step 7.1: Create Test Script**

Create `/Users/riteshambastha/projects/pathvest/backend/test_bigquery.py`:

```python
"""Test BigQuery connection"""
from google.cloud import bigquery
import os
from datetime import datetime

# Set credentials
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = './gcp-credentials.json'

def test_bigquery_connection():
    """Test connection to BigQuery"""
    try:
        # Initialize client
        project_id = "pathvest-prod-XXXXX"  # ← YOUR PROJECT ID
        client = bigquery.Client(project=project_id)
        
        print("=" * 60)
        print("🔍 Testing BigQuery Connection")
        print("=" * 60)
        
        # Test 1: List datasets
        print("\n1. Listing datasets...")
        datasets = list(client.list_datasets())
        if datasets:
            print(f"✅ Found {len(datasets)} datasets:")
            for dataset in datasets:
                print(f"   • {dataset.dataset_id}")
        else:
            print("⚠️  No datasets found")
        
        # Test 2: Query test
        print("\n2. Running test query...")
        query = "SELECT 'Hello from BigQuery!' as message, CURRENT_TIMESTAMP() as timestamp"
        results = client.query(query).result()
        for row in results:
            print(f"✅ {row.message}")
            print(f"   Timestamp: {row.timestamp}")
        
        # Test 3: Check tables
        print("\n3. Checking tables in sec_filings dataset...")
        dataset_ref = client.dataset("sec_filings")
        tables = list(client.list_tables(dataset_ref))
        if tables:
            print(f"✅ Found {len(tables)} tables:")
            for table in tables:
                print(f"   • {table.table_id}")
        else:
            print("⚠️  No tables found (create them first)")
        
        # Test 4: Insert sample data
        print("\n4. Inserting sample 13F holding...")
        table_id = f"{project_id}.sec_filings.form_13f_holdings"
        
        rows_to_insert = [{
            "accession_number": "0001234567-24-000001",
            "filing_date": "2024-11-14",
            "report_period_date": "2024-09-30",
            "cik": "0001067983",
            "filer_name": "BERKSHIRE HATHAWAY INC",
            "cusip": "037833100",
            "ticker": "AAPL",
            "issuer_name": "APPLE INC",
            "shares": 300000000,
            "value_usd": 82000000000,
            "percentage_of_portfolio": 23.5
        }]
        
        errors = client.insert_rows_json(table_id, rows_to_insert)
        if not errors:
            print("✅ Sample data inserted successfully!")
        else:
            print(f"⚠️  Errors: {errors}")
        
        # Test 5: Query inserted data
        print("\n5. Querying inserted data...")
        query = f"""
            SELECT 
                filer_name,
                ticker,
                shares,
                value_usd,
                filing_date
            FROM `{project_id}.sec_filings.form_13f_holdings`
            WHERE ticker = 'AAPL'
            LIMIT 5
        """
        results = client.query(query).result()
        
        print("\n✅ Query results:")
        for row in results:
            print(f"   {row.filer_name}: {row.shares:,.0f} shares of {row.ticker} (${row.value_usd:,.0f})")
        
        print("\n" + "=" * 60)
        print("🎉 BigQuery Connection Test PASSED!")
        print("=" * 60)
        print("\n✅ Your BigQuery setup is working correctly!")
        print("✅ You can now store historical SEC data")
        print("✅ Ready for production data ingestion")
        
    except Exception as e:
        print("\n" + "=" * 60)
        print("❌ BigQuery Connection Test FAILED")
        print("=" * 60)
        print(f"\nError: {e}")
        print("\nTroubleshooting:")
        print("1. Check your project ID in the script")
        print("2. Verify gcp-credentials.json exists")
        print("3. Ensure service account has BigQuery permissions")
        print("4. Check that datasets and tables are created")

if __name__ == "__main__":
    test_bigquery_connection()
```

---

### **Step 7.2: Run Test**

```bash
cd /Users/riteshambastha/projects/pathvest/backend
source venv/bin/activate
python test_bigquery.py
```

**Expected output:**
```
============================================================
🔍 Testing BigQuery Connection
============================================================

1. Listing datasets...
✅ Found 2 datasets:
   • sec_filings
   • backtest_results

2. Running test query...
✅ Hello from BigQuery!
   Timestamp: 2025-12-15 22:00:00 UTC

3. Checking tables in sec_filings dataset...
✅ Found 2 tables:
   • form_13f_holdings
   • form_4_insider_transactions

4. Inserting sample 13F holding...
✅ Sample data inserted successfully!

5. Querying inserted data...
✅ Query results:
   BERKSHIRE HATHAWAY INC: 300,000,000 shares of AAPL ($82,000,000,000)

============================================================
🎉 BigQuery Connection Test PASSED!
============================================================
```

---

## **PART 8: Verify in GCP Console**

### **Step 8.1: Check Data in BigQuery UI**

```
1. Go back to BigQuery in GCP Console
2. Expand your project > sec_filings > form_13f_holdings
3. Click "Preview" tab
4. You should see the test data you inserted!
```

---

## 🎉 **Setup Complete!**

### **What You've Accomplished:**

✅ **Created GCP Project**: pathvest-prod  
✅ **Enabled BigQuery API**: Ready to use  
✅ **Created Datasets**: sec_filings + backtest_results  
✅ **Created Tables**: Holdings, transactions, backtests  
✅ **Service Account**: Authentication configured  
✅ **Credentials**: Downloaded and secured  
✅ **Backend Configuration**: .env updated  
✅ **Connection Tested**: Working correctly  

---

## 🚀 **What's Next?**

### **Option 1: Start Data Ingestion (Recommended)**

Now that BigQuery is set up, you can:

1. **Bulk Load Historical Data**: Upload past 5+ years of 13F filings
2. **Schedule Daily Updates**: Auto-fetch new filings
3. **Enable Point-in-Time Queries**: Accurate historical analysis

### **Option 2: Update Backend to Use BigQuery**

Modify the backend to:
- Store SEC data in BigQuery (not in-memory)
- Query historical filings for backtests
- Persist backtest results permanently

### **Option 3: Continue with Current Setup**

Keep using in-memory storage for now, knowing BigQuery is ready when needed.

---

## 💰 **Billing & Cost Management**

### **Monitor Your Costs:**

```
1. Go to: "Billing" > "Reports" in GCP Console
2. View: Usage by service
3. Check: BigQuery costs

Typical monthly costs:
- Storage: $0.50 - $2.00
- Queries: $0.00 (under free tier)
- Total: ~$1-2/month
```

### **Set Budget Alerts:**

```
1. Go to: "Billing" > "Budgets & alerts"
2. Create budget
3. Amount: $10/month
4. Alert threshold: 50%, 90%, 100%
5. Email notifications: Your email
```

---

## 🔒 **Security Best Practices**

### **✅ Do:**
- Keep `gcp-credentials.json` secure (never commit to Git)
- Use `.gitignore` to exclude credentials
- Rotate service account keys periodically
- Use minimal required permissions

### **❌ Don't:**
- Share credentials publicly
- Commit credentials to Git
- Use overly permissive roles
- Leave unused service accounts active

---

## 📚 **Useful Resources**

- **BigQuery Console**: https://console.cloud.google.com/bigquery
- **BigQuery Documentation**: https://cloud.google.com/bigquery/docs
- **Pricing Calculator**: https://cloud.google.com/products/calculator
- **Python Client Docs**: https://cloud.google.com/python/docs/reference/bigquery/latest

---

## 🆘 **Troubleshooting**

### **Problem: "Permission denied" error**

**Solution:**
```
1. Check service account has correct roles:
   - BigQuery Admin
   - BigQuery Data Editor
   - BigQuery Job User

2. Verify credentials path in .env:
   GOOGLE_APPLICATION_CREDENTIALS=./gcp-credentials.json

3. Check file permissions:
   chmod 600 gcp-credentials.json
```

---

### **Problem: "Dataset not found"**

**Solution:**
```
1. Verify dataset names match exactly:
   - sec_filings (not sec-filings or SEC_FILINGS)
   - backtest_results (not backtest-results)

2. Check project ID is correct in queries
3. Ensure datasets are in same location (US)
```

---

### **Problem: "Exceeded rate limit"**

**Solution:**
```
Free tier limits:
- Storage: 10 GB free
- Queries: 1 TB/month free

If exceeded:
1. Check usage in Billing > Reports
2. Optimize queries (use LIMIT, WHERE clauses)
3. Consider upgrading (still very cheap)
```

---

## ✅ **Quick Checklist**

Before you start, make sure you have:

- [ ] GCP account created
- [ ] Project created: pathvest-prod
- [ ] BigQuery API enabled
- [ ] Datasets created: sec_filings, backtest_results
- [ ] Tables created: form_13f_holdings, form_4_insider_transactions, backtest_runs
- [ ] Service account created
- [ ] Service account key downloaded
- [ ] Credentials file in backend directory
- [ ] .env file updated
- [ ] Python dependencies installed
- [ ] Connection test passed
- [ ] Sample data inserted and queried

---

**🎉 Once all checked, your BigQuery integration is complete!**

**Ready to store millions of SEC filings and run lightning-fast queries!** ⚡📊

