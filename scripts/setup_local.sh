#!/bin/bash

# Local Development Setup Script for PathVest

set -e

echo "========================================="
echo "PathVest Local Development Setup"
echo "========================================="
echo ""

# Check prerequisites
check_prerequisites() {
    echo "Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        echo "❌ Docker not found. Please install Docker Desktop."
        exit 1
    fi
    echo "✅ Docker found"
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        echo "❌ Docker Compose not found. Please install Docker Compose."
        exit 1
    fi
    echo "✅ Docker Compose found"
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        echo "❌ Python 3 not found. Please install Python 3.11+."
        exit 1
    fi
    echo "✅ Python 3 found"
    
    # Check Node.js
    if ! command -v node &> /dev/null; then
        echo "❌ Node.js not found. Please install Node.js 18+."
        exit 1
    fi
    echo "✅ Node.js found"
    
    echo ""
}

# Setup environment files
setup_env_files() {
    echo "Setting up environment files..."
    
    # Backend .env
    if [ ! -f ".env" ]; then
        cp .env.example .env
        echo "✅ Created .env from .env.example"
        echo "⚠️  Please edit .env and add your API keys"
    else
        echo "✅ .env already exists"
    fi
    
    # Frontend .env
    if [ ! -f "frontend/.env" ]; then
        echo "VITE_API_BASE_URL=http://localhost:8000/api/v1" > frontend/.env
        echo "✅ Created frontend/.env"
    else
        echo "✅ frontend/.env already exists"
    fi
    
    echo ""
}

# Install Python dependencies
install_python_deps() {
    echo "Installing Python dependencies..."
    cd backend
    
    if [ ! -d "venv" ]; then
        python3 -m venv venv
        echo "✅ Created Python virtual environment"
    fi
    
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    
    cd ..
    echo "✅ Python dependencies installed"
    echo ""
}

# Install Node.js dependencies
install_node_deps() {
    echo "Installing Node.js dependencies..."
    cd frontend
    npm install
    cd ..
    echo "✅ Node.js dependencies installed"
    echo ""
}

# Setup Docker containers
setup_docker() {
    echo "Setting up Docker containers..."
    docker-compose up -d postgres redis
    
    echo "Waiting for PostgreSQL to be ready..."
    sleep 5
    
    echo "✅ Docker containers running"
    echo ""
}

# Run database migrations
run_migrations() {
    echo "Running database migrations..."
    cd backend
    source venv/bin/activate
    
    # Create tables from models
    python -c "
from app.db.base import Base
from app.core.config import settings
from sqlalchemy import create_engine

engine = create_engine(settings.DATABASE_URL)
Base.metadata.create_all(bind=engine)
print('✅ Database tables created')
"
    
    cd ..
    echo ""
}

# Load mock data
load_mock_data() {
    echo "Loading mock SEC data..."
    cd backend
    source venv/bin/activate
    
    python -c "
from app.services.mock_data.mock_sec_provider import MockSECProvider
from app.services.bigquery_service import BigQueryService
from datetime import datetime, timedelta

print('Generating mock 13F filings...')
provider = MockSECProvider()

# Generate filings for last 2 years
end_date = datetime.now()
start_date = end_date - timedelta(days=730)

filings = provider.get_13f_filings(start_date, end_date)
print(f'✅ Generated {len(filings)} mock 13F filings')

# Note: In production, this would upload to BigQuery
# For local dev, data is generated on-demand
"
    
    cd ..
    echo ""
}

# Main setup flow
main() {
    check_prerequisites
    setup_env_files
    install_python_deps
    install_node_deps
    setup_docker
    run_migrations
    load_mock_data
    
    echo "========================================="
    echo "✅ Setup Complete!"
    echo "========================================="
    echo ""
    echo "To start the development environment:"
    echo ""
    echo "1. Start backend:"
    echo "   cd backend"
    echo "   source venv/bin/activate"
    echo "   uvicorn app.main:app --reload"
    echo ""
    echo "2. Start frontend (in new terminal):"
    echo "   cd frontend"
    echo "   npm run dev"
    echo ""
    echo "3. Access the application:"
    echo "   Frontend: http://localhost:3000"
    echo "   Backend API: http://localhost:8000"
    echo "   API Docs: http://localhost:8000/docs"
    echo ""
    echo "Or use Docker Compose:"
    echo "   docker-compose up"
    echo ""
}

# Run main setup
main

