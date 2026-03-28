from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/neo", tags=["NEO"])

class NEORequest(BaseModel):
    date: str
    observatory: str = "Hanle"

@router.post("/predict")
async def predict_neo(request: Request, body: NEORequest):
    """Predict NEO threat levels using the dashboard model."""
    if not hasattr(request.app.state, 'neo') or request.app.state.neo is None:
        raise HTTPException(status_code=503, detail="NEO Model module not ready")
    
    # Logic to call the external module loaded in app.state
    try:
        # Assuming the predict module has a 'predict' function
        result = request.app.state.neo.predict(body.dict())
        return result
    except Exception as e:
        return {"status": "error", "message": str(e), "fallback": "No threat detected."}
