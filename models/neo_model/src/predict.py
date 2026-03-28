"""
predict.py — NEO Prediction and Visibility Module
==================================================
Loads trained models (Classifier, Regressor) and provides an interface 
for querying NEO close approaches with visibility information from Indian observatories.
"""

import pandas as pd
import numpy as np
import joblib
from pathlib import Path
from datetime import datetime, timedelta, timezone
from astropy.coordinates import SkyCoord, AltAz, EarthLocation
from astropy.time import Time
import astropy.units as u
import warnings

# Suppress noisy Astropy/Pandas warnings
warnings.filterwarnings('ignore')

# ── Paths & Loading ───────────────────────────────────────────────────────────
SRC_DIR = Path(__file__).parent.resolve()
BASE_DIR = SRC_DIR.parent
SAVED_DIR = BASE_DIR / "saved"
DATA_DIR = BASE_DIR / "data"

# Load models once at module level
THREAT_CLF = joblib.load(SAVED_DIR / "threat_classifier.pkl")
# Threat regressor was bonus, but requested for 'threat_score' prediction
THREAT_REG = joblib.load(SAVED_DIR / "threat_regressor.pkl")
FEATURE_NAMES = joblib.load(SAVED_DIR / "feature_names.pkl")
RAW_DF = pd.read_csv(DATA_DIR / "neo_closeapproach.csv")

# Constants
OBS = {
    0: ("IAO Hanle",      32.7794, 78.9644, 4500),
    1: ("ARIES Nainital", 29.3609, 79.4566, 1951),
    2: ("VBO Kavalur",    12.5765, 78.8268,  725),
    3: ("PRL Ahmedabad",  23.0225, 72.5714,   53),
    4: ("IUCAA Pune",     18.5204, 73.8567,  559)
}
OBS_NAMES = {k: v[0] for k, v in OBS.items()}

# ── Helper Logic (Reused from features.py) ───────────────────────────────────

def get_ist_offset() -> timezone:
    return timezone(timedelta(hours=5, minutes=30))

def compute_physical_features(df: pd.DataFrame) -> pd.DataFrame:
    """Computes features required by the models."""
    df = df.copy()
    
    # 1. Temporal
    df['cd_dt'] = pd.to_datetime(df['cd'])
    df['month'] = df['cd_dt'].dt.month
    
    today = datetime.now(timezone.utc).replace(tzinfo=None)
    df['days_from_now'] = (df['cd_dt'] - today).dt.total_seconds() / (24 * 3600)
    
    # 2. Physics
    df['dist_km'] = pd.to_numeric(df['dist'], errors='coerce') * 149597870.7
    df['v_rel'] = pd.to_numeric(df['v_rel'], errors='coerce')
    df['h'] = pd.to_numeric(df['h'], errors='coerce')
    
    df['diameter_km'] = (1329.0 / (0.154 ** 0.5)) * (10 ** (-df['h'] / 5)) / 1000
    
    # Target feature in Classifier, but needs to be calculated for the regressor inputs 
    # if it's part of FEATURE_NAMES. 
    # NOTE: In train.py, the regressor used (FEATURE_NAMES - 'threat_score').
    # But the Classifier used the FULL FEATURE_NAMES.
    df['threat_score_calc'] = (df['diameter_km'] / df['dist_km']) * df['v_rel']
    
    # Mass/Energy (for feature completeness)
    r_m = (df['diameter_km'] * 1000) / 2
    mass_kg = (4/3) * 3.14159 * (r_m ** 3) * 1500
    df['kinetic_energy_megatons'] = 0.5 * mass_kg * (df['v_rel'] * 1000)**2 / (4.184e15)
    
    # Map the columns to standard FEATURE_NAMES for prediction
    # If 'threat_score' in FEATURE_NAMES, we'll use the calculated one for the CLASSIFIER
    # and the REGRESSOR will use its version.
    df['threat_score'] = df['threat_score_calc']
    
    return df

import requests
from requests.exceptions import Timeout

def get_cardinal_direction(az_deg: float) -> str:
    """Converts azimuth degrees to cardinal direction."""
    directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    idx = int((az_deg + 22.5) / 45) % 8
    return directions[idx]

def find_highest_alt_ist(cd_dt: datetime, ra: float, dec: float, obs_idx: int) -> tuple:
    """Calculates the time, highest altitude, and azimuth from an observatory location."""
    name, lat, lon, height = OBS[obs_idx]
    loc = EarthLocation(lat=lat*u.deg, lon=lon*u.deg, height=height*u.m)
    coord = SkyCoord(ra=ra*u.deg, dec=dec*u.deg)
    
    # Check 24 hours around approach
    times = [cd_dt - timedelta(hours=12) + timedelta(minutes=15 * i) for i in range(24 * 4)]
    astro_times = Time(times)
    
    altaz_frame = AltAz(obstime=astro_times, location=loc)
    altaz_objs = coord.transform_to(altaz_frame)
    alts = altaz_objs.alt.deg
    
    idx_max = np.argmax(alts)
    best_time = times[idx_max]
    az_at_max = altaz_objs.az.deg[idx_max]
    
    # Convert to IST
    ist_time = best_time.replace(tzinfo=timezone.utc).astimezone(get_ist_offset())
    return ist_time.strftime("%H:%M IST"), np.max(alts), az_at_max

