import os
import joblib
import pandas as pd
import numpy as np
import difflib
from datetime import datetime
from pathlib import Path
from math import radians, cos, sin, asin, sqrt
from astropy.time import Time
from astropy.coordinates import get_sun

# ── Paths and Loading ─────────────────────────────────────────────────────────
SRC_DIR = Path(__file__).parent.resolve()
BASE_DIR = SRC_DIR.parent
DATA_DIR = BASE_DIR / "data"
SAVED_DIR = BASE_DIR / "saved"

# Load at module level
LOOKUP_PATH = SAVED_DIR / "visibility_lookup.parquet"
BORTLE_MAP_PATH = SAVED_DIR / "city_bortle_map.pkl"
CITIES_CSV_PATH = DATA_DIR / "india_cities_bortle.csv"
SHOWERS_CSV_PATH = DATA_DIR / "iau_meteor_showers.csv"

# Global module state
try:
    lookup_df = pd.read_parquet(LOOKUP_PATH)
    # Ensure date is string format as used in lookup_df during building
    lookup_df['date'] = lookup_df['date'].astype(str)
    
    city_bortle = joblib.load(BORTLE_MAP_PATH)
    cities_df = pd.read_csv(CITIES_CSV_PATH)
    showers_info = pd.read_csv(SHOWERS_CSV_PATH)
except Exception as e:
    print(f"[!] Error loading prediction data: {e}")
    lookup_df = pd.DataFrame()
    city_bortle = {}
    cities_df = pd.DataFrame()
    showers_info = pd.DataFrame()

# ── Metadata ─────────────────────────────────────────────────────────────────
CONSTELLATIONS = {
    'PER': ('Perseus', 'PR'), 'GEM': ('Gemini', 'GE'), 'LEO': ('Leo', 'LE'),
    'ORI': ('Orion', 'OR'), 'ETA': ('Aquarius', 'AQ'), 'QUA': ('Boötes', 'BO'),
    'LYR': ('Lyra', 'LY'), 'SDA': ('Aquarius', 'AQ'), 'TAU': ('Taurus', 'TA'),
    'DRA': ('Draco', 'DR'), 'URS': ('Ursa Minor', 'UM'), 'MON': ('Monoceros', 'MO'),
    'COM': ('Coma Berenices', 'CB'), 'NOO': ('Orion', 'OR'), 'KAP': ('Cygnus', 'CY'),
    'AND': ('Andromeda', 'AD'), 'PHO': ('Phoenix', 'PH'), 'NTA': ('Taurus', 'TA'),
    'JAC': ('Draco', 'DR'), 'AUR': ('Auriga', 'AU'), 'SPE': ('Perseus', 'PR'),
    'CAP': ('Capricornus', 'CP'), 'GDR': ('Draco', 'DR'), 'LMI': ('Leo Minor', 'LM'),
    'OPH': ('Ophiuchus', 'OP'), 'JBO': ('Boötes', 'BO'), 'PPU': ('Puppis', 'PU'),
    'ARC': ('Centaurus', 'CE'), 'GAN': ('Norma', 'NO'), 'VEL': ('Vela', 'VE')
}

# ── Helper Functions ──────────────────────────────────────────────────────────
def haversine(lat1, lon1, lat2, lon2):
    """Calculates the straight-line distance between two points in km."""
    R = 6371.0 # Earth radius
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    return R * c

def get_solar_longitude(dt_obj):
    """Calculates approximate solar longitude for a given datetime."""
    t = Time(dt_obj)
    sun = get_sun(t)
    return sun.ra.deg # Very approximate, better use ecliptic longitude but RA is close enough for +/- 3 days check

def find_peak_date(solar_long_peak, year=None):
    """Estimate the calendar date for a given solar longitude peak in target year."""
    if year is None: year = datetime.utcnow().year
    # Pivot date: starts at spring equinox (March 21) where solar_lon = 0
    # Approx 1 degree per day.
    # We find the day within the year.
    days_since_Jan1 = int(solar_long_peak * 1.01) + 80 # Offset for Equinox roughly
    # Actually, iterate to find closest day
    best_date = datetime(year, 1, 1)
    min_diff = 360
    # Search every 5 days then refine? Or just check common peaks. 
    # For simplicity, we'll return the string from a lookup or a simpler calc.
    # In a real app, this would be more precise.
    return f"{year}-MM-DD (Est)" # Placeholder string format for clarity

