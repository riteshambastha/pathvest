# 🏗️ SEC Integration Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                          USER INTERFACE                              │
│                     http://localhost:3000                            │
│                                                                      │
│  ┌────────────────┐         ┌────────────────┐                     │
│  │  SEC Explorer  │────────▶│ Filing Detail  │                     │
│  │     Page       │         │      Page      │                     │
│  │                │         │                │                     │
│  │ • Institution  │         │ • Summary Card │                     │
│  │   dropdown     │         │ • Holdings     │                     │
│  │ • Date filters │         │   Table        │                     │
│  │ • Search btn   │         │ • Search/Sort  │                     │
│  │ • Cache badge  │         │ • Back button  │                     │
│  └────────┬───────┘         └────────────────┘                     │
│           │                                                          │
└───────────┼──────────────────────────────────────────────────────────┘
            │ HTTP/REST API
            │ Authorization: Bearer <JWT>
            ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        FASTAPI BACKEND                               │
│                     http://localhost:8000                            │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    API ENDPOINTS                              │  │
│  │                 /api/v1/sec/...                              │  │
│  │                                                                │  │
│  │  • GET  /institutions                                         │  │
│  │  • POST /institutions/seed                                    │  │
│  │  • GET  /filings/search                                       │  │
│  │  • GET  /filings/{id}                                         │  │
│  │  • GET  /filings/{id}/holdings                                │  │
│  └────────────────────────┬─────────────────────────────────────┘  │
│                            │                                         │
│                            ▼                                         │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                   SEC SERVICE                                 │  │
│  │               (Smart Caching Logic)                           │  │
│  │                                                                │  │
│  │  fetch_and_cache_filings():                                   │  │
│  │    1. Check PostgreSQL DB                                     │  │
│  │    2. If found → return cached data (0 API requests)         │  │
│  │    3. If not found → query SEC-API.io (1 API request)        │  │
│  │    4. Store in DB for future use                              │  │
│  │    5. Return data + cache indicator                           │  │
│  └────────┬───────────────────────────┬─────────────────────────┘  │
│           │                            │                             │
└───────────┼────────────────────────────┼─────────────────────────────┘
            │                            │
            │ SQLAlchemy ORM             │ HTTP Requests
            ▼                            ▼
┌─────────────────────────┐   ┌──────────────────────────┐
│   POSTGRESQL DATABASE   │   │      SEC-API.io          │
│   localhost:5432        │   │  https://api.sec-api.io  │
│                         │   │                          │
│  ┌──────────────────┐  │   │  External API Service    │
│  │  institutions    │  │   │  (paid per request)      │
│  │  • id            │  │   │                          │
│  │  • cik           │  │   │  Endpoints:              │
│  │  • name          │  │   │  • /search               │
│  │  • is_popular    │  │   │  • /13f/{accession}      │
│  └──────────────────┘  │   │                          │
│                         │   └──────────────────────────┘
│  ┌──────────────────┐  │                ▲
│  │  filings         │  │                │
│  │  • id            │  │                │ Only query if
│  │  • institution_id│  │                │ not in database
│  │  • accession_no  │  │                │ (Smart Caching)
│  │  • filed_at      │  │                │
│  │  • total_value   │  │   ┌────────────┴─────────────┐
│  │  • raw_response  │  │   │    SEC.gov (Public)      │
│  └──────────────────┘  │   │  https://www.sec.gov     │
│                         │   │                          │
│  ┌──────────────────┐  │   │  • XML filings           │
│  │  holdings        │  │   │  • Free access           │
│  │  • id            │  │   │  • Requires User-Agent   │
│  │  • filing_id     │  │   └──────────────────────────┘
│  │  • name_of_issuer│  │
│  │  • cusip         │  │
│  │  • ticker        │  │
│  │  • value         │  │
│  │  • shares        │  │
│  └──────────────────┘  │
│                         │
└─────────────────────────┘
```

## Data Flow: First Search

```
User clicks "Search Filings" for Renaissance Technologies
    │
    ├─ 1. Frontend: secService.searchFilings({ cik: "0001037389" })
    │
    ├─ 2. HTTP Request: GET /api/v1/sec/filings/search?cik=0001037389
    │
    ├─ 3. Backend: SECService.fetch_and_cache_filings(cik="0001037389")
    │
    ├─ 4. Check Database:
    │     SELECT * FROM filings WHERE institution_id = (
    │       SELECT id FROM institutions WHERE cik = '0001037389'
    │     )
    │     Result: Empty (not cached yet)
    │
    ├─ 5. Query SEC-API.io:
    │     POST https://api.sec-api.io
    │     {
    │       "query": "cik:1037389 AND formType:\"13F-HR\"",
    │       "sort": [{"filedAt": {"order": "desc"}}]
    │     }
    │     Cost: 1 API request 💸
    │
    ├─ 6. Store in Database:
    │     INSERT INTO institutions (cik, name) VALUES ('0001037389', 'Renaissance Technologies')
    │     INSERT INTO filings (institution_id, accession_no, ...) VALUES (...)
    │     [3 filings inserted]
    │
    ├─ 7. Return Response:
    │     {
    │       "total": 3,
    │       "filings": [...],
    │       "cached": false  ← Blue badge in UI
    │     }
    │
    └─ 8. Frontend displays results with blue badge:
          "↻ Data fetched from SEC-API.io and cached for future use"
