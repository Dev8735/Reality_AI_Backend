"""FastAPI main application entrypoint."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Reality AI Backend API",
    version="1.0.0",
    description="Backend service for Reality AI — AI-powered real estate exploration platform in Surat, Gujarat.",
)

# CORS Middleware setup
# NOTE: Configured permissively for local development; must be tightened before production deployment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["Health"])
def health_check() -> dict[str, str]:
    """Basic health check endpoint."""
    return {"status": "ok"}


# ── Routers ──────────────────────────────────────────────────────────────
from app.api.routes import auth, listings, chat, boundary_search, analytics

app.include_router(auth.router)
app.include_router(listings.router)
app.include_router(chat.router)
app.include_router(boundary_search.router)
app.include_router(analytics.router)

