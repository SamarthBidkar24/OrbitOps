"""
build_bortle_map.py — Light Pollution and Sky Darkest Estimation for India
========================================================================
Calculates Bortle scale and naked-eye limiting magnitude (NELM) for 
Indian cities to assist in meteor shower visibility predictions.
"""

import pandas as pd
import numpy as np
import joblib
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent.parent.resolve()
INPUT_CSV = BASE_DIR / "data" / "india_cities.csv"
OUTPUT_CSV = BASE_DIR / "data" / "india_cities_bortle.csv"
SAVED_PKL = BASE_DIR / "saved" / "city_bortle_map.pkl"

def calculate_limiting_mag(bortle):
    # limiting_mag = 7.93 - 5 * log10(1 + 10^(4.316 - bortle * 0.395))
    val = 1 + 10**(4.316 - bortle * 0.395)
    return 7.93 - 5 * np.log10(val)

def assign_bortle(pop):
    if pd.isna(pop) or pop < 10_000:
        return 3
    elif pop < 50_000:
        return 4
    elif pop < 200_000:
        return 5
    elif pop < 1_000_000:
        return 6
    elif pop < 5_000_000:
        return 7
    else:
        return 8

def build_map():
    if not INPUT_CSV.exists():
        print(f"[✗] Input not found: {INPUT_CSV}")
        return

    print(f"[->] Loading {INPUT_CSV.name}...")
    df = pd.read_csv(INPUT_CSV)
    
    # 1. Map columns
    # Resource columns: name, state_name, latitude, longitude, population
    df = df.rename(columns={
        'name': 'city',
        'state_name': 'state',
        'latitude': 'lat',
        'longitude': 'lon'
    })
    
    # 2. Estimate Bortle from population
    print("[->] Estimating Bortle class from population density proxy...")
    df['bortle'] = df['population'].apply(assign_bortle)
    
    # 3. Apply manual overrides (Known Dark Sky Sites)
    overrides = {
        "Hanle, Ladakh":       (32.7794, 78.9644, 1),
        "Spiti Valley":        (32.2432, 78.0413, 2),
        "Rann of Kutch":       (23.7337, 69.8597, 2),
        "Coorg, Karnataka":    (12.3375, 75.8069, 3),
        "Pench, MP":           (21.7548, 79.2961, 3),
        "Jaisalmer outskirts": (26.9157, 70.9083, 2),
    }
    
    override_rows = []
    for city, (lat, lon, bortle) in overrides.items():
        override_rows.append({
            'city': city,
            'state': 'Manual Override',
            'lat': lat,
            'lon': lon,
            'population': 0,
            'bortle': bortle
        })
    
    df_overrides = pd.DataFrame(override_rows)
    df = pd.concat([df, df_overrides], ignore_index=True)
    
    # 4. Compute Limiting Magnitude
    print("[->] Computing Limiting Magnitude (NELM)...")
    df['limiting_magnitude'] = df['bortle'].apply(calculate_limiting_mag)
    
    # Selection of final columns
    final_df = df[['city', 'state', 'lat', 'lon', 'population', 'bortle', 'limiting_magnitude']]
    
    # 5. Save Outputs
    final_df.to_csv(OUTPUT_CSV, index=False)
    
    # Create PKL Map
    # dict: city_name -> {bortle, limiting_mag, lat, lon}
    # Using city name as key. Note: potential dupes, but usually latest takes precedence or unique enough.
    # To be safe, we can use "City, State" if requested, but user said "city_name".
    bortle_map = {}
    for _, row in final_df.iterrows():
        bortle_map[row['city']] = {
            'bortle': int(row['bortle']),
            'limiting_mag': float(row['limiting_magnitude']),
            'lat': float(row['lat']),
            'lon': float(row['lon'])
        }
    
    BASE_DIR.joinpath("saved").mkdir(exist_ok=True)
    joblib.dump(bortle_map, SAVED_PKL)
    
    print(f"\n[✓] Enriched data saved to {OUTPUT_CSV.name}")
    print(f"[✓] Bortle map serialized to {SAVED_PKL.name}")
    
    # 6. Summary Prints
    print("\n" + "="*40)
    print("TOP 10 DARKEST SITES / CITIES")
    print("="*40)
    darkest = final_df.sort_values(by=['bortle', 'population'], ascending=[True, True]).head(10)
    for _, row in darkest.iterrows():
        print(f"  {row['city']:<20} | Bortle {row['bortle']} | Mag {row['limiting_magnitude']:.2f}")
        
    print("\n" + "="*40)
    print("TOP 5 BRIGHTEST CITIES")
    print("="*40)
    brightest = final_df.sort_values(by='population', ascending=False).head(5)
    for _, row in brightest.iterrows():
        print(f"  {row['city']:<20} | Bortle {row['bortle']} | Pop {int(row['population']):,}")
    print("="*40)

if __name__ == "__main__":
    build_map()
