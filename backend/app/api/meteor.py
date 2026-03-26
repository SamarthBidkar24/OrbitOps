import os
import sys
import pandas as pd
from fastapi import APIRouter, HTTPException
from pathlib import Path

# Fix module imports for cross-directory access
MODEL_PATH = Path("c:/Users/acer/Desktop/OrbitOps/bharatakash/models/meteor_model/src")
sys.path.append(str(MODEL_PATH))

import predict as meteor_predict

router = APIRouter(prefix="/meteor", tags=["Meteor"])

# ── 1. Tonight's Showers ──────────────────────────────────────────────────────
@router.get("/tonight/{city}")
async def get_tonight(city: str):
    """Get visible meteor showers for a specific city for tonight."""
    try:
        res = meteor_predict.get_tonight_showers(city)
        return res
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

# ── 2. Monthly Calendar ───────────────────────────────────────────────────────
@router.get("/calendar/{city}")
async def get_calendar(city: str):
    """Aggregate daily intensities into a 30-day view."""
    try:
        res = meteor_predict.get_month_calendar(city)
        return res
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

# ── 3. Dark Sky Map (NEW) ─────────────────────────────────────────────────────
@router.get("/darkmap")
async def get_darkmap():
    """Return all city sky ratings for the India color-coded map."""
    try:
        # Load city data from model folder
        data_path = Path("c:/Users/acer/Desktop/OrbitOps/bharatakash/models/meteor_model/data/india_cities_bortle.csv")
        df = pd.read_csv(data_path)
        
        # Only return cities with population > 50,000
        # Assuming population column is 'population'
        df_filtered = df[df['population'] > 50000].copy()
        df_filtered = df_filtered.sort_values(by='bortle', ascending=True)
        
        cities = []
        for _, row in df_filtered.iterrows():
            cities.append({
                "name": str(row['city']),
                "lat": float(row['lat']),
                "lon": float(row['lng']),
                "bortle": int(row['bortle']),
                "limiting_mag": float(row['limiting_mag']),
                "state": str(row['admin_name'])
            })
            
        return {"cities": cities}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
