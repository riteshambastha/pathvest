"""
FastAPI Application Entry Point
"""

# Load environment variables FIRST before any other imports
from dotenv import load_dotenv
import os
load_dotenv()
print("🚀🚀🚀 MAIN.PY LOADED - DOTENV LOADED 🚀🚀🚀")
print(f"🔧 ALPHAVANTAGE_API_KEY: {os.getenv('ALPHAVANTAGE_API_KEY', 'NOT_SET')[:10]}...")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1.api import api_router


def create_application() -> FastAPI:
    """Create and configure FastAPI application"""
    
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
        docs_url=f"{settings.API_V1_PREFIX}/docs",
        redoc_url=f"{settings.API_V1_PREFIX}/redoc",
    )
    
    # Configure CORS - include common localhost ports for development
    cors_origins = [str(origin) for origin in settings.BACKEND_CORS_ORIGINS]
    # Always allow common localhost ports for local development
    localhost_ports = [
        "http://localhost:3000",
        "http://localhost:3001", 
        "http://localhost:3002",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "http://127.0.0.1:3002",
    ]
    for port in localhost_ports:
        if port not in cors_origins:
            cors_origins.append(port)
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include API router
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)
    
    @app.get("/")
    async def root():
        """Root endpoint"""
        return {
            "message": f"Welcome to {settings.APP_NAME}",
            "version": settings.APP_VERSION,
            "docs": f"{settings.API_V1_PREFIX}/docs"
        }
    
    return app


app = create_application()