def get_orbital_elements(des: str) -> dict:
    """Fetches orbital elements from JPL SBDB API."""
    fallback = {"a": 1.2, "e": 0.3, "i": 10.0, "om": 0.0, "w": 0.0, "ma": 0.0}
    url = f"https://ssd-api.jpl.nasa.gov/sbdb.api?sstr={des}"
    try:
        resp = requests.get(url, timeout=3)
        if resp.status_code == 200:
            data = resp.json()
            orbit = data.get('orbit', {})
            elements = orbit.get('elements', [])
            
            # Map elements based on 'name' key in JPL output
            # Elements typically: a, e, i, q, om, w, ma
            extracted = {}
            mapping = {'a': 'a', 'e': 'e', 'i': 'i', 'om': 'om', 'w': 'w', 'ma': 'ma'}
            for el in elements:
                name = el.get('name')
                if name in mapping:
                    extracted[mapping[name]] = float(el.get('value'))
            
            # Use fallback for missing keys
            for key in fallback:
                if key not in extracted:
                    extracted[key] = fallback[key]
            
            # Ensure omega, w, M naming matches user request if they differ
            # User asked for: { a, e, i, omega, w, M }
            # JPL: om (omega), w (w), ma (M)
            return {
                "a": extracted["a"],
                "e": extracted["e"],
                "i": extracted["i"],
                "omega": extracted["om"],
                "w": extracted["w"],
                "M": extracted["ma"]
            }
    except (Timeout, Exception):
        pass
    return {
        "a": fallback["a"],
        "e": fallback["e"],
        "i": fallback["i"],
        "omega": fallback["om"],
        "w": fallback["w"],
        "M": fallback["ma"]
    }

# ── Main API ───────────────────────────────────────────────────────────────

def predict_neo(date_str: str, observatory_index: int = 0) -> dict:
    """
    date_str: 'YYYY-MM-DD'
    observatory_index: Index of the observatory (0-4)
    """
    target_date = datetime.strptime(date_str, "%Y-%m-%d")
    
    # 1. Filter raw_df for UPCOMING approaches (from target_date to +180 days)
    df = RAW_DF.copy()
    df['cd_dt'] = pd.to_datetime(df['cd'])
    
    mask = (df['cd_dt'] >= target_date) & \
           (df['cd_dt'] <= target_date + timedelta(days=180))
    df_window = df[mask].copy()
    
    if df_window.empty:
        return {
            "query_date": date_str,
            "observatory": OBS_NAMES[observatory_index],
            "total_neos_in_window": 0,
            "top_neos": [],
            "summary": f"No upcoming NEOs found in the window after {date_str}."
        }

    # 2. Compute Features
    df_feats = compute_physical_features(df_window)
    
    # 3. Predict threat_category and threat_score
    # Prepare X for Classifier
    X_clf = df_feats[FEATURE_NAMES]
    df_feats['threat_level'] = THREAT_CLF.predict(X_clf)
    
    # Prepare X for Regressor (it was trained on FEATURE_NAMES without 'threat_score')
    features_reg = [f for f in FEATURE_NAMES if f != 'threat_score']
    X_reg = df_feats[features_reg]
    df_feats['predicted_threat_score'] = THREAT_REG.predict(X_reg)
    
    # 4. Sort and take Top 30
    df_top = df_feats.sort_values(by='predicted_threat_score', ascending=False).head(30)
    
    # 5. Viewing details
    top_neos_list = []
    for _, row in df_top.iterrows():
        # Match simulation RA/Dec from features.py (based on index)
        orig_idx = row.name
        ra_sim = (orig_idx * 13.5) % 360
        dec_sim = np.clip((orig_idx * 7.2) % 180 - 90, -90.0, 90.0)
        
        view_time, max_alt, az_at_max = find_highest_alt_ist(row['cd_dt'], ra_sim, dec_sim, observatory_index)
        
        # Orbital elements
        orbit = get_orbital_elements(str(row['des']))
        
        # Send raw diameter for frontend precision handling
        diam_km = float(row['diameter_km'])
        
        top_neos_list.append({
            "name": str(row['des']),
            "close_approach_date": row['cd_dt'].strftime("%Y-%b-%d %H:%M"),
            "distance_km": float(round(row['dist_km'], -3)),
            "diameter_km": diam_km,
            "velocity_kms": float(round(row['v_rel'], 2)),
            "threat_level": row['threat_level'],
            "threat_score": float(round(row['predicted_threat_score'], 5)),
            "orbital_elements": orbit,
            "sky_position": {
                "azimuth_deg": float(round(az_at_max, 2)),
                "altitude_deg": float(round(max_alt, 2)),
                "cardinal_direction": get_cardinal_direction(az_at_max)
            },
            "best_viewing_time_ist": view_time,
            "india_visible": bool(max_alt > 20)
        })
        
    # 6. Summary
    alert_count = sum(1 for n in top_neos_list if n['threat_level'] == 'alert')
    if alert_count > 0:
        summary = f"{len(df_top)} NEOs found. {alert_count} pose a high-risk ALERT in this window."
    else:
        summary = f"{len(df_top)} NEOs approach Earth in this window. None pose a significant threat requiring immediate alert."

    return {
        "query_date": date_str,
        "observatory": OBS_NAMES[observatory_index],
        "total_neos_in_window": len(df_window),
        "top_neos": top_neos_list,
        "summary": summary
    }

if __name__ == "__main__":
    # Test query
    sample_res = predict_neo("2024-05-15", observatory_index=0)
    import json
    print(json.dumps(sample_res, indent=2))
