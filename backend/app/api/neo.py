from fastapi import APIRouter

router = APIRouter(prefix="/neo", tags=["NEO"])

@router.post("/predict")
async def predict_neo(data: dict):
    """Run NEO hazard prediction model."""
    # TODO: wire up NEO inference service
    return {"model": "neo_model", "prediction": None}
