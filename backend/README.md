# Pathvest Backend (FastAPI)

A scalable, production-ready FastAPI backend for the Pathvest equity backtesting platform.

## 🏗️ Architecture

### Core Structure
```
backend/
├── app/
│   ├── api/v1/          # API endpoints
│   │   └── endpoints/   # Route handlers
│   ├── core/            # Core configuration
│   ├── db/              # Database setup
│   ├── models/          # SQLAlchemy models
│   ├── schemas/         # Pydantic schemas
│   ├── services/        # Business logic
│   └── utils/           # Utility functions
├── tests/               # Test suite
└── requirements.txt     # Dependencies
```

## 🚀 Quick Start

### 1. Create Virtual Environment
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Environment
```bash
cp .env.example .env
# Edit .env with your configuration
```

### 4. Run Development Server
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 📚 API Documentation

Once the server is running, visit:
- **Swagger UI**: http://localhost:8000/api/v1/docs
- **ReDoc**: http://localhost:8000/api/v1/redoc

## 🔐 Authentication

The API uses JWT Bearer token authentication:

1. Register: `POST /api/v1/auth/register`
2. Login: `POST /api/v1/auth/login` (returns access_token)
3. Use token in headers: `Authorization: Bearer {access_token}`

## 📊 API Endpoints

### Health Check
- `GET /api/v1/health` - Health check

### Authentication
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - Login user
- `GET /api/v1/auth/me` - Get current user

### Portfolios
- `GET /api/v1/portfolios/` - List user portfolios
- `POST /api/v1/portfolios/` - Create portfolio
- `GET /api/v1/portfolios/{id}` - Get portfolio details
- `PUT /api/v1/portfolios/{id}` - Update portfolio
- `DELETE /api/v1/portfolios/{id}` - Delete portfolio

## 🗄️ Database

The application uses PostgreSQL with SQLAlchemy (async).

### Setup Database
```bash
# Create database
createdb pathvest

# Update DATABASE_URL in .env
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/pathvest
```

### Run Migrations
```bash
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head
```

## 🧪 Testing

```bash
pytest
```

## 📦 Key Dependencies

- **FastAPI**: Modern web framework
- **SQLAlchemy**: ORM with async support
- **Pydantic**: Data validation
- **python-jose**: JWT handling
- **passlib**: Password hashing
- **uvicorn**: ASGI server

## 🔧 Configuration

All configuration is managed through environment variables (see `.env.example`):

- `DATABASE_URL`: PostgreSQL connection string
- `SECRET_KEY`: JWT secret key
- `BACKEND_CORS_ORIGINS`: Allowed origins for CORS
- `SEC_API_KEY`: SEC-API.io API key

## 🌐 CORS

CORS is configured to allow requests from specified origins (frontend URLs).
Update `BACKEND_CORS_ORIGINS` in `.env` to add more origins.

## 📝 Code Style

- Follow PEP 8 guidelines
- Use type hints
- Document functions and classes
- Keep business logic in services

## 🏭 Production Deployment

```bash
# Using Gunicorn with Uvicorn workers
gunicorn app.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

## 📄 License

MIT