```

## Data Flow: Second Search (Same Institution)

```
User clicks "Search Filings" again for Renaissance Technologies
    │
    ├─ 1. Frontend: secService.searchFilings({ cik: "0001037389" })
    │
    ├─ 2. HTTP Request: GET /api/v1/sec/filings/search?cik=0001037389
    │
    ├─ 3. Backend: SECService.fetch_and_cache_filings(cik="0001037389")
    │
    ├─ 4. Check Database:
    │     SELECT * FROM filings WHERE institution_id = (
    │       SELECT id FROM institutions WHERE cik = '0001037389'
    │     )
    │     Result: 3 filings found ✓
    │
    ├─ 5. Skip SEC-API.io:
    │     Cost: 0 API requests 🎉 (saved!)
    │
    ├─ 6. Return Response:
    │     {
    │       "total": 3,
    │       "filings": [...],
    │       "cached": true  ← Green badge in UI
    │     }
    │
    └─ 7. Frontend displays results with green badge:
          "✓ Data served from cache (API request saved)"
```

## Database Relationships

```
institutions (1) ──────< filings (many)
                         │
                         │
                         ├──────< holdings (many)
                         │
                         └──────  raw_response (JSON)

Example:
┌─────────────────────────┐
│ Renaissance Technologies│  (1 institution)
│ CIK: 0001037389         │
└───────────┬─────────────┘
            │
            ├─ Filing 1: 2024-12-05  (1 filing)
            │  └─ 1,234 holdings
            │
            ├─ Filing 2: 2024-09-05  (1 filing)
            │  └─ 1,189 holdings
            │
            └─ Filing 3: 2024-06-05  (1 filing)
               └─ 1,156 holdings
```

## Component Hierarchy

```
App.tsx
 ├─ Navbar.tsx
 │   ├─ Link: Dashboard
 │   ├─ Link: Portfolios
 │   └─ Link: SEC Explorer  ← NEW
 │
 ├─ Route: /sec
 │   └─ SECExplorerPage.tsx  ← NEW
 │       ├─ Institution Dropdown
 │       ├─ Date Range Filters
 │       ├─ Search Button
 │       ├─ Cache Badge
 │       └─ Filings Table
 │           └─ "View Details" Button
 │
 └─ Route: /sec/filings/:filingId
     └─ FilingDetailPage.tsx  ← NEW
         ├─ Filing Summary Card
         │   ├─ CIK
         │   ├─ Filed Date
         │   ├─ Total Holdings
         │   └─ Total AUM
         ├─ Search Input
         └─ Holdings Table
             ├─ Sortable Columns
             ├─ Formatted Values
             └─ Portfolio %
```

## API Request Flow

```
Frontend                Backend              Database           SEC-API.io
   │                       │                     │                  │
   ├─ searchFilings() ────▶│                     │                  │
   │                       ├─ Check cache ──────▶│                  │
   │                       │◀────── empty ───────┤                  │
   │                       │                     │                  │
   │                       ├─ Query API ─────────┼─────────────────▶│
   │                       │◀──── response ──────┼──────────────────┤
   │                       │                     │                  │
   │                       ├─ Save to DB ───────▶│                  │
   │                       │◀────── ok ──────────┤                  │
   │                       │                     │                  │
   │◀─ {cached: false} ────┤                     │                  │
   │                       │                     │                  │
   │ (User searches again) │                     │                  │
   │                       │                     │                  │
   ├─ searchFilings() ────▶│                     │                  │
   │                       ├─ Check cache ──────▶│                  │
   │                       │◀──── results ───────┤                  │
   │                       │                     │                  │
   │◀─ {cached: true} ─────┤                     │                  │
   │                       │                     │                  │
```

## Smart Caching Decision Tree

```
                    User searches for filings
                              │
                              ▼
                  ┌───────────────────────┐
                  │ Is force_refresh=true?│
                  └───────┬───────────────┘
                          │
                ┌─────────┴─────────┐
               YES                  NO
                │                    │
                ▼                    ▼
    ┌─────────────────────┐   ┌────────────────────┐
    │ Skip database cache │   │ Check database     │
    │ Query SEC-API.io    │   └────────┬───────────┘
    │ Update database     │            │
    └─────────┬───────────┘   ┌────────┴────────┐
              │              Found            Not Found
              │               │                  │
              │               ▼                  ▼
              │     ┌──────────────────┐  ┌──────────────────┐
              │     │ Return from DB   │  │ Query SEC-API.io │
              │     │ cached = true    │  │ Store in DB      │
              │     │ Cost: $0         │  │ cached = false   │
              │     └──────────────────┘  │ Cost: $X         │
              │                           └──────────────────┘
              │                                    │
              └────────────────┬───────────────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Return response     │
                    │ with cache indicator│
                    └─────────────────────┘
