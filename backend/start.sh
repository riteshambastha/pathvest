#!/bin/bash
# Start script for Render deployment
# Sets PYTHONPATH to ensure lean_engine can be imported

# Render runs from /opt/render/project/src/backend directory
# So we need to add the current directory to PYTHONPATH
export PYTHONPATH=$(pwd):$PYTHONPATH

echo "🚀 Starting PathVest Backend"
echo "📍 PYTHONPATH: $PYTHONPATH"
echo "📍 Current directory: $(pwd)"
echo ""
echo "📂 Checking directory structure..."
ls -la | head -20
echo ""
echo "📂 Checking lean_engine..."
if [ -d "lean_engine" ]; then
    echo "✅ lean_engine directory exists"
    ls -la lean_engine/
    echo ""
    echo "📂 Checking lean_engine/__init__.py..."
    if [ -f "lean_engine/__init__.py" ]; then
        echo "✅ lean_engine/__init__.py exists"
        cat lean_engine/__init__.py
    else
        echo "❌ lean_engine/__init__.py NOT FOUND"
    fi
    echo ""
    echo "📂 Checking lean_engine/worker..."
    if [ -d "lean_engine/worker" ]; then
        echo "✅ lean_engine/worker directory exists"
        ls -la lean_engine/worker/
        echo ""
        if [ -f "lean_engine/worker/__init__.py" ]; then
            echo "✅ lean_engine/worker/__init__.py exists"
        else
            echo "❌ lean_engine/worker/__init__.py NOT FOUND"
        fi
    else
        echo "❌ lean_engine/worker directory NOT FOUND"
    fi
else
    echo "❌ lean_engine directory NOT FOUND"
fi

echo ""
echo "🔍 Verifying imports..."
# Verify imports before starting
python3 -c "
import sys
print(f'Python version: {sys.version}')
print(f'Python path: {sys.path[:5]}')
print()
try:
    import lean_engine
    print(f'✅ lean_engine module found at: {lean_engine.__file__}')
except Exception as e:
    print(f'❌ lean_engine import failed: {e}')
    import traceback
    traceback.print_exc()
print()
try:
    from lean_engine.worker import backtest_worker
    print('✅ lean_engine.worker.backtest_worker imports successfully')
except Exception as e:
    print(f'❌ lean_engine.worker.backtest_worker import failed: {e}')
    import traceback
    traceback.print_exc()
print()
try:
    from app.services.backtest_orchestrator import BacktestOrchestrator
    print('✅ BacktestOrchestrator imports successfully')
except Exception as e:
    print(f'❌ BacktestOrchestrator import failed: {e}')
"

echo ""
echo "🚀 Starting uvicorn..."
# Start the FastAPI server
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}


