#!/bin/bash

# PathVest Deployment Script
# Usage: ./deploy.sh [environment] [component]
# Example: ./deploy.sh prod all
# Example: ./deploy.sh staging backend

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default values
ENVIRONMENT="${1:-dev}"
COMPONENT="${2:-all}"
PROJECT_ID="${GCP_PROJECT_ID}"
REGION="us-central1"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}PathVest Deployment Script${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "Environment: ${YELLOW}${ENVIRONMENT}${NC}"
echo -e "Component: ${YELLOW}${COMPONENT}${NC}"
echo -e "Project: ${YELLOW}${PROJECT_ID}${NC}"
echo ""

# Validate inputs
if [[ -z "$PROJECT_ID" ]]; then
    echo -e "${RED}Error: GCP_PROJECT_ID environment variable not set${NC}"
    exit 1
fi

if [[ ! "$ENVIRONMENT" =~ ^(dev|staging|prod)$ ]]; then
    echo -e "${RED}Error: Environment must be dev, staging, or prod${NC}"
    exit 1
fi

# Set project
echo -e "${GREEN}Setting GCP project...${NC}"
gcloud config set project "$PROJECT_ID"

# Deploy infrastructure with Terraform
deploy_infrastructure() {
    echo -e "${GREEN}Deploying infrastructure with Terraform...${NC}"
    cd terraform
    terraform init
    terraform plan -var="project_id=$PROJECT_ID" -var="environment=$ENVIRONMENT" -out=tfplan
    terraform apply tfplan
    cd ..
    echo -e "${GREEN}Infrastructure deployed successfully!${NC}"
}

# Deploy backend
deploy_backend() {
    echo -e "${GREEN}Deploying backend...${NC}"
    
    # Build and push Docker image
    echo "Building backend Docker image..."
    gcloud builds submit --config=cloudbuild.yaml --substitutions=_COMPONENT=backend .
    
    # Deploy to Cloud Run
    echo "Deploying to Cloud Run..."
    gcloud run deploy pathvest-backend \
        --image gcr.io/$PROJECT_ID/pathvest-backend:latest \
        --region $REGION \
        --platform managed \
        --allow-unauthenticated \
        --memory 2Gi \
        --cpu 2 \
        --timeout 900 \
        --max-instances 10 \
        --set-env-vars ENVIRONMENT=$ENVIRONMENT,GCP_PROJECT_ID=$PROJECT_ID \
        --set-secrets DATABASE_URL=DATABASE_URL:latest,ALPHAVANTAGE_API_KEY=ALPHAVANTAGE_API_KEY:latest
    
    echo -e "${GREEN}Backend deployed successfully!${NC}"
}

# Deploy LEAN worker
deploy_lean_worker() {
    echo -e "${GREEN}Deploying LEAN worker...${NC}"
    
    # Build and push Docker image
    echo "Building LEAN worker Docker image..."
    gcloud builds submit --config=cloudbuild.yaml --substitutions=_COMPONENT=lean-worker .
    
    # Deploy to Cloud Run
    echo "Deploying LEAN worker to Cloud Run..."
    gcloud run deploy pathvest-lean-worker \
        --image gcr.io/$PROJECT_ID/pathvest-lean-worker:latest \
        --region $REGION \
        --platform managed \
        --no-allow-unauthenticated \
        --memory 4Gi \
        --cpu 4 \
        --timeout 3600 \
        --max-instances 5 \
        --set-secrets DATABASE_URL=DATABASE_URL:latest
    
    echo -e "${GREEN}LEAN worker deployed successfully!${NC}"
}

# Deploy frontend
deploy_frontend() {
    echo -e "${GREEN}Deploying frontend...${NC}"
    
    # Build frontend
    echo "Building frontend..."
    cd frontend
    npm ci
    npm run build
    
    # Deploy to Firebase Hosting
    echo "Deploying to Firebase Hosting..."
    firebase deploy --only hosting --project $PROJECT_ID
    cd ..
    
    echo -e "${GREEN}Frontend deployed successfully!${NC}"
}

# Run database migrations
run_migrations() {
    echo -e "${GREEN}Running database migrations...${NC}"
    
    # Get Cloud Run backend URL
    BACKEND_URL=$(gcloud run services describe pathvest-backend --region=$REGION --format='value(status.url)')
    
    # Trigger migration endpoint
    curl -X POST "$BACKEND_URL/api/v1/admin/run-migrations" \
        -H "Content-Type: application/json"
    
    echo -e "${GREEN}Migrations completed!${NC}"
}

# Load initial data
load_initial_data() {
    echo -e "${GREEN}Loading initial SEC data...${NC}"
    
    # Get Cloud Run backend URL
    BACKEND_URL=$(gcloud run services describe pathvest-backend --region=$REGION --format='value(status.url)')
    
    # Trigger data load endpoint
    curl -X POST "$BACKEND_URL/api/v1/admin/trigger-data-refresh" \
        -H "Content-Type: application/json"
    
    echo -e "${GREEN}Initial data load triggered!${NC}"
}

# Main deployment logic
case "$COMPONENT" in
    infrastructure)
        deploy_infrastructure
        ;;
    backend)
        deploy_backend
        ;;
    lean-worker)
        deploy_lean_worker
        ;;
    frontend)
        deploy_frontend
        ;;
    all)
        deploy_infrastructure
        sleep 10  # Wait for infrastructure to stabilize
        deploy_backend
        deploy_lean_worker
        deploy_frontend
        sleep 5
        run_migrations
        ;;
    *)
        echo -e "${RED}Error: Component must be infrastructure, backend, lean-worker, frontend, or all${NC}"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Deployment Complete!${NC}"
echo -e "${GREEN}========================================${NC}"

# Display service URLs
if [[ "$COMPONENT" == "all" ]] || [[ "$COMPONENT" == "backend" ]]; then
    BACKEND_URL=$(gcloud run services describe pathvest-backend --region=$REGION --format='value(status.url)' 2>/dev/null || echo "Not deployed")
    echo -e "Backend API: ${YELLOW}${BACKEND_URL}${NC}"
fi

if [[ "$COMPONENT" == "all" ]] || [[ "$COMPONENT" == "frontend" ]]; then
    echo -e "Frontend: ${YELLOW}https://${PROJECT_ID}.web.app${NC}"
fi

echo ""
echo -e "${GREEN}Next steps:${NC}"
echo "1. Verify services are running: gcloud run services list"
echo "2. Check logs: gcloud logging read"
echo "3. Monitor metrics: https://console.cloud.google.com/monitoring"

