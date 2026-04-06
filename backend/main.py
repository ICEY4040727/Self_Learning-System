import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

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
    init_db()
    yield


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

    status = "healthy" if all(v == "ok" for v in checks.values()) else "degraded"
    return {"status": status, "checks": checks}


# Import and include routers
from backend.api.routes import archive, auth, learning, save  # noqa: E402

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(archive.router, prefix="/api", tags=["archive"])
app.include_router(learning.router, prefix="/api", tags=["learning"])
app.include_router(save.router, prefix="/api", tags=["checkpoints"])

# Static files
static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")
# HOT RELOAD TEST
