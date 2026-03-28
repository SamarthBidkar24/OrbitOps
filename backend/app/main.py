import importlib.util
import sys
from pathlib import Path
from fastapi import FastAPI, APIRouter, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
import uvicorn

from app.core.config import settings
from app.api.auth import router as auth_router
from app.api.chatbot import router as chatbot_router
from app.api.feed import router as feed_router
from app.api.calendar import router as calendar_router
from app.api.neo import router as neo_router
from app.api.spectra import router as spectra_router
from app.api.meteor import router as meteor_router

# Resolution: bharatakash/backend/app/main.py
# parent -> app/
# parent.parent -> backend/
# parent.parent.parent -> bharatakash/
BASE_DIR = Path(__file__).resolve().parent.parent.parent
MODELS_DIR = BASE_DIR / "models"
DB_PATH = BASE_DIR / "backend" / "orbitops.db"

def load_module(name: str, path: Path):
    if not path.exists():
        print(f"[!] Warning: Module not found at {path}")
        return None
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        if spec is None:
            return None
        mod = importlib.util.module_from_spec(spec)
        # Add the module's parent folder to sys.path to resolve internal relative imports
        if str(path.parent) not in sys.path:
            sys.path.append(str(path.parent))
        spec.loader.exec_module(mod)
        return mod
    except Exception as e:
        print(f"[!] Error loading module {name} from {path}: {e}")
        return None

app = FastAPI(
    title="OrbitOps API",
    description="Backend API for OrbitOps — NEO, Spectra & Meteor prediction platform",
    version="0.1.0",
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")

from fastapi.openapi.utils import get_openapi

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    # Use get_openapi to avoid recursion
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    
    # Add BearerAuth security scheme
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT"
        }
    }
    
    # Loop through paths and apply security logic
    for path, methods in openapi_schema["paths"].items():
        for method, details in methods.items():
            if method in ["get", "post", "put", "delete", "patch"]:
                # Logic to exclude specific open paths
                if "/auth/login" in path or "/auth/register" in path or path == "/health":
                    details.pop("security", None)
                else:
                    details["security"] = [{"BearerAuth": []}]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# CORS configuration: Hardcoded list to ensure security and local dev support
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173", 
        "http://localhost:5174", 
        "http://localhost:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    # Load model weights into global variables (app.models)
    from app.models import load_neo_model, load_spectra_model
    load_neo_model()
    load_spectra_model()

    # Load model prediction modules into app.state (for compatibility)
    app.state.neo = load_module("neo_predict", MODELS_DIR / "neo_model/src/predict.py")
    app.state.spectra = load_module("spectra_predict", MODELS_DIR / "spectra_model/src/predict.py")
    app.state.meteor = load_module("meteor_predict", MODELS_DIR / "meteor_model/src/predict.py")
    
    # --- Initialize database ---
    try:
        from app.db.models import create_tables, get_db_engine, get_session_local
        from app.db.sqlitemanager import SQLiteManager

        engine = get_db_engine(f"sqlite:///{DB_PATH}")
        create_tables(engine)
        SessionLocal = get_session_local(engine)
        app.state.db = SQLiteManager(SessionLocal)
        print("[*] Database initialized")
    except Exception as e:
        print(f"[!] DB init failed: {e}")

    # Final module readiness checks
    if app.state.meteor: print("[+] Meteor module ready")

# Prefix /api/v1 as used formerly
api_router = APIRouter(prefix="/api/v1")

# Include Routers
api_router.include_router(neo_router)
api_router.include_router(spectra_router)
api_router.include_router(meteor_router)
api_router.include_router(auth_router)
api_router.include_router(chatbot_router)
api_router.include_router(feed_router)
api_router.include_router(calendar_router)

app.include_router(api_router)

@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "ok",
        "env": settings.APP_ENV,
        "models": {
            "neo": hasattr(app.state, "neo") and app.state.neo is not None,
            "spectra": hasattr(app.state, "spectra") and app.state.spectra is not None,
            "meteor": hasattr(app.state, "meteor") and app.state.meteor is not None
        }
    }

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
