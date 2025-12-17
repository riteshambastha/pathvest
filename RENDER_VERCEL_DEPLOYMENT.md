# 🚀 Pathvest Deployment Guide - Render + Vercel

**Deploy your algorithmic trading platform in under 30 minutes!**

---

## 📋 Deployment Overview

- **Backend (FastAPI)**: Render Web Service
- **Database**: Render PostgreSQL
- **Frontend (React)**: Vercel
- **Cost**: ~$7-20/month (Render Starter + PostgreSQL)

---

## 🎯 Pre-Deployment Checklist

- [x] Code pushed to GitHub
- [ ] Render account created (free at https://render.com)
- [ ] Vercel account created (free at https://vercel.com)
- [ ] API keys ready (AlphaVantage, SEC API, OpenFIGI)

---

## 🗄️ Part 1: Deploy Database on Render (5 minutes)

### Step 1: Create PostgreSQL Database

1. Go to https://dashboard.render.com
2. Click **"New +"** → **"PostgreSQL"**

3. Configure:
   ```
   Name: pathvest-db
   Database: pathvest
   User: pathvest_user
   Region: Oregon (US West) or nearest to you
   PostgreSQL Version: 16
   Plan: Starter ($7/month) or Free (90 days)
   ```

4. Click **"Create Database"**

5. **SAVE THESE** (you'll need them):
   - **Internal Database URL** (for backend)
   - **External Database URL** (for local access)
   
   Format: `postgresql://user:password@host:port/database`

### Step 2: Initialize Database Schema

**Option A: Using Render Shell (Recommended)**

1. In your database dashboard, click **"Connect"** → **"PSQL Command"**
2. Copy the connection command
3. Run locally:
   ```bash
   # Install psql if needed (Mac)
   brew install postgresql

   # Connect to Render database
   psql postgresql://pathvest_user:PASSWORD@HOST/pathvest

   # You'll be connected to the database
   # Now run migrations (we'll set this up)
   ```

**Option B: We'll run migrations from the backend after deployment**

---

## 🔧 Part 2: Deploy Backend on Render (10 minutes)

### Step 1: Create Web Service

1. On Render dashboard, click **"New +"** → **"Web Service"**

2. Connect your GitHub repository:
   - Click **"Connect account"** → Authorize GitHub
   - Select **"pathvest"** repository

3. Configure:
   ```
   Name: pathvest-backend
   Region: Oregon (US West) - same as database
   Branch: main
   Root Directory: backend
   Runtime: Python 3
   Build Command: pip install -r requirements.txt
   Start Command: uvicorn app.main:app --host 0.0.0.0 --port $PORT
   Plan: Starter ($7/month) or Free
   ```

### Step 2: Add Environment Variables

Click **"Advanced"** → **"Add Environment Variable"**

Add these (one by one):

```bash
# Database
DATABASE_URL=<paste-internal-database-url-from-step-1>

# API Keys
ALPHA_VANTAGE_API_KEY=your_alphavantage_key
SEC_API_KEY=your_sec_api_key
OPENFIGI_API_KEY=your_openfigi_key

# Application
SECRET_KEY=your_secret_key_here_change_this
DEBUG=False
ALLOWED_HOSTS=*
ENVIRONMENT=production

# CORS (we'll update this after Vercel deployment)
CORS_ORIGINS=http://localhost:5173,https://pathvest.vercel.app

# Optional - GCP (if you want BigQuery)
GCP_PROJECT_ID=
GOOGLE_APPLICATION_CREDENTIALS=
```

### Step 3: Deploy

1. Click **"Create Web Service"**
2. Wait for deployment (2-3 minutes)
3. Once deployed, you'll see a URL like:
   ```
   https://pathvest-backend.onrender.com
   ```
4. **SAVE THIS URL** - you'll need it for frontend

### Step 4: Verify Backend is Running

Visit: `https://pathvest-backend.onrender.com/docs`

You should see the FastAPI Swagger documentation! ✅

### Step 5: Run Database Migrations

**Option A: Using Render Shell**

1. In your backend service dashboard, click **"Shell"**
2. Run:
   ```bash
   cd /opt/render/project/src/backend
   python -m alembic upgrade head
   ```

**Option B: Add to Build Command**

Update Build Command to:
```bash
pip install -r requirements.txt && python -m alembic upgrade head
```

Then **"Manual Deploy"** → **"Clear build cache & deploy"**

---

## 🎨 Part 3: Deploy Frontend on Vercel (5 minutes)

### Step 1: Prepare Frontend

1. Create `vercel.json` in frontend directory:

```json
{
  "buildCommand": "npm run build",
  "outputDirectory": "dist",
  "devCommand": "npm run dev",
  "installCommand": "npm install",
  "framework": "vite",
  "rewrites": [
    {
      "source": "/(.*)",
      "destination": "/index.html"
    }
  ]
}
```

2. Update frontend `.env.production` (create if doesn't exist):

```bash
VITE_API_BASE_URL=https://pathvest-backend.onrender.com
```

### Step 2: Deploy to Vercel

1. Go to https://vercel.com/new

2. **Import Git Repository**:
   - Click **"Add New..."** → **"Project"**
   - Select **"pathvest"** repository
   - Click **"Import"**

3. Configure:
   ```
   Project Name: pathvest
   Framework Preset: Vite
   Root Directory: frontend
   Build Command: npm run build
   Output Directory: dist
   Install Command: npm install
   ```

4. **Environment Variables** (click "Add"):
   ```
   VITE_API_BASE_URL=https://pathvest-backend.onrender.com
   VITE_ENABLE_LEAN_ENGINE=true
   ```

5. Click **"Deploy"**

6. Wait for deployment (1-2 minutes)

7. You'll get a URL like:
   ```
   https://pathvest.vercel.app
   ```

### Step 3: Update Backend CORS

1. Go back to Render backend dashboard
2. Update `CORS_ORIGINS` environment variable:
   ```
   CORS_ORIGINS=https://pathvest.vercel.app,https://pathvest-*.vercel.app
   ```
3. Click **"Save Changes"** (backend will auto-redeploy)

---

## ✅ Part 4: Post-Deployment Setup

### 1. Test the Deployment

Visit your Vercel URL: `https://pathvest.vercel.app`

Try:
- [ ] Homepage loads
- [ ] Navigate to Strategy Builder
- [ ] Check if backend API connects (open browser console)
- [ ] Try creating a test strategy

### 2. Populate Database with Initial Data

You need to add some institutional data for the app to work.

**Option A: Via Backend Shell (Render)**

1. Go to backend dashboard → **"Shell"**
2. Run:
   ```bash
   cd /opt/render/project/src/backend
   python
   ```
3. In Python shell:
   ```python
   from app.services.postgres_service import PostgresService
   from app.db.models import Institution, IndexConstituent
   
   ps = PostgresService()
   
   # Add some institutions
   institutions = [
       {"cik": "0001037389", "name": "RENAISSANCE TECHNOLOGIES LLC"},
       {"cik": "0001067983", "name": "BERKSHIRE HATHAWAY INC"},
       {"cik": "0001364742", "name": "SOROS FUND MANAGEMENT LLC"},
   ]
   
   for inst in institutions:
       ps.insert_institution(inst["cik"], inst["name"])
   
   print("✅ Institutions added!")
   ```

**Option B: Create a Data Import Endpoint**

We can add a secure endpoint to import initial data if needed.

### 3. Set Up Custom Domain (Optional)

**For Frontend (Vercel):**
1. Go to Project Settings → **"Domains"**
2. Add your custom domain (e.g., `pathvest.com`)
3. Follow DNS configuration instructions

**For Backend (Render):**
1. Go to Service Settings → **"Custom Domains"**
2. Add your API domain (e.g., `api.pathvest.com`)
3. Configure DNS

### 4. Enable Auto-Deploy

Both Render and Vercel automatically deploy on git push:
- **Render**: Deploys backend on push to `main` branch
- **Vercel**: Deploys frontend on push to `main` branch

---

## 💰 Cost Breakdown

### Free Tier (Limited)
- **Render Database**: Free for 90 days (1GB, sleeps after 15 min)
- **Render Web Service**: Free (sleeps after 15 min, 750 hours/month)
- **Vercel**: Free (100GB bandwidth, unlimited deployments)
- **Total**: $0/month

### Paid Plan (Recommended for Production)
- **Render PostgreSQL Starter**: $7/month (10GB, no sleep)
- **Render Web Service Starter**: $7/month (512MB RAM, no sleep)
- **Vercel Pro** (optional): $20/month (1TB bandwidth, priority support)
- **Total**: $14-34/month

---

## 🔍 Monitoring & Logs

### Backend Logs (Render)
1. Go to backend dashboard
2. Click **"Logs"** tab
3. See real-time logs

### Frontend Logs (Vercel)
1. Go to project dashboard
2. Click **"Deployments"** → Select deployment → **"View Function Logs"**

---

## 🐛 Troubleshooting

### Backend Not Starting

**Check logs on Render:**
```bash
# Common issues:
1. Missing environment variables
2. Database connection failed
3. Python dependencies missing
```

**Solutions:**
1. Verify all environment variables are set
2. Check DATABASE_URL is the Internal Database URL
3. Ensure requirements.txt is complete

### Frontend Can't Connect to Backend

**Check browser console:**
```
Error: Network request failed
```

**Solutions:**
1. Verify VITE_API_BASE_URL is correct
2. Check CORS_ORIGINS includes Vercel domain
3. Test backend directly: `https://pathvest-backend.onrender.com/docs`

### Database Connection Timeout

**Error:** `Could not connect to PostgreSQL`

**Solutions:**
1. Check DATABASE_URL is correct
2. Verify database is running (check Render dashboard)
3. Use Internal Database URL (not External)

### Cold Start (Service Sleeping)

**Issue:** First request takes 30-60 seconds

**Solutions:**
1. Upgrade to Starter plan ($7/month) - no sleeping
2. Use keep-alive service (UptimeRobot, free)
3. Accept cold starts for free tier

---

## 🔐 Security Checklist

- [x] Database not publicly accessible (using Internal URL)
- [ ] Change SECRET_KEY to strong random value
- [ ] Rotate API keys every 90 days
- [ ] Enable 2FA on Render and Vercel accounts
- [ ] Review access logs regularly
- [ ] Set up Sentry or error tracking (optional)

---

## 📊 Performance Optimization

### Backend (Render)

1. **Upgrade Plan**: Starter → Standard for more RAM
2. **Add Redis**: Render Redis for caching (optional, $10/month)
3. **Database Optimization**: 
   - Add indexes on frequently queried columns
   - Use connection pooling (already implemented)

### Frontend (Vercel)

1. **Enable Analytics**: Vercel Analytics (free)
2. **Optimize Images**: Use Vercel Image Optimization
3. **Caching**: Already optimized by Vite

---

## 🔄 CI/CD Pipeline (Already Set Up!)

Both platforms auto-deploy on git push:

```bash
# Make changes
git add .
git commit -m "Update feature"
git push origin main

# Automatic deployments:
# ✅ Render: Backend deploys in 2-3 minutes
# ✅ Vercel: Frontend deploys in 1-2 minutes
```

---

## 📞 Quick Command Reference

```bash
# Connect to production database (from local)
psql <EXTERNAL_DATABASE_URL>

# Run migrations manually
cd backend
python -m alembic upgrade head

# Check backend health
curl https://pathvest-backend.onrender.com/health

# View real-time logs (Render CLI)
pip install render-cli
render logs pathvest-backend --tail
```

---

## 🎉 Deployment Complete!

Your Pathvest platform is now live!

**URLs:**
- **Frontend**: https://pathvest.vercel.app
- **Backend API**: https://pathvest-backend.onrender.com
- **API Docs**: https://pathvest-backend.onrender.com/docs

**Next Steps:**
1. Test all features thoroughly
2. Import institutional data
3. Run your first backtest
4. Share with users!

---

## 📚 Additional Resources

- **Render Docs**: https://render.com/docs
- **Vercel Docs**: https://vercel.com/docs
- **PostgreSQL Guide**: https://render.com/docs/databases
- **Custom Domains**: https://vercel.com/docs/custom-domains

---

**Need Help?** Check the troubleshooting section or create an issue on GitHub!

**Happy Trading! 🚀📈**

