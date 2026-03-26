from fastapi import APIRouter

router = APIRouter(prefix="/spectra", tags=["Spectra"])

@router.post("/predict")
async def predict_spectra(data: dict):
    """Run stellar spectra classification model."""
    # TODO: wire up Spectra inference service
    return {"model": "spectra_model", "prediction": None}
