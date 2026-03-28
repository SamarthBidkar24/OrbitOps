import os
import sys
import pandas as pd
from pathlib import Path
from fastapi import APIRouter, HTTPException

# ── 1. Setup Relative Paths ──────────────────────────────────────────────────
# Resolve paths relative to this file to allow for portability across machines
# File path: /bharatakash/backend/app/api/meteor.py
# parent -> api/
# parent.parent -> app/
# parent.parent.parent -> backend/
# parent.parent.parent.parent -> bharatakash/
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
MODEL_PATH = BASE_DIR / "models" / "meteor_model" / "src"

# Add the model source directory to sys.path to allow imports
if str(MODEL_PATH) not in sys.path:
    sys.path.insert(0, str(MODEL_PATH))

# Now we can import the predict module relatively
try:
    import predict as meteor_predict
except ImportError as e:
    # Fallback to keep the router functional even if module loading fails during dev
    print(f"✘ Meteor Predict module not found at {MODEL_PATH}: {e}")
    meteor_predict = None

router = APIRouter(prefix="/meteor", tags=["Meteor"])

# ── 2. Route Handlers ─────────────────────────────────────────────────────────

@router.get("/tonight/{city}")
async def get_tonight(city: str):
    """Fetch visible meteor showers for a specific city for the current night."""
    if not meteor_predict:
        raise HTTPException(status_code=503, detail="Meteor prediction service unavailable")
    try:
        # Calls the function in predict.py
        result = meteor_predict.get_tonight_showers(city)
        return result
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Error finding city: {str(e)}")

@router.get("/calendar/{city}")
async def get_calendar(city: str, year: int = None, month: int = None):
    """Get a 30-day forecast of meteor shower intensity for calendars."""
    if not meteor_predict:
        raise HTTPException(status_code=503, detail="Meteor prediction service unavailable")
    try:
        from datetime import datetime
        now = datetime.now()
        
        # Use provided query params or fallback to current month
        target_year = year if year is not None else now.year
        target_month = month if month is not None else now.month
        
        result = meteor_predict.get_month_calendar(city, target_year, target_month)
        return result
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Error getting calendar data: {str(e)}")

@router.get("/darkmap")
async def get_darkmap():
    """Retrieve city-wise sky quality (Bortle rating) for the observation map."""
    try:
        data_path = MODEL_PATH.parent / "data" / "india_cities_bortle.csv"
        
        if not data_path.exists():
            raise FileNotFoundError(f"City data file not found at {data_path}")
            
        df = pd.read_csv(data_path)
        
        # Keep cities with pop > 50k OR very dark spots (Bortle <= 4)
        df_filtered = df[(df['population'] > 50000) | (df['bortle'] <= 4)].copy()
        
        # Sort by Bortle (darkest first) then population (largest first)
        df_filtered = df_filtered.sort_values(by=['bortle', 'population'], ascending=[True, False])
        
        cities = []
        for _, row in df_filtered.iterrows():
            lat = row.get('latitude', row.get('lat', 0.0))
            lon = row.get('longitude', row.get('lon', row.get('lng', 0.0)))
            
            cities.append({
                "name": str(row['city']),
                "lat": float(lat),
                "lon": float(lon),
                "bortle": int(row['bortle']),
                "bortle_class": int(row['bortle']), # Alias for frontend
                "population": float(row['population']) if pd.notnull(row['population']) else 0,
                "limiting_mag": float(row['limiting_magnitude']),
                "state": str(row.get('state', row.get('admin_name', '')))
            })
            
        return {"cities": cities}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
