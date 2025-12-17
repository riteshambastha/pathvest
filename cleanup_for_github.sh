#!/bin/bash

# ============================================
# Pathvest GitHub Cleanup Script
# ============================================
# This script from Ritesh Ambastha removes temporary, sensitive, and development files
# before committing to GitHub
#
# Usage: chmod +x cleanup_for_github.sh && ./cleanup_for_github.sh

set -e  # Exit on error

echo "🧹 Pathvest GitHub Cleanup Script"
echo "=================================="
echo ""

# Confirm before proceeding
read -p "This will delete temporary files and sensitive data. Continue? (y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]
then
    echo "❌ Cleanup cancelled"
    exit 1
fi

echo ""
echo "📁 Cleaning up backend files..."
cd backend

# Delete sensitive files
echo "  🔒 Removing sensitive files..."
rm -f gcp-credentials.json
echo "    ✓ Deleted gcp-credentials.json"

# Delete backup files
echo "  💾 Removing backup files..."
find app/services -name "*.bak" -type f -delete
echo "    ✓ Deleted *.bak files"

# Delete log files
echo "  📋 Removing log files..."
rm -f *.log
rm -f universe_data_fetch.log
rm -f yfinance_fetch.log
rm -f backend.log
echo "    ✓ Deleted log files"

# Delete database files
echo "  🗄️  Removing database files..."
rm -f pathvest_local.db
rm -f *.sqlite
rm -f *.db
echo "    ✓ Deleted database files"

# Delete CSV data files
echo "  📊 Removing CSV data files..."
rm -f *.csv
rm -f universe_data_stock_liquidity_metrics.csv
rm -f universe_data_stock_market_cap_history.csv
echo "    ✓ Deleted CSV files"

# Delete JSON data files
echo "  📄 Removing JSON data files..."
rm -f *_holdings*.json
rm -f *_filings*.json
rm -f *_metadata.json
rm -f all_real_sec_holdings.json
rm -f expanded_sec*.json
rm -f historical_*.json
rm -f real_sec_*.json
echo "    ✓ Deleted JSON data files"

# Delete migration backups
echo "  🔄 Removing migration backups..."
rm -rf migration_backups/
echo "    ✓ Deleted migration_backups/"

