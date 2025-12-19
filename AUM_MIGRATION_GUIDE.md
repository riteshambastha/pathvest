# AUM Migration Guide

## What Changed
Added `aum` (Assets Under Management) field to institutions table with realistic values for major hedge funds and investment firms.

## Steps to Apply on Render

1. **Open Render Shell** for your backend service

2. **Run the migration:**
   ```bash
   alembic upgrade head
   ```

3. **Verify the migration:**
   ```bash
   psql $DATABASE_URL -c "SELECT name, aum FROM institutions WHERE aum IS NOT NULL LIMIT 5;"
   ```

## Expected Output
You should see AUM values like:
- Berkshire Hathaway: $350B
- Bridgewater: $125B
- Citadel: $50B
- Renaissance Technologies: $130B
- etc.

## Frontend Changes
The institutions list will now display:
- Popular badge (if applicable)
- AUM in billions (e.g., "AUM: $350.0B")
- CIK number

## After Migration
Redeploy frontend on Vercel:
```bash
cd frontend
vercel --prod --yes
```

---

*Migration File:* `backend/alembic/versions/a1b2c3d4e5f6_add_aum_to_institutions.py`

