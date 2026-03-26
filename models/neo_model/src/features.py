import pandas as pd
import numpy as np
from datetime import datetime, timezone
from pathlib import Path
from astropy.coordinates import SkyCoord, AltAz, EarthLocation
from astropy.time import Time
import astropy.units as u
import warnings

# Suppress noisy Pandas/Astropy warnings during batch processing
warnings.filterwarnings('ignore')

# ── Configuration ─────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent.parent.resolve()
INPUT_CSV = BASE_DIR / "data" / "neo_closeapproach.csv"
OUTPUT_CSV = BASE_DIR / "data" / "neo_features.csv"

# Indian Observatories metadata (From USER)
OBS = {
    0: ("IAO Hanle",      32.7794, 78.9644, 4500),
    1: ("ARIES Nainital", 29.3609, 79.4566, 1951),
    2: ("VBO Kavalur",    12.5765, 78.8268,  725),
    3: ("PRL Ahmedabad",  23.0225, 72.5714,   53),
    4: ("IUCAA Pune",     18.5204, 73.8567,  559)
}

def build_features():
    if not INPUT_CSV.exists():
        print(f"[!] Input file not found: {INPUT_CSV}")
        return None

    print(f"[->] Loading {INPUT_CSV.name}...")
    df = pd.read_csv(INPUT_CSV)
    
    # ── 1. Date Transformation ──────────────────────────────────────────────
    print("[->] Parsing dates and temporal features...")
    df['cd_dt'] = pd.to_datetime(df['cd'], errors='coerce')
    df = df.dropna(subset=['cd_dt']).copy()
    
    df['year'] = df['cd_dt'].dt.year
    df['month'] = df['cd_dt'].dt.month
    df['day_of_year'] = df['cd_dt'].dt.dayofyear
    
    # Today as naive UTC for comparison
    today = datetime.now(timezone.utc).replace(tzinfo=None)
    df['days_from_now'] = (df['cd_dt'] - today).dt.total_seconds() / (24 * 3600)

    # ── 2. Physical Transformations ─────────────────────────────────────────
    print("[->] Computing physics metrics (Diameter, Energy, Score)...")
    # Ensure numeric types
    for col in ['dist', 'v_rel', 'h']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    df = df.dropna(subset=['dist', 'v_rel', 'h']).copy()

    df['dist_km'] = df['dist'] * 149597870.7
    
    # Diameter (km) based on albedo 0.154
    df['diameter_km'] = (1329.0 / (0.154 ** 0.5)) * (10 ** (-df['h'] / 5)) / 1000
    
    # Threat score
    df['threat_score'] = (df['diameter_km'] / df['dist_km']) * df['v_rel']
    
    # Kinetic Energy (exact user formula)
    # KE = 0.5 * Mass * V^2. Assuming density 1500 and volume (sphere).
    # Conversion to Megatons (4.184e15 J/MT)
    # Note: radius part uses (km*1000) inside to get correct units for mass calculation
    r_m = (df['diameter_km'] * 1000) / 2
    mass_kg = (4/3) * 3.14159 * (r_m ** 3) * 1500
    df['kinetic_energy_megatons'] = 0.5 * mass_kg * (df['v_rel'] * 1000)**2 / (4.184e15)

    # ── 3. Visibility from India ────────────────────────────────────────────
    print("[->] Calculating visibility from 5 Indian observatories...")
    
    # Placeholder RA/Dec for geometry logic demonstration (CNEOS CAD lacks them)
    # We generate deterministic variability based on index and clip to valid bounds
    df['ra_sim']  = (df.index * 13.5) % 360
    df['dec_sim'] = np.clip((df.index * 7.2) % 180 - 90, -90.0, 90.0)
    
    locations = [EarthLocation(lat=lat*u.deg, lon=lon*u.deg, height=height*u.m) 
                 for name, lat, lon, height in OBS.values()]
    
    # Force numpy/standard structures to avoid Astropy/Pandas Series mismatch
    times = Time(df['cd_dt'].dt.strftime('%Y-%m-%d %H:%M:%S').tolist(), scale='utc', format='iso')
    coords = SkyCoord(ra=df['ra_sim'].to_numpy()*u.deg, dec=df['dec_sim'].to_numpy()*u.deg)
    
    max_alt = np.full(len(df), -90.0)
    best_obs = np.full(len(df), -1)

    for i, loc in enumerate(locations):
        frame = AltAz(obstime=times, location=loc)
        alt = coords.transform_to(frame).alt.deg
        
        better = alt > max_alt
        max_alt[better] = alt[better]
        best_obs[better] = i
        
    df['india_visible'] = (max_alt > 20).astype(int)
    df['best_observatory'] = best_obs

    # ── 4. Target Labeling ──────────────────────────────────────────────────
    print("[->] Labelling threat categories...")
    def label_threat(row):
        if row['dist_km'] < 1000000 and row['diameter_km'] > 0.14:
            return 'alert'
        elif row['dist_km'] < 5000000 or row['diameter_km'] > 0.05:
            return 'watch'
        else:
            return 'monitor'
            
    df['threat_category'] = df.apply(label_threat, axis=1)

    # ── 5. Output ───────────────────────────────────────────────────────────
    print("\n[OK] Processing Complete.")
    print("Class Distribution of Threat Category:")
    print(df['threat_category'].value_counts())
    print("-" * 35)

    final_cols = [
        'des', 'year', 'month', 'day_of_year', 'days_from_now',
        'dist_km', 'diameter_km', 'v_rel', 'h', 'threat_score', 'kinetic_energy_megatons',
        'india_visible', 'best_observatory', 'threat_category'
    ]
    
    out_df = df[final_cols]
    out_df.to_csv(OUTPUT_CSV, index=False)
    print(f"[OK] Features written to {OUTPUT_CSV.name}")
    
    return out_df

if __name__ == "__main__":
    build_features()
