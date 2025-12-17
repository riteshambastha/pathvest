## PathVest Deployment Guide

# Comprehensive GCP Deployment Guide

**Version**: 1.0  
**Last Updated**: December 15, 2024  

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Local Development Setup](#local-development-setup)
3. [GCP Infrastructure Setup](#gcp-infrastructure-setup)
4. [Production Deployment](#production-deployment)
5. [Configuration Management](#configuration-management)
6. [Monitoring & Observability](#monitoring--observability)
7. [Troubleshooting](#troubleshooting)
8. [Rollback Procedures](#rollback-procedures)

---

## Prerequisites

### Required Tools

- **Google Cloud SDK** (`gcloud` CLI) - [Install](https://cloud.google.com/sdk/docs/install)
- **Terraform** 1.0+ - [Install](https://www.terraform.io/downloads)
- **Docker** 20.10+ - [Install](https://docs.docker.com/get-docker/)
- **Docker Compose** 2.0+ - [Install](https://docs.docker.com/compose/install/)
- **Python** 3.11+ - [Install](https://www.python.org/downloads/)
- **Node.js** 18+ - [Install](https://nodejs.org/)
- **Firebase CLI** - `npm install -g firebase-tools`

### GCP Account Setup

1. Create a GCP Project
2. Enable billing
3. Set project quotas (increase if needed):
   - Cloud Run: 10 services minimum
   - BigQuery: 1 TB/month query quota
   - Cloud Build: 120 build-minutes/day (free tier)

### Required GCP APIs

The following APIs will be automatically enabled by Terraform:
- Cloud Run API
- Cloud Build API
- BigQuery API
- Cloud Storage API
- Secret Manager API
- Cloud Scheduler API
- Pub/Sub API
- MemoryStore (Redis) API
- Cloud SQL Admin API
- Compute Engine API

---

## Local Development Setup

### Quick Start

```bash
# Clone repository
git clone https://github.com/your-org/pathvest.git
cd pathvest

# Run setup script
chmod +x scripts/setup_local.sh
./scripts/setup_local.sh
```

This script will:
1. Check prerequisites
2. Create environment files
3. Install Python and Node.js dependencies
4. Start PostgreSQL and Redis containers
5. Run database migrations
6. Load mock SEC data

### Manual Setup

If you prefer manual setup:

```bash
# 1. Setup environment
cp .env.example .env
# Edit .env with your configuration

# 2. Start infrastructure
docker-compose up -d postgres redis

# 3. Backend setup
cd backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Start backend
uvicorn app.main:app --reload

# 4. Frontend setup (in new terminal)
cd frontend
npm install
npm run dev
```

### Accessing Local Services

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs (Swagger UI)
- **Alternative Docs**: http://localhost:8000/redoc (ReDoc)
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379

---

## GCP Infrastructure Setup

### Step 1: Authenticate with GCP

```bash
# Login to GCP
gcloud auth login

# Set default project
export GCP_PROJECT_ID="your-project-id"
gcloud config set project $GCP_PROJECT_ID

# Enable Application Default Credentials
gcloud auth application-default login
```

### Step 2: Create GCS Bucket for Terraform State

```bash
gsutil mb -p $GCP_PROJECT_ID -l us-central1 gs://$GCP_PROJECT_ID-terraform-state
gsutil versioning set on gs://$GCP_PROJECT_ID-terraform-state
```

### Step 3: Deploy Infrastructure with Terraform

```bash
cd terraform

# Initialize Terraform
terraform init

# Review planned changes
terraform plan -var="project_id=$GCP_PROJECT_ID" -var="environment=prod"

# Apply infrastructure
terraform apply -var="project_id=$GCP_PROJECT_ID" -var="environment=prod"
```

This creates:
- **Cloud Storage** bucket for data
- **BigQuery** datasets (sec_filings, backtest_results)
- **Cloud SQL** PostgreSQL instance (regional HA)
- **MemoryStore** Redis instance
- **VPC Network** with private subnet
- **Pub/Sub** topics and subscriptions
- **Secret Manager** secrets
- **Cloud Scheduler** jobs
- **Service Accounts** with proper IAM roles

### Step 4: Store Secrets

```bash
# Database URL
echo -n "postgresql://user:password@/pathvest?host=/cloudsql/PROJECT_ID:REGION:INSTANCE_NAME" | \
  gcloud secrets create DATABASE_URL --data-file=-

# AlphaVantage API Key
echo -n "YOUR_ALPHAVANTAGE_KEY" | \
  gcloud secrets create ALPHAVANTAGE_API_KEY --data-file=-

# Verify secrets
gcloud secrets list
```

---

## Production Deployment

### Option 1: Automated Deployment Script

```bash
# Deploy everything
chmod +x deploy.sh
./deploy.sh prod all

# Deploy specific components
./deploy.sh prod backend
./deploy.sh prod lean-worker
./deploy.sh prod frontend
```

### Option 2: Manual Deployment with Cloud Build

```bash
# Trigger Cloud Build
gcloud builds submit --config=cloudbuild.yaml

# Monitor build
gcloud builds log <BUILD_ID> --stream
```

### Option 3: Manual Component Deployment

#### Backend API

```bash
# Build Docker image
docker build -t gcr.io/$GCP_PROJECT_ID/pathvest-backend:latest -f backend/Dockerfile backend/

# Push to Container Registry
docker push gcr.io/$GCP_PROJECT_ID/pathvest-backend:latest

# Deploy to Cloud Run
gcloud run deploy pathvest-backend \
  --image gcr.io/$GCP_PROJECT_ID/pathvest-backend:latest \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --timeout 900 \
  --max-instances 10 \
  --set-env-vars ENVIRONMENT=production,GCP_PROJECT_ID=$GCP_PROJECT_ID \
  --set-secrets DATABASE_URL=DATABASE_URL:latest,ALPHAVANTAGE_API_KEY=ALPHAVANTAGE_API_KEY:latest
```

#### LEAN Worker

```bash
# Build and deploy LEAN worker
docker build -t gcr.io/$GCP_PROJECT_ID/pathvest-lean-worker:latest -f backend/lean_engine/Dockerfile backend/lean_engine/
docker push gcr.io/$GCP_PROJECT_ID/pathvest-lean-worker:latest

gcloud run deploy pathvest-lean-worker \
  --image gcr.io/$GCP_PROJECT_ID/pathvest-lean-worker:latest \
  --region us-central1 \
  --no-allow-unauthenticated \
  --memory 4Gi \
  --cpu 4 \
  --timeout 3600 \
  --max-instances 5
```

#### Frontend (Firebase Hosting)

```bash
cd frontend

# Build production bundle
npm run build

# Deploy to Firebase
firebase login
firebase init hosting  # Select existing project
firebase deploy --only hosting
```

---

## Configuration Management

### Environment Variables

Managed via:
1. **Local**: `.env` file
2. **Cloud Run**: Environment variables in deployment
3. **Sensitive**: GCP Secret Manager

### Secrets Rotation

```bash
# Rotate database password
gcloud sql users set-password postgres \
  --instance=pathvest-postgres-prod \
  --password=NEW_PASSWORD

# Update secret
echo -n "NEW_DATABASE_URL" | gcloud secrets versions add DATABASE_URL --data-file=-

# Redeploy services to pick up new secret
gcloud run services update pathvest-backend --region=us-central1
```

### Feature Flags

Managed in `app/core/config.py`:
- `ENABLE_MOCK_DATA`: Use mock data providers
- `ENABLE_VALIDATION`: Run robustness validation
- `DEBUG`: Enable debug mode

---

## Monitoring & Observability

### Cloud Monitoring Dashboards

1. Navigate to: https://console.cloud.google.com/monitoring
2. Create custom dashboard with:
   - Cloud Run request count
   - Cloud Run latency (p50, p95, p99)
   - Cloud Run error rate
   - BigQuery bytes scanned
   - MemoryStore CPU/memory usage

### Logging

```bash
# View Cloud Run logs
gcloud logging read "resource.type=cloud_run_revision" --limit 50

# View BigQuery logs
gcloud logging read "resource.type=bigquery_project" --limit 50

# Stream logs in real-time
gcloud logging tail "resource.type=cloud_run_revision"
```

### Alerting

Create alerts for:
- Cloud Run error rate > 5%
- Cloud Run latency p99 > 10s
- BigQuery query cost > $100/day
- MemoryStore memory usage > 80%

---

## Troubleshooting

### Common Issues

#### 1. Cloud Run Service Not Starting

```bash
# Check logs
gcloud run services logs read pathvest-backend --region=us-central1 --limit=50

# Common causes:
# - Missing secrets
# - Database connection failure
# - Port not exposed (must be 8000)
```

#### 2. Database Connection Timeout

```bash
# Verify Cloud SQL instance is running
gcloud sql instances list

# Check Cloud SQL proxy
gcloud sql instances describe pathvest-postgres-prod

# Test connection from Cloud Shell
gcloud sql connect pathvest-postgres-prod --user=postgres
```

#### 3. BigQuery Permission Denied

```bash
# Grant service account access
gcloud projects add-iam-policy-binding $GCP_PROJECT_ID \
  --member="serviceAccount:pathvest-backend@$GCP_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/bigquery.dataEditor"
```

#### 4. Frontend 404 Errors

```bash
# Verify Firebase Hosting deployed correctly
firebase hosting:channel:list

# Check nginx.conf for SPA fallback
# Ensure all routes serve index.html
```

---

## Rollback Procedures

### Rollback Cloud Run Service

```bash
# List revisions
gcloud run revisions list --service=pathvest-backend --region=us-central1

# Rollback to previous revision
gcloud run services update-traffic pathvest-backend \
  --region=us-central1 \
  --to-revisions=pathvest-backend-00002-abc=100
```

### Rollback Frontend

```bash
cd frontend

# List previous deployments
firebase hosting:channel:list

# Rollback to previous version
firebase hosting:rollback
```

### Rollback Infrastructure (Terraform)

```bash
cd terraform

# Revert to previous state
git checkout <previous-commit>
terraform plan -var="project_id=$GCP_PROJECT_ID"
terraform apply -var="project_id=$GCP_PROJECT_ID"
```

---

## Performance Optimization

### Backend Optimizations

1. **Redis Caching**: Market data cached for 1 hour
2. **BigQuery Materialized Views**: Pre-aggregate common queries
3. **Connection Pooling**: SQLAlchemy pool size = 20
4. **Async Endpoints**: FastAPI async for I/O-bound operations

### Frontend Optimizations

1. **Code Splitting**: Lazy load step components
2. **Image Optimization**: Serve WebP where supported
3. **CDN**: Firebase Hosting serves via global CDN
4. **Gzip Compression**: Enabled in nginx.conf

---

## Cost Optimization

### Current Monthly Cost Estimate (Production)

- **Cloud Run** (Backend + Worker): ~$50-100
- **Cloud SQL** (db-custom-2-7680, Regional HA): ~$200-250
- **MemoryStore** (Redis 5GB, Standard HA): ~$100
- **BigQuery** (1TB queries/month): ~$5
- **Cloud Storage** (100GB): ~$2
- **Cloud Build** (Free tier): $0
- **Firebase Hosting** (Free tier): $0

**Total**: ~$357-457/month

### Cost Reduction Strategies

1. Use Cloud SQL proxy instead of private IP (save ~$10/month)
2. Scale down Cloud Run to min 0 instances during off-hours
3. Use BigQuery slots reservations for predictable workloads
4. Implement data lifecycle policies (archive old backtests)

---

## Security Best Practices

1. **Secrets**: Store all sensitive data in Secret Manager
2. **IAM**: Follow principle of least privilege
3. **VPC**: Use private IPs for database and Redis
4. **SSL/TLS**: Enforce HTTPS on all endpoints
5. **API Keys**: Rotate every 90 days
6. **Audit Logs**: Enable for all services

---

## Next Steps

1. **CI/CD Pipeline**: Setup GitHub Actions for automated deployments
2. **Staging Environment**: Create staging environment for testing
3. **Load Testing**: Use Locust or JMeter for performance testing
4. **Disaster Recovery**: Setup cross-region backups
5. **Documentation**: Add API usage examples and tutorials

---

**Need Help?**  
Contact: [admin@pathvest.com](mailto:admin@pathvest.com)  
Documentation: [https://docs.pathvest.com](https://docs.pathvest.com)

