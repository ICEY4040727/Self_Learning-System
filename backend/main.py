from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from backend.core.config import get_settings
from backend.db.database import init_db

limiter = Limiter(key_func=get_remote_address)

settings = get_settings()

# Sentry error monitoring (only if DSN configured)
if settings.sentry_dsn:
    import sentry_sdk
    sentry_sdk.init(dsn=settings.sentry_dsn, traces_sample_rate=0.1)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_db()
    if settings.knowledge_graph_enabled:
        from backend.services.knowledge_graph import knowledge_graph_service
        knowledge_graph_service.configure(
            neo4j_uri=settings.neo4j_uri,
            neo4j_user=settings.neo4j_user,
            neo4j_password=settings.neo4j_password,
        )
        await knowledge_graph_service.initialize()
    yield
    # Shutdown
    if settings.knowledge_graph_enabled:
        from backend.services.knowledge_graph import knowledge_graph_service
        await knowledge_graph_service.close()


app = FastAPI(
    title="Socratic Learning System",
    description="基于苏格拉底教学法的个性化学习系统",
    version="1.0.0",
    lifespan=lifespan,
)

# Rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.cors_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"message": "Socratic Learning System API", "version": "1.0.0"}


@app.get("/health")
async def health_check():
    from sqlalchemy import text
    from backend.db.database import SessionLocal
    from backend.services.memory import memory_service

    checks = {"api": "ok"}

    db = None
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception:
        checks["database"] = "error"
    finally:
        if db:
            db.close()

    try:
        memory_service.client.heartbeat()
        checks["chromadb"] = "ok"
    except Exception:
        checks["chromadb"] = "error"

    status = "healthy" if all(v == "ok" for v in checks.values()) else "degraded"
    return {"status": status, "checks": checks}


# Import and include routers
from backend.api.routes import auth, archive, learning, save

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(archive.router, prefix="/api", tags=["archive"])
app.include_router(learning.router, prefix="/api", tags=["learning"])
app.include_router(save.router, prefix="/api", tags=["save"])


# Voice endpoint (reserved, returns 501)
@app.post("/api/voice", status_code=501)
async def voice_input():
    return {"message": "Voice input not yet implemented"}
