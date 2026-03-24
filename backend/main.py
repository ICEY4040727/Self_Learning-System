from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.core.config import get_settings
from backend.db.database import init_db

settings = get_settings()

app = FastAPI(
    title="Socratic Learning System",
    description="基于苏格拉底教学法的个性化学习系统",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    init_db()


@app.get("/")
async def root():
    return {"message": "Socratic Learning System API", "version": "1.0.0"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


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


# Settings endpoint placeholder
@app.get("/api/settings")
async def get_settings():
    return {"message": "User settings endpoint"}