# Delete LEAN data
echo "  🧪 Cleaning LEAN directories..."
rm -rf lean/data/* 2>/dev/null || true
rm -rf lean/results/* 2>/dev/null || true
rm -rf lean_engine/data/* 2>/dev/null || true
echo "    ✓ Cleaned LEAN directories"

# Delete temporary test scripts
echo "  🧪 Removing temporary test scripts..."
rm -f test_*.py
rm -f fetch_*.py
rm -f step*.py
rm -f run_*.py
rm -f generate_*.py
rm -f populate_*.py
rm -f ingest_*.py
rm -f fix_*.py
rm -f verify_*.py
rm -f export_*.py
rm -f batch_*.py
rm -f check_*.py
rm -f add_*.py
rm -f migrate_*.py
rm -f update_*.py
rm -f init_*.py
rm -f setup_postgres_env.py
rm -f import_*.py
echo "    ✓ Deleted temporary scripts"

# Delete backend dev documentation
echo "  📚 Removing backend dev docs..."
rm -f MIGRATION_*.md
echo "    ✓ Deleted backend dev docs"

# Go back to root
cd ..

echo ""
echo "📁 Cleaning up root files..."

# Delete development documentation
echo "  📚 Removing dev documentation..."
rm -f ACCOMPLISHMENTS_CHECKLIST.md
rm -f API_CALL_FLOW.md
rm -f BACKTEST_REAL_DATA_PROOF.md
rm -f BIGQUERY_*.md
rm -f BUG_FIX_*.md
rm -f CHECKLIST.md
rm -f COMPLETE_*.md
rm -f CORRECTED_STATUS_REPORT.md
rm -f DATA_INGESTION_SUMMARY.md
rm -f DATA_STATUS_REPORT.md
rm -f DRAWDOWN_DISPLAY_FIX.md
rm -f DUAL_ENGINE_TESTING_GUIDE.md
rm -f DYNAMIC_*.md
rm -f EXIT_MODULES_EXECUTIVE_SUMMARY.md
rm -f EXPANDED_SEC_DATABASE.md
rm -f FINAL_SESSION_SUMMARY.md
rm -f FINAL_UNIVERSE_DATA_SUMMARY.md
rm -f FRONTEND_COMPLETE_VERIFICATION.md
rm -f FRONTEND_STEPS_COMPLETE.md
rm -f IMPLEMENTATION_*.md
rm -f INSTITUTIONAL_FOLLOWING_COMPLETE.md
rm -f INTERACTIVE_LOADING_SCREEN.md
rm -f LEAN_FINAL_SUMMARY.md
rm -f LEAN_PHASE1_COMPLETE.md
rm -f LOCAL_TEST_RESULTS.md
rm -f MILESTONE_*.md
rm -f MISSION_ACCOMPLISHED.md
rm -f MY_STRATEGIES_*.md
rm -f NA_VALUES_FIX.md
rm -f NEW_SUMMARY_INTERFACE.md
rm -f PHASE*.md
rm -f POSITION_SIZING_EXECUTIVE_SUMMARY.md
rm -f POSTGRES_STRATEGY_STORAGE.md
rm -f PROJECT_COMPLETE.md
rm -f PROJECT_SUMMARY.md
rm -f PROJECT_README.md
rm -f QUICK_START_INSTITUTIONAL.md
rm -f QUICK_START_STRATEGY_STORAGE.md
rm -f QUICK_TEST_GUIDE.md
rm -f READY_TO_BACKTEST_SUMMARY.md
rm -f REAL_DATA_UI_UPDATE.md
rm -f REAL_HISTORICAL_BACKTESTING.md
rm -f REAL_VS_MOCK_*.md
rm -f SEC_INTEGRATION_GUIDE.md
rm -f SETUP_COMPLETE.md
rm -f SIGNAL_ENGINE_EXECUTIVE_SUMMARY.md
rm -f STOCK_DIVERSITY_UPDATE.md
rm -f STRATEGY_STORAGE_ACTIVATED.md
rm -f TABS_COMPLETE_GUIDE.md
rm -f TABS_DATA_STATUS.md
rm -f TEST_COMPLETE_FRONTEND.md
rm -f TEST_REAL_BACKTESTING_NOW.md
rm -f TEST_RESULTS_API_FLOW.md
rm -f TEST_RESULTS_FINAL.md
rm -f TIMEOUT_FIX.md
rm -f TODAYS_PROGRESS_SUMMARY.md
rm -f UNIVERSE_DATA_*.md
rm -f VISUALIZATIONS_STATUS.md
rm -f BACKTEST_UX_IMPROVEMENT.md
echo "    ✓ Deleted dev documentation"

# Delete test scripts
echo "  🧪 Removing test scripts..."
rm -f test_institutional_flow.sh
rm -f test_real_data.sh
echo "    ✓ Deleted test scripts"

# Delete log files
echo "  📋 Removing root log files..."
rm -f frontend.log
rm -f *.log
echo "    ✓ Deleted log files"

# Delete Docker image
echo "  🐳 Removing Docker image..."
rm -f Docker.dmg
echo "    ✓ Deleted Docker.dmg"

echo ""
echo "🔍 Scanning for remaining sensitive data..."

# Search for potential secrets
echo ""
echo "  Checking for API keys..."
FOUND_KEYS=$(grep -r "API_KEY.*=" --exclude-dir=venv --exclude-dir=venv-lean --exclude-dir=node_modules --exclude="*.md" --exclude=".env.example" --exclude="cleanup_for_github.sh" . 2>/dev/null | grep -v "your_" | grep -v "VITE_" | grep -v "example" || true)

if [ -n "$FOUND_KEYS" ]; then
    echo "  ⚠️  WARNING: Potential API keys found:"
    echo "$FOUND_KEYS"
    echo ""
    read -p "  Continue anyway? (y/n) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Cleanup halted. Please review and remove sensitive data."
        exit 1
    fi
else
    echo "  ✓ No hardcoded API keys found"
fi

echo ""
echo "✅ Cleanup Complete!"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 Next Steps:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "1. Review changes:"
echo "   git status"
echo ""
echo "2. Verify .env files are not tracked:"
echo "   git ls-files | grep .env"
echo ""
echo "3. Check for any remaining sensitive files:"
echo "   git ls-files | grep -E 'credentials|\.log$|\.db$'"
echo ""
echo "4. Review the files to be committed:"
echo "   git add ."
echo "   git status"
echo ""
echo "5. Commit your code:"
echo "   git commit -m 'Initial commit: Pathvest trading platform'"
echo ""
echo "6. Push to GitHub:"
echo "   git remote add origin <your-repo-url>"
echo "   git push -u origin main"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "✨ Your codebase is now ready for GitHub!"
echo ""

