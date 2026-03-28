import importlib.util
import sys
from pathlib import Path
from fastapi import FastAPI, APIRouter, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
import uvicorn

# Resolution: bharatakash/backend/app/main.py
# parent -> app/
# parent.parent -> backend/
# parent.parent.parent -> bharatakash/
BASE_DIR = Path(__file__).resolve().parent.parent.parent
MODELS_DIR = BASE_DIR / "models"
DB_PATH = BASE_DIR / "backend" / "orbitops.db"

# -------------------------------------------------------------
# Module dynamic loader for model src scripts
# -------------------------------------------------------------
def load_module(name: str, path: Path):
    if not path.exists():
        print(f"✘ Warning: Module not found at {path}")
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
        print(f"✘ Error loading module {name} from {path}: {e}")
        return None

# -------------------------------------------------------------
# App configuration and startup
# -------------------------------------------------------------
from app.core.config import settings

app = FastAPI(
    title="OrbitOps API",
    description="Backend API for OrbitOps — NEO, Spectra & Meteor prediction platform",
    version="0.1.0",
)

# Dummy OAuth2PasswordBearer as a placeholder
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")

# CORS setup
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
    try:
        from app.models import load_neo_model, load_spectra_model
        load_neo_model()
        load_spectra_model()
    except Exception as e:
        print(f"✘ Model initialization failed: {e}")

    # Load model prediction modules into app.state (for compatibility)
    app.state.neo = load_module("neo_predict", MODELS_DIR / "neo_model/src/predict.py")
    app.state.spectra = load_module("spectra_predict", MODELS_DIR / "spectra_model/src/predict.py")
    app.state.meteor = load_module("meteor_predict", MODELS_DIR / "meteor_model/src/predict.py")
    
    # Ready checks
    if app.state.meteor: print("✓ Meteor module ready")
    if app.state.neo: print("✓ NEO module ready")
    if app.state.spectra: print("✓ Spectra module ready")

# Placeholder routers for the missing APIs - to be filled
api_router = APIRouter(prefix="/api/v1")

# Include Routers (Must be imported/rebuilt first)
# For now, let's include the ones we are about to rebuild
from app.api.chatbot import router as chatbot_router
from app.api.neo import router as neo_router
from app.api.spectra import router as spectra_router
from app.api.meteor import router as meteor_router

api_router.include_router(chatbot_router)
api_router.include_router(neo_router)
api_router.include_router(spectra_router)
api_router.include_router(meteor_router)

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
