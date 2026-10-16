"""
JanSetu AI — FastAPI Application Entrypoint.

Civic Incident Multi-Agent Orchestration Engine.

Exposes REST APIs for:
- Health checks and configuration validation
- Dashboard metric aggregation
- Incident intake with optional photographic evidence
- LangGraph workflow execution with deterministic closure verification
- Seeded failure scenario control
- Execution traces and audit trails
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.health import router as health_router
from app.api.routes.incidents import router as incidents_router
from app.api.routes.ml import router as ml_router
from app.config import settings
from app.db.session import init_db

# Configure application-wide logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("jansetu.main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application startup and shutdown lifecycle management."""
    logger.info("Starting JanSetu AI backend in '%s' environment...", settings.ENVIRONMENT)
    settings.ensure_directories()
    # Initialize database tables non-destructively
    init_db()
    yield
    logger.info("Shutting down JanSetu AI backend.")


app = FastAPI(
    title="JanSetu AI API",
    description="Multi-Agent Civic Incident Triage, Planning, and Adaptive Recovery Platform",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ============================================================================
# CORS Middleware Configuration
# ============================================================================

logger.info("Configuring CORS with permitted origins: %s", settings.cors_origins)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# ============================================================================
# Global Safe Exception Handlers
# ============================================================================

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle request validation errors cleanly without leaking internals."""
    errors = exc.errors()
    simplified_errors = []
    for err in errors:
        loc = " -> ".join(str(item) for item in err.get("loc", []))
        msg = err.get("msg", "Invalid value")
        simplified_errors.append(f"{loc}: {msg}")

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation Error",
            "detail": "; ".join(simplified_errors),
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle explicit HTTP exceptions uniformly."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "HTTP Error",
            "detail": exc.detail,
        },
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch unhandled errors, log securely, and return safe generic message."""
    logger.error("Unhandled internal server error: %s", str(exc), exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal Server Error",
            "detail": "An unexpected error occurred while processing the request.",
        },
    )

# ============================================================================
# API Route Mounting
# ============================================================================

# Primary v1 API routes
app.include_router(health_router, prefix="/api/v1")
app.include_router(dashboard_router, prefix="/api/v1")
app.include_router(incidents_router, prefix="/api/v1")
app.include_router(ml_router, prefix="/api/v1")

# Direct /health endpoint
app.include_router(health_router)

# Backward-compatibility routes for legacy callers (/api/incidents)
app.include_router(incidents_router, prefix="/api")
app.include_router(ml_router, prefix="/api")


@app.get("/", tags=["Health"])
def root_health():
    """Root quick liveness probe."""
    return {
        "status": "ok",
        "service": "JanSetu AI API",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
    }
