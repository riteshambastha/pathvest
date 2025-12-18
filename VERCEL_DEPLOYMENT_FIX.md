# Vercel Deployment Fix - CORS & Environment Variables

## 🔴 Problem

**Error**: `Unexpected token '<', "<!doctype "... is not valid JSON`

**Root Causes**:
1. Frontend doesn't have backend URL configured
2. Backend CORS doesn't allow Vercel domain

---

## ✅ Solution (3 Steps)

### Step 1: Configure Vercel Environment Variables

Go to your Vercel project dashboard:

1. **Vercel Dashboard** → Your Project → **Settings** → **Environment Variables**

2. Add this variable:
   - **Name**: `VITE_API_BASE_URL`
   - **Value**: `https://pathvest-backend.onrender.com/api/v1`
   - **Environment**: Production, Preview, Development (check all)

3. Click **Save**

### Step 2: Get Your Vercel URL

Your Vercel app URL is something like:
- `https://pathvest.vercel.app` OR
- `https://your-project-name.vercel.app`

**Find it**: Vercel Dashboard → Your Project → **Domains** tab

Copy this URL!

### Step 3: Update Backend CORS on Render

**Option A: Via Render Dashboard (Quick)**

1. Go to **Render Dashboard** → `pathvest-backend` → **Environment**
2. Add/update this variable:
   - **Key**: `BACKEND_CORS_ORIGINS`
   - **Value**: `["http://localhost:3000","https://YOUR-VERCEL-URL.vercel.app"]`
   
   Replace `YOUR-VERCEL-URL` with your actual Vercel URL!

3. Click **Save Changes**
4. Render will auto-redeploy (~2 minutes)

**Option B: Via Code (Permanent)**

Update `backend/app/core/config.py` (already done locally):

```python
BACKEND_CORS_ORIGINS: List[str] = [
    "http://localhost:3000",
    "https://pathvest.vercel.app",  # Your Vercel URL
]
```

Then:
```bash
git add backend/app/core/config.py frontend/.env.production
git commit -m "Add CORS for Vercel and production env vars"
git push origin main
```

### Step 4: Redeploy Frontend on Vercel

After setting environment variables:

```bash
cd frontend
vercel --prod
```

Or trigger redeploy from Vercel Dashboard:
- **Deployments** tab → **...** menu → **Redeploy**

---

## 🧪 Test It Works

Once both are redeployed:

1. **Open your Vercel frontend URL**
2. **Open browser console** (F12 → Console tab)
3. **Try to load data** (e.g., view institutions)
4. **Should work!** No more JSON parsing errors

### Manual Test

Open in browser:
```
https://pathvest-backend.onrender.com/api/v1/institutions/sec/list
```

Should return JSON (not HTML).

From frontend console, check:
```javascript
console.log(import.meta.env.VITE_API_BASE_URL)
// Should show: https://pathvest-backend.onrender.com/api/v1
```

---

## 🔍 How to Debug

### Check Frontend is Using Correct URL

In browser console:
```javascript
// Check environment variable
console.log(import.meta.env.VITE_API_BASE_URL)

// Check what axios is using
import apiClient from './services/api'
console.log(apiClient.defaults.baseURL)
```

### Check Backend CORS Settings

Test with curl:
```bash
curl -H "Origin: https://your-app.vercel.app" \
     -H "Access-Control-Request-Method: GET" \
     -H "Access-Control-Request-Headers: Content-Type" \
     -X OPTIONS \
     https://pathvest-backend.onrender.com/api/v1/institutions/sec/list
```

Should return CORS headers like:
```
access-control-allow-origin: https://your-app.vercel.app
```

### Check Vercel Environment Variables

In Vercel Dashboard:
1. Go to **Settings** → **Environment Variables**
2. Verify `VITE_API_BASE_URL` is set correctly
3. Make sure it's enabled for **Production**

---

## 📋 Checklist

Before testing:

- [ ] `.env.production` file created locally (already done ✅)
- [ ] Vercel environment variable `VITE_API_BASE_URL` set
- [ ] Render environment variable `BACKEND_CORS_ORIGINS` includes Vercel URL
- [ ] Backend redeployed on Render (auto after env var change)
- [ ] Frontend redeployed on Vercel
- [ ] Browser cache cleared (Ctrl+Shift+R or Cmd+Shift+R)

---

## 🎯 Expected Result

After fixes:

✅ Frontend loads without errors  
✅ Console shows no CORS errors  
✅ Console shows no JSON parsing errors  
✅ API calls return data successfully  
✅ You can register/login/use the app  

---

## 🆘 Still Not Working?

### Error: Still getting HTML instead of JSON

**Check**: Is the API endpoint correct?

```bash
# This should work (returns JSON)
curl https://pathvest-backend.onrender.com/api/v1/institutions/sec/list

# This returns HTML (wrong URL)
curl https://pathvest-backend.onrender.com/institutions/sec/list
```

**Fix**: Make sure `VITE_API_BASE_URL` includes `/api/v1`

### Error: CORS policy blocked

**Check**: Did you add your Vercel URL to CORS origins?

**Fix**: Update `BACKEND_CORS_ORIGINS` on Render with your exact Vercel URL (including `https://`)

### Error: Environment variable not working on Vercel

**Fix**: 
1. Redeploy after setting env vars
2. Make sure env var is for "Production" environment
3. Try clearing Vercel build cache

---

## 📝 Quick Reference

**Your URLs**:
- Backend: `https://pathvest-backend.onrender.com`
- Frontend: `https://your-app.vercel.app` (replace with yours)

**Environment Variables**:

**Vercel**:
```
VITE_API_BASE_URL=https://pathvest-backend.onrender.com/api/v1
```

**Render**:
```
BACKEND_CORS_ORIGINS=["http://localhost:3000","https://your-app.vercel.app"]
```

---

**After following these steps, your Vercel frontend should work perfectly!** 🎉

