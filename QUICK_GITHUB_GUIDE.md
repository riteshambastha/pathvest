# 🚀 Quick GitHub Setup Guide

## One-Command Cleanup

```bash
cd /Users/riteshambastha/projects/pathvest
./cleanup_for_github.sh
```

## Git Push Commands

```bash
# 1. Check git status
git status

# 2. Add all files
git add .

# 3. Verify no sensitive files
git ls-files | grep -E '\.env$|credentials|\.log$|\.db$'

# 4. Commit
git commit -m "Initial commit: Pathvest algorithmic trading platform"

# 5. Add remote (replace with your URL)
git remote add origin https://github.com/YOUR_USERNAME/pathvest.git

# 6. Push
git push -u origin main
```

## Post-Push Checklist

- [ ] Add repository description
- [ ] Add topics: `algorithmic-trading`, `python`, `react`, `typescript`, `fastapi`
- [ ] Enable Issues
- [ ] Enable Discussions
- [ ] Set up branch protection on `main`
- [ ] Review and customize README.md on GitHub
- [ ] Add social preview image (optional)

## Files That Will Be Committed

✅ **Source Code**
- `frontend/src/` (all React components)
- `backend/app/` (all Python modules)
- `backend/requirements.txt`
- `frontend/package.json`

✅ **Configuration**
- `.gitignore`
- `.env.example` (both frontend and backend)
- `docker-compose.yml`
- `terraform/` (infrastructure)

✅ **Documentation**
- `README.md`
- `LICENSE`
- `ARCHITECTURE.md`
- `DEPLOYMENT_GUIDE.md`
- `USER_GUIDE.md`
- `TESTING_GUIDE.md`

## Files That Will NOT Be Committed

❌ **Sensitive Data**
- `.env` (actual environment variables)
- `gcp-credentials.json`
- Any `*credentials*.json`

❌ **Generated Data**
- `*.db` (database files)
- `*.log` (log files)
- `*.csv` (data exports)
- `*_holdings.json`, `*_filings.json`

❌ **Dependencies**
- `venv/`, `venv-lean/`
- `node_modules/`
- `__pycache__/`

❌ **Temporary Files**
- `*.bak`, `*.backup`, `*.old`
- Development documentation (PHASE*.md, etc.)
- Test scripts (test_*.py, fetch_*.py, etc.)

## Security Checks

```bash
# Check for hardcoded API keys
grep -r "API_KEY.*=" --exclude-dir=venv --exclude-dir=node_modules --exclude="*.md" . | grep -v "example"

# Check for passwords
grep -r "password" --exclude-dir=venv --exclude-dir=node_modules -i . | grep -v "example"

# Check for credentials
find . -name "*credential*" -type f | grep -v "example"
```

## Environment Variables Needed

### Backend `.env`
```
DATABASE_URL=postgresql://user:pass@localhost:5432/pathvest
ALPHA_VANTAGE_API_KEY=your_key
SEC_API_KEY=your_key
OPENFIGI_API_KEY=your_key
SECRET_KEY=your_secret
```

### Frontend `.env`
```
VITE_API_BASE_URL=http://localhost:8000
```

## Help

- Full details: See `GITHUB_PREP_CHECKLIST.md`
- Comprehensive docs: See `README.md`
- Any questions: Review the checklist before pushing

---

**Ready to push? Run `./cleanup_for_github.sh` first!** 🎯

