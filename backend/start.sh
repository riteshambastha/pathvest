#!/bin/bash
# Start script for Render deployment
# Sets PYTHONPATH to ensure lean_engine can be imported

# Render runs from /opt/render/project/src/backend directory
# So we need to add the current directory to PYTHONPATH
export PYTHONPATH=$(pwd):$PYTHONPATH

echo "🚀 Starting PathVest Backend"
echo "📍 PYTHONPATH: $PYTHONPATH"
echo "📍 Current directory: $(pwd)"
echo "📍 Checking lean_engine..."
ls -la lean_engine/ 2>/dev/null && echo "✅ lean_engine directory exists" || echo "❌ lean_engine directory not found"

# Verify imports before starting
python3 -c "
import sys
print(f'Python path: {sys.path[:3]}')
try:
    from lean_engine.worker.backtest_worker import get_backtest_worker
    print('✅ lean_engine imports successfully')
except Exception as e:
    print(f'⚠️ lean_engine import failed: {e}')
try:
    from app.services.backtest_orchestrator import BacktestOrchestrator
    print('✅ BacktestOrchestrator imports successfully')
except Exception as e:
    print(f'⚠️ BacktestOrchestrator import failed: {e}')
"

# Start the FastAPI server
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}


