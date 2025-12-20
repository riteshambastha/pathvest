#!/bin/bash
# ==============================================
# Environment Setup Script for Pathvest
# Usage: ./scripts/setup-env.sh [staging|production]
# ==============================================

ENV=${1:-staging}

echo "🔧 Setting up $ENV environment..."

if [ "$ENV" == "staging" ]; then
    cp backend/.env.staging backend/.env
    cp frontend/.env.staging frontend/.env
    echo "✅ Staging environment configured"
    echo ""
    echo "📋 Next steps:"
    echo "   1. cd backend && source venv/bin/activate && uvicorn app.main:app --reload"
    echo "   2. cd frontend && npm run dev"
elif [ "$ENV" == "production" ]; then
    if [ ! -f "backend/.env.production" ]; then
        echo "❌ backend/.env.production not found!"
        echo "   Create it from backend/.env.example with your production values"
        exit 1
    fi
    cp backend/.env.production backend/.env
    cp frontend/.env.production frontend/.env
    echo "✅ Production environment configured"
else
    echo "❌ Unknown environment: $ENV"
    echo "Usage: ./scripts/setup-env.sh [staging|production]"
    exit 1
fi
