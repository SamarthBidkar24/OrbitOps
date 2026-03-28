from fastapi import APIRouter, Request, HTTPException, UploadFile, File
from pydantic import BaseModel

router = APIRouter(prefix="/spectra", tags=["Spectra"])

@router.post("/predict")
async def analyze_spectra(request: Request, body: dict):
    """Analyze asteroid spectral data for mineral composition."""
    if not hasattr(request.app.state, 'spectra') or request.app.state.spectra is None:
        raise HTTPException(status_code=503, detail="Spectra module not ready")
    
    try:
        return request.app.state.spectra.predict(body)
    except Exception as e:
        return {"predicted_class": "Unknown", "composition": {"Iron": 0, "Silicates": 0}, "error": str(e)}

@router.post("/upload")
async def upload_spectra(request: Request, file: UploadFile = File(...)):
    """Handle spectral .spc file uploads."""
    content = await file.read()
    # In a real app we'd save it or parse it. 
    return {"status": "success", "filename": file.filename}
