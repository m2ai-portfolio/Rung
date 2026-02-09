"""Rung FastAPI Application - Main Entry Point

HIPAA-compliant psychology agent orchestration API.
All PHI handling follows encryption and audit logging requirements.
"""

import os
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

# Create FastAPI app with environment-aware configuration
app = FastAPI(
    title="Rung - Psychology Agent Orchestration",
    version="0.1.0",
    description="HIPAA-compliant multi-agent psychology support system",
    docs_url="/docs" if os.environ.get("RUNG_ENV") != "production" else None,
    redoc_url="/redoc" if os.environ.get("RUNG_ENV") != "production" else None,
)


# =============================================================================
# Health Checks
# =============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint for ECS/load balancer"""
    return {
        "status": "healthy",
        "service": "rung",
        "version": "0.1.0",
    }


@app.get("/healthz")
async def healthz():
    """Kubernetes-style health check"""
    return {"status": "ok"}


# =============================================================================
# Error Handlers
# =============================================================================

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    """Return structured validation errors without exposing internal details"""
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Invalid request",
            "type": "validation_error",
        },
    )


# =============================================================================
# API Routers
# =============================================================================

# Import and include API routers
try:
    from src.api.pre_session import router as pre_session_router
    app.include_router(pre_session_router)
except ImportError as e:
    print(f"Warning: Could not import pre_session router: {e}")

try:
    from src.api.post_session import router as post_session_router
    app.include_router(post_session_router)
except ImportError as e:
    print(f"Warning: Could not import post_session router: {e}")

try:
    from src.api.couples import router as couples_router
    app.include_router(couples_router)
except ImportError as e:
    print(f"Warning: Could not import couples router: {e}")

try:
    from src.api.voice_memo import router as voice_memo_router
    app.include_router(voice_memo_router)
except ImportError as e:
    print(f"Warning: Could not import voice_memo router: {e}")

try:
    from src.api.development_plan import router as development_plan_router
    app.include_router(development_plan_router)
except ImportError as e:
    print(f"Warning: Could not import development_plan router: {e}")

try:
    from src.api.merged_frameworks import router as merged_frameworks_router
    app.include_router(merged_frameworks_router)
except ImportError as e:
    print(f"Warning: Could not import merged_frameworks router: {e}")

try:
    from src.api.reading_list import router as reading_list_router
    app.include_router(reading_list_router)
except ImportError as e:
    print(f"Warning: Could not import reading_list router: {e}")


# =============================================================================
# Startup/Shutdown Events
# =============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize application resources"""
    print("Rung API starting up...")


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up application resources"""
    print("Rung API shutting down...")


# =============================================================================
# Root Endpoint
# =============================================================================

@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "service": "rung",
        "description": "HIPAA-compliant psychology agent orchestration",
        "version": "0.1.0",
        "docs": "/docs" if os.environ.get("RUNG_ENV") != "production" else None,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, workers=2)
