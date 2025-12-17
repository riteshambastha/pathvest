# 🚀 Deploy Pathvest TODAY - Quick Checklist

**Time to Complete**: ~30 minutes
**Cost**: $14/month (or Free for 90 days)

---

## ✅ Pre-Flight Check

- [x] Code pushed to GitHub ✅
- [ ] Have these API keys ready:
  - AlphaVantage API Key
  - SEC API Key  
  - OpenFIGI API Key
- [ ] Render account (sign up: https://render.com)
- [ ] Vercel account (sign up: https://vercel.com)

---

## 📦 PART 1: Database Setup (5 min)

### On Render:

1. Go to https://dashboard.render.com
2. Click **"New +"** → **"PostgreSQL"**
3. Configure:
   - Name: `pathvest-db`
   - Region: `Oregon (US West)`
   - Plan: `Starter ($7/month)` or `Free` for testing
4. Click **"Create Database"**
5. **COPY** the **Internal Database URL** → You'll need this!

```
postgresql://pathvest_user:PASSWORD@HOST:5432/pathvest
```

---

## 🔧 PART 2: Backend Setup (10 min)

### On Render:

1. Click **"New +"** → **"Web Service"**
2. Connect GitHub → Select **"pathvest"** repo
3. Configure:

```
Name: pathvest-backend
Region: Oregon (US West)
Branch: main
Root Directory: backend
Runtime: Python 3
Build Command: pip install -r requirements.txt
Start Command: uvicorn app.main:app --host 0.0.0.0 --port $PORT
Plan: Starter ($7/month) or Free
```

4. **Environment Variables** (click Advanced):

```bash
DATABASE_URL=<paste-internal-database-url>
ALPHA_VANTAGE_API_KEY=<your-key>
SEC_API_KEY=<your-key>
OPENFIGI_API_KEY=<your-key>
SECRET_KEY=change_this_to_something_random_and_long
DEBUG=False
CORS_ORIGINS=http://localhost:5173
```

5. Click **"Create Web Service"**
6. Wait 2-3 minutes for deployment
7. **SAVE** your backend URL:
   ```
   https://pathvest-backend.onrender.com
   ```

8. **Verify**: Visit `https://pathvest-backend.onrender.com/docs`
   - Should see Swagger API docs ✅

---

## 🎨 PART 3: Frontend Setup (5 min)

### On Vercel:

1. Go to https://vercel.com/new
2. Click **"Add New..."** → **"Project"**
3. Select **"pathvest"** repository
4. Configure:

```
Project Name: pathvest
Framework: Vite
Root Directory: frontend
Build Command: npm run build
Output Directory: dist
```

5. **Environment Variables**:

```
VITE_API_BASE_URL=https://pathvest-backend.onrender.com
VITE_ENABLE_LEAN_ENGINE=true
```

6. Click **"Deploy"**
7. Wait 1-2 minutes
8. **SAVE** your frontend URL:
   ```
   https://pathvest.vercel.app
   ```

---

## 🔗 PART 4: Connect Frontend & Backend (2 min)

### Update Backend CORS:

1. Go back to Render → Your backend service
2. Go to **"Environment"** tab
3. Update `CORS_ORIGINS`:
   ```
   CORS_ORIGINS=https://pathvest.vercel.app,https://pathvest-*.vercel.app
   ```
4. Click **"Save Changes"**
5. Backend will auto-redeploy (1-2 min)

---

## 🗄️ PART 5: Database Migrations (3 min)

### Option A: From Backend Shell (Render)

1. Go to backend service → **"Shell"** tab
2. Run:
   ```bash
   python -m alembic upgrade head
   ```

### Option B: Update Build Command

1. Go to **"Settings"** → **"Build & Deploy"**
2. Update Build Command to:
   ```bash
   pip install -r requirements.txt && python -m alembic upgrade head
   ```
3. Click **"Save Changes"**
4. Click **"Manual Deploy"** → **"Clear build cache & deploy"**

---

## 🧪 PART 6: Test Everything (5 min)

### 1. Test Backend

Visit: `https://pathvest-backend.onrender.com/docs`

- [ ] API docs load
- [ ] Try `/health` endpoint
- [ ] Check `/api/v1/institutions` (might be empty, that's OK)

### 2. Test Frontend

Visit: `https://pathvest.vercel.app`

- [ ] Homepage loads
- [ ] Navigate to Strategy Builder
- [ ] Open browser console (F12) → Check for errors
- [ ] No CORS errors

### 3. Test Integration

1. Go to Strategy Builder
2. Try Step 1: Setup
3. Check if it connects to backend

---

## 🎉 YOU'RE LIVE!

Your Pathvest platform is deployed!

**Your URLs:**
- 🎨 Frontend: https://pathvest.vercel.app
- 🔧 Backend: https://pathvest-backend.onrender.com
- 📚 API Docs: https://pathvest-backend.onrender.com/docs

---

## ⚠️ Troubleshooting

### Backend Shows "Service Unavailable"

**Check Logs:**
1. Go to backend dashboard → **"Logs"** tab
2. Look for errors

**Common Fixes:**
- Missing environment variable
- Database connection failed (check DATABASE_URL)
- Wrong Start Command

### Frontend Shows Blank Page

**Check Browser Console (F12):**
- Look for red errors

**Common Fixes:**
- Wrong VITE_API_BASE_URL
- CORS error (update backend CORS_ORIGINS)

### Can't Connect to Database

**Check:**
- Using **Internal Database URL** (not External)
- Database is running (check Render dashboard)
- DATABASE_URL has no spaces or extra characters

---

## 💰 Current Cost

### Free Tier (90 days)
- Database: Free for 90 days
- Backend: Free (with cold starts)
- Frontend: Free
- **Total: $0/month**

### Production (Recommended)
- Database: $7/month
- Backend: $7/month  
- Frontend: Free
- **Total: $14/month**

---

## 📋 Post-Deployment Tasks

### Today:
- [ ] Add institutional data (use backend shell or create endpoint)
- [ ] Test backtesting with real data
- [ ] Create your first strategy

### This Week:
- [ ] Set up custom domain (optional)
- [ ] Enable monitoring/alerts
- [ ] Add more institutional data
- [ ] Share with friends!

### This Month:
- [ ] Optimize performance
- [ ] Add more features
- [ ] Consider upgrading plans if needed

---

## 🔒 Security Notes

1. **Change SECRET_KEY** to a strong random value:
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

2. **Rotate API keys** every 90 days

3. **Enable 2FA** on Render and Vercel accounts

4. **Monitor logs** regularly for suspicious activity

---

## 📞 Need Help?

1. Check `RENDER_VERCEL_DEPLOYMENT.md` for detailed guide
2. Check backend logs on Render
3. Check browser console for frontend errors
4. Create GitHub issue if stuck

---

## 🎯 What's Next?

1. **Add Data**: Import institutional holdings
2. **Test Backtests**: Run a test strategy
3. **Customize**: Update branding, colors, etc.
4. **Share**: Show it to friends and get feedback!
5. **Iterate**: Keep improving!

---

**🚀 Ready to deploy? Start with PART 1!**

Time estimate: 30 minutes from start to finish.

You got this! 💪

