from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings , get

app = FastAPI(
    title="OrbitOps API",
    description="Backend API for OrbitOps — NEO, Spectra & Meteor prediction platform",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", tags=["Health"])
async def root():
    return {"status": "ok", "message": "OrbitOps API is running 🚀"}