```

## Technology Stack

```
┌─────────────────────────────────────────────────────────────┐
│                        FRONTEND                              │
│                                                              │
│  React 18          TypeScript        Tailwind CSS           │
│  React Router      Zustand           Axios                  │
│  Lucide Icons      Vite              TanStack Query         │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ HTTP/REST
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                        BACKEND                               │
│                                                              │
│  FastAPI           Pydantic          SQLAlchemy             │
│  Uvicorn           Alembic           AsyncPG                │
│  Python-JOSE       Passlib           Bcrypt                 │
│  Requests          Python-dotenv     Httpx                  │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ SQL
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                       DATABASE                               │
│                                                              │
│  PostgreSQL 14+                                             │
│  AsyncPG Driver                                             │
│  3 Tables: institutions, filings, holdings                  │
└─────────────────────────────────────────────────────────────┘
```

## File Structure

```
pathvest/
├── backend/
│   ├── app/
│   │   ├── api/v1/endpoints/
│   │   │   └── sec.py                 ← API endpoints
│   │   ├── models/
│   │   │   ├── institution.py         ← DB model
│   │   │   ├── filing.py              ← DB model
│   │   │   └── holding.py             ← DB model
│   │   ├── schemas/
│   │   │   ├── institution.py         ← Pydantic schema
│   │   │   ├── filing.py              ← Pydantic schema
│   │   │   └── holding.py             ← Pydantic schema
│   │   ├── services/
│   │   │   └── sec_service.py         ← Smart caching logic ⭐
│   │   └── core/
│   │       └── config.py              ← SEC_API_KEY config
│   ├── alembic/versions/
│   │   └── 846c3c4d7d71_*.py          ← Migration
│   ├── test_sec_integration.py        ← Test script
│   └── .env                            ← API key here!
│
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── SECExplorerPage.tsx    ← Search UI ⭐
│   │   │   └── FilingDetailPage.tsx   ← Holdings UI ⭐
│   │   ├── services/
│   │   │   └── secService.ts          ← API client
│   │   ├── types/
│   │   │   └── sec.ts                 ← TypeScript types
│   │   ├── components/
│   │   │   └── Navbar.tsx             ← Added SEC link
│   │   └── App.tsx                    ← Registered routes
│   └── .env
│
├── README.md                           ← Quick start
├── SEC_INTEGRATION_GUIDE.md            ← Detailed guide
├── IMPLEMENTATION_SUMMARY.md           ← Feature list
├── CHECKLIST.md                        ← Next steps
└── ARCHITECTURE.md                     ← This file
```

## Security Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    User Authentication                       │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │ User logs in          │
              │ (LoginPage.tsx)       │
              └──────────┬────────────┘
                         │
                         ▼
              ┌───────────────────────┐
              │ Backend validates     │
              │ credentials           │
              └──────────┬────────────┘
                         │
                         ▼
              ┌───────────────────────┐
              │ Returns JWT token     │
              │ (access_token)        │
              └──────────┬────────────┘
                         │
                         ▼
              ┌───────────────────────┐
              │ Frontend stores token │
              │ in Zustand state      │
              └──────────┬────────────┘
                         │
                         ▼
              ┌───────────────────────┐
              │ API client adds token │
              │ to all requests:      │
              │ Authorization: Bearer │
              └──────────┬────────────┘
                         │
                         ▼
              ┌───────────────────────┐
              │ SEC endpoints require │
              │ authentication        │
              │ (get_current_user)    │
              └───────────────────────┘
```

## Performance Metrics

### Without Caching
```
Request 1: 1500ms (API call)
Request 2: 1500ms (API call)
Request 3: 1500ms (API call)
Request 4: 1500ms (API call)
Request 5: 1500ms (API call)
───────────────────────────
Total:     7500ms
API Calls: 5
Cost:      5 × $X
```

### With Caching (This Implementation)
```
Request 1: 1500ms (API call → cache)
Request 2:   20ms (from cache)
Request 3:   20ms (from cache)
Request 4:   20ms (from cache)
Request 5:   20ms (from cache)
───────────────────────────
Total:     1580ms (79% faster)
API Calls: 1
Cost:      1 × $X (80% savings)
```

---

**This architecture provides a scalable, efficient, and cost-effective solution for exploring SEC 13F-HR filings!** 🚀

