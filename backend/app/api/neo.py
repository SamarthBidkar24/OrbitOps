from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

router = APIRouter(prefix="/neo", tags=["NEO"])

class NeoRequest(BaseModel):
    date: str
    observatory_index: int = 0
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "date": "2025-08-12",
                    "observatory_index": 0
                }
            ]
        }
    }

from app.cache import get_cached, set_cached

@router.post("/predict")
async def predict_neo(body: NeoRequest, request: Request):
    """Run real NEO hazard prediction and cache results."""
    try:
        # 1. Check cache first
        cached = get_cached(body.date, body.observatory_index)
        if cached:
            return cached

        # 2. Access the loaded model module from app state
        # This was loaded in main.py startup
        neo_module = getattr(request.app.state, "neo", None)
        
        if neo_module is None:
            raise HTTPException(status_code=503, detail="NEO prediction module not loaded")
            
        # 3. Call the real predict_neo function
        # Signature: predict_neo(date_str, observatory_index=0)
        result = neo_module.predict_neo(
            date_str=body.date, 
            observatory_index=body.observatory_index
        )
        
        # 4. Error handling from model logic
        if isinstance(result, dict) and "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
            
        # 5. Store in cache
        set_cached(body.date, body.observatory_index, result)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"✘ NEO API Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