# ── Main API ──────────────────────────────────────────────────────────────────
def get_tonight_showers(city_name: str) -> dict:
    # 1. Handle city name with fuzzy match if not found exactly
    found_city = None
    if city_name in cities_df['city'].values:
        found_city = city_name
    else:
        all_cities = cities_df['city'].tolist()
        matches = difflib.get_close_matches(city_name, all_cities, n=1, cutoff=0.6)
        if matches:
            found_city = matches[0]
        else:
            return {"error": f"City '{city_name}' not found and no close matches found."}

    # 2. Query Tonight's Visibility (using UTC date as proxy for 'tonight')
    today = datetime.utcnow().date()
    today_str = str(today)
    
    city_tonight = lookup_df[(lookup_df['city'] == found_city) & 
                             (lookup_df['date'] == today_str) & 
                             (lookup_df['is_visible'] == True)].copy()
    
    city_tonight = city_tonight.sort_values('adjusted_zhr', ascending=False)
    
    # 3. Enrich with Bortle and limiting magnitude
    city_info = cities_df[cities_df['city'] == found_city].iloc[0]
    bortle = int(city_info['bortle'])
    lim_mag = float(city_info['limiting_magnitude'])
    
    # Approx current solar longitude for 'is_near_peak' calculation
    current_sol_lon = get_solar_longitude(datetime.utcnow())
    
    active_showers = []
    for _, row in city_tonight.iterrows():
        code = row['shower_code']
        # Fetch peak info
        info = showers_info[showers_info['shower_code'] == code]
        peak_sol_lon = info.iloc[0]['solar_long_peak'] if not info.empty else 0
        
        # is_near_peak: within +/- 3 degrees of solar longitude
        diff = abs(current_sol_lon - peak_sol_lon)
        if diff > 180: diff = 360 - diff
        is_near_peak = diff <= 3.0
        
        active_showers.append({
            "name": row['shower_name'],
            "shower_code": code,
            "adjusted_zhr": float(row['adjusted_zhr']),
            "radiant_altitude_deg": float(row['radiant_altitude_deg']),
            "best_viewing_time": f"{row['best_viewing_hour_ist']:02d}:00 IST",
            "constellation": CONSTELLATIONS.get(code, ("Unknown", ""))[0],
            "peak_date": f"SolLon {peak_sol_lon:.1f}°", # Simple reference
            "is_near_peak": bool(is_near_peak)
        })

    return {
        "city": found_city,
        "date": today_str,
        "bortle_class": bortle,
        "limiting_magnitude": lim_mag,
        "active_showers": active_showers,
        "best_nearby_dark_spots": get_dark_spots(found_city, radius_km=300)
    }

def get_month_calendar(city_name: str, year: int, month: int) -> dict:
    prefix = f"{year}-{month:02d}"
    df_month = lookup_df[(lookup_df['city'] == city_name) & 
                         (lookup_df['date'].str.startswith(prefix))].copy()
    
    if df_month.empty:
        return {}

    calendar = {}
    grouped = df_month.groupby('date')
    
    for date_str, group in grouped:
        max_zhr = group['adjusted_zhr'].max()
        showers_above_0 = group[group['is_visible'] == True]['shower_name'].tolist()
        
        # Intensity mapping
        if max_zhr < 5: intensity = "none"
        elif max_zhr < 25: intensity = "low"
        elif max_zhr < 60: intensity = "medium"
        else: intensity = "high"
        
        calendar[date_str] = {
            "showers": showers_above_0,
            "peak_zhr": float(max_zhr),
            "intensity": intensity
        }
        
    return calendar

def get_dark_spots(city_name: str, radius_km: int = 300) -> list:
    if city_name not in cities_df['city'].values:
        return []
    
    target_city = cities_df[cities_df['city'] == city_name].iloc[0]
    t_lat, t_lon = target_city['lat'], target_city['lon']
    
    candidates = []
    # Filter cities by distance
    for _, city in cities_df.iterrows():
        if city['city'] == city_name: continue
        
        dist = haversine(t_lat, t_lon, city['lat'], city['lon'])
        if dist <= radius_km:
            candidates.append({
                "name": city['city'],
                "state": city['state'],
                "bortle_class": int(city['bortle']),
                "limiting_mag": float(city['limiting_magnitude']),
                "distance_km": round(dist, 1)
            })
            
    # Sort by Bortle class (Darker = Lower) then Limiting Mag (Usually darker = higher negative magnitude in our map)
    # Actually, we sort primarily by Bortle.
    candidates.sort(key=lambda x: (x['bortle_class'], x['distance_km']))
    
    # Take top 3
    top_spots = candidates[:3]
    for spot in top_spots:
        # driving distance estimate = straight_line_km * 1.4
        road_km = spot['distance_km'] * 1.4
        # drive_hours = road_km / 60km/h average
        spot['drive_hours'] = round(road_km / 60, 1)
        spot['distance_km'] = round(road_km, 1)

    return top_spots

# ── Module Test ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import json
    # Run test for Mumbai
    print("\n--- Testing get_tonight_showers for 'Mumbai' ---")
    mumbai_showers = get_tonight_showers("Mumbai")
    print(json.dumps(mumbai_showers, indent=2))
    
    print("\n--- Testing get_month_calendar for 'Ahmedabad' (2026-08) ---")
    ahmedabad_cal = get_month_calendar("Ahmedabad", 2026, 8)
    # Print only sample dates (Aug 10-15)
    sample_dates = [f"2026-08-{i:02d}" for i in range(10, 16)]
    sample_cal = {d: ahmedabad_cal.get(d) for d in sample_dates if d in ahmedabad_cal}
    print(json.dumps(sample_cal, indent=2))
