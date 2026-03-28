import io
from fastapi import APIRouter, HTTPException, Request, File, UploadFile
from pydantic import BaseModel

router = APIRouter(prefix="/spectra", tags=["Spectra"])

class SpectraRequest(BaseModel):
    wavelengths: list[float]
    reflectances: list[float]

@router.post("/classify")
async def classify_spectra(
    request: Request,
    file: UploadFile = File(None),
    body: SpectraRequest = None
):
    """Classify asteroid spectra using trained machine learning models."""
    try:
        wavelengths = []
        reflectances = []

        if file:
            # Handle .spc file upload (Assuming SPEX format: wavelength reflectance per line)
            content = await file.read()
            text = content.decode('utf-8')
            for line in text.splitlines():
                parts = line.split()
                if len(parts) >= 2:
                    try:
                        w = float(parts[0])
                        r = float(parts[1])
                        # Auto-convert micrometers to nanometers if detected
                        # (If max wavelength is < 10, it's definitely in micrometers)
                        wavelengths.append(w)
                        reflectances.append(r)
                    except ValueError:
                        continue
            
            # Post-process wavelengths if they are in micrometers
            if wavelengths and max(wavelengths) < 10:
                wavelengths = [w * 1000 for w in wavelengths]
        
        elif body:
            wavelengths = body.wavelengths
            reflectances = body.reflectances
            if wavelengths and max(wavelengths) < 10:
                wavelengths = [w * 1000 for w in wavelengths]
        
        if not wavelengths or not reflectances:
            raise HTTPException(status_code=400, detail="No spectral data provided")

        if len(wavelengths) < 3:
            raise HTTPException(status_code=400, detail="Minimum 3 data points required")

        # Call the spectra classification module
        spectra_module = request.app.state.spectra
        if not spectra_module:
            raise HTTPException(status_code=503, detail="Spectra service unavailable")
            
        result = spectra_module.classify_spectrum(wavelengths, reflectances)
        
        # Merge AI result with a 'type' alias for backward compatibility
        # but ensure 'predicted_class' is present for the new UI.
        return {
            **result,
            "type": result.get("predicted_class", "S-type")
        }
        
    except Exception as e:
        # Log error in terminal to help debug
        print(f"✘ [SPECTRA API ERROR] {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Classification failed: {str(e)}")
