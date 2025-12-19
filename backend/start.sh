#!/bin/bash
# Start script for Render deployment
# Sets PYTHONPATH to ensure lean_engine can be imported

export PYTHONPATH=/opt/render/project/src/backend:$PYTHONPATH

echo "🚀 Starting PathVest Backend"
echo "📍 PYTHONPATH: $PYTHONPATH"
echo "📍 Current directory: $(pwd)"

# Start the FastAPI server
uvicorn app.main:app --host 0.0.0.0 --port 8000

