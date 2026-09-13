"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.ai import agent_router, router as ai_router
from app.api.complaints import router as complaints_router
from app.api.health import router as health_router
from app.config import get_settings, parse_frontend_origins

settings = get_settings()

app = FastAPI(
    title="Pharma Complaint AI API",
    version=settings.app_version,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=parse_frontend_origins(settings.frontend_origin),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix="/api")
app.include_router(complaints_router, prefix="/api")
app.include_router(ai_router, prefix="/api")
app.include_router(agent_router, prefix="/api")
