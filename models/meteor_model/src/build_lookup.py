import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from multiprocessing import Pool
from astropy import units as u
from astropy.time import Time
from astropy.coordinates import EarthLocation, SkyCoord, AltAz

# ── Paths ─────────────────────────────────────────────────────────────────────
SRC_DIR = Path(__file__).parent.resolve()
BASE_DIR = SRC_DIR.parent
DATA_DIR = BASE_DIR / "data"
SAVED_DIR = BASE_DIR / "saved"

SHOWERS_CSV = DATA_DIR / "iau_meteor_showers.csv"
CITIES_CSV = DATA_DIR / "india_cities_bortle.csv"
OUTPUT_PARQUET = SAVED_DIR / "visibility_lookup.parquet"

# Ensure output directory exists
SAVED_DIR.mkdir(parents=True, exist_ok=True)

# ── Load and Filter Data ──────────────────────────────────────────────────────
def load_data():
    if not SHOWERS_CSV.exists() or not CITIES_CSV.exists():
        print(f"[!] Input files missing: {SHOWERS_CSV} or {CITIES_CSV}")
        sys.exit(1)

    # Load showers
    showers_df = pd.read_csv(SHOWERS_CSV)
    # The user mentioned "confirmed" showers. Check if status column exists. 
    # Based on earlier view_file, it doesn't. We filter by ZHR >= 5.
    if 'status' in showers_df.columns:
        showers_df = showers_df[showers_df['status'].str.lower() == 'confirmed']
    
    showers_df = showers_df[showers_df['zhr'] >= 5].copy()
    print(f"[✓] Loaded {len(showers_df)} showers (ZHR >= 5).")

    # Load cities
    cities_df = pd.read_csv(CITIES_CSV)
    # Ensure population is numeric for sorting
    cities_df['population'] = pd.to_numeric(cities_df['population'], errors='coerce').fillna(0)
    top_cities = cities_df.sort_values(by='population', ascending=False).head(200).copy()
    print(f"[✓] Selected top {len(top_cities)} cities by population.")
    
    return showers_df, top_cities

# ── Core Computation ──────────────────────────────────────────────────────────
def process_city(args):
    """
    Computes meteor visibility for a single city across all showers and dates.
    Uses vectorization for significant performance improvement.
    """
    city_data, showers_df, dates, city_idx, total_cities = args
    print(f"Processing city {city_idx} of {total_cities}: {city_data['city']}...")

    city_name = city_data['city']
    lat, lon = city_data['lat'], city_data['lon']
    limiting_mag = city_data.get('limiting_magnitude', -4.0)
    
    location = EarthLocation(lat=lat*u.deg, lon=lon*u.deg, height=0*u.m)
    
    # 1. Prepare Times
    # For each date (365), we want to check 11 hours (-4 to +6 around midnight IST)
    # total_times = 365 * 11 = 4015
    hour_offsets = np.arange(-4, 7) # -4, -3, -2, -1, 0, 1, 2, 3, 4, 5, 6
    
    # Base times in UTC (Midnight IST = UTC + 5.5 => midnight_UTC = midnight_IST - 5.5)
    base_times_utc = Time(dates) - 5.5 * u.hour
    
    # Grid of all times to check
    # base_times_utc is (365,)
    # hour_offsets is (11,)
    # all_times is (365, 11)
    all_times = (base_times_utc[:, None] + hour_offsets * u.hour).flatten()
    
    # 2. Prepare SkyCoords for all showers
    # showers_df has e.g. 40 rows.
    shower_coords = SkyCoord(ra=showers_df['ra_radiant'].values*u.deg, 
                             dec=showers_df['dec_radiant'].values*u.deg, 
                             frame='icrs')
    num_showers = len(shower_coords)
    num_dates = len(dates)
    num_hours = len(hour_offsets)

    # 3. Transform to AltAz
    # all_times is (4015,)
    altaz_frame = AltAz(obstime=all_times, location=location)
    
    # Broadcast shower_coords against altaz_frame
    # results_altaz is (num_showers, 4015)
    # Using [:, None] to broadcast coordinates against time grid
    results_altaz = shower_coords[:, None].transform_to(altaz_frame)
    all_alts = results_altaz.alt.deg # (num_showers, 4015)
    all_azs = results_altaz.az.deg   # (num_showers, 4015)
    
    # Reshape to (num_showers, num_dates, num_hours)
    all_alts_3d = all_alts.reshape(num_showers, num_dates, num_hours)
    all_azs_3d = all_azs.reshape(num_showers, num_dates, num_hours)
    
    # 4. Extract midnight values (indexed at hour offset 0, which is at hour_offsets[4])
    # Note: hour_offsets = [-4, -3, -2, -1, 0, 1, 2, 3, 4, 5, 6]
    # idx of 0 is 4.
    midnight_idx = 4
    midnight_alts = all_alts_3d[:, :, midnight_idx] # (num_showers, num_dates)
    
    # 5. Extract best hour values (max altitude across the 11 hours)
    best_hour_indices = np.argmax(all_alts_3d, axis=2) # (num_showers, num_dates)
    best_hours = hour_offsets[best_hour_indices] % 24  # (num_showers, num_dates)
    
    # 6. Build final list
    # Flattening for efficient dataframe creation
    city_results = []
    
    # Pre-calculate visibility and adjusted ZHR for midnight
    zhr_values = showers_df['zhr'].values[:, None] # (num_showers, 1) to broadcast across dates
    is_visible = midnight_alts > 10
    adj_zhr = zhr_values * np.sin(np.radians(midnight_alts))
    adj_zhr[~is_visible] = 0.0
    
    date_strings = [dt.strftime('%Y-%m-%d') for dt in dates]
    shower_codes = showers_df['shower_code'].values
    shower_names = showers_df['name'].values

    for s_idx in range(num_showers):
        code = shower_codes[s_idx]
        name = shower_names[s_idx]
        for d_idx in range(num_dates):
            city_results.append({
                'city': city_name,
                'date': date_strings[d_idx],
                'shower_code': code,
                'shower_name': name,
                'is_visible': bool(is_visible[s_idx, d_idx]),
                'radiant_altitude_deg': round(float(midnight_alts[s_idx, d_idx]), 2),
                'adjusted_zhr': round(float(adj_zhr[s_idx, d_idx]), 2),
                'best_viewing_hour_ist': int(best_hours[s_idx, d_idx]),
                'limiting_mag': round(limiting_mag, 2)
            })
            
    return city_results

# ── Main Execution ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    showers_df, top_cities = load_data()
    
    # Date range: today to today + 365 days
    start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    dates = [start_date + timedelta(days=i) for i in range(365)]
    
    # Prepare arguments for multiprocessing
    args_list = []
    total_cities = len(top_cities)
    for i, (_, city_row) in enumerate(top_cities.iterrows(), 1):
        args_list.append((city_row.to_dict(), showers_df, dates, i, total_cities))
    
    print(f"\n[→] Starting computation using {os.cpu_count()} cores...")
    
    # Use Pool to parallelize across cities
    with Pool() as pool:
        results_nested = pool.map(process_city, args_list)
    
    # Flatten results
    print("\n[→] Flattening and saving results...")
    final_results = [item for sublist in results_nested for item in sublist]
    lookup_df = pd.DataFrame(final_results)
    
    # Save as Parquet
    lookup_df.to_parquet(OUTPUT_PARQUET, compression='snappy')
    
    # ── Summary and Sample ──────────────────────────────────────────────────
    print(f"\n[✓] PRE-COMPUTATION COMPLETE")
    print("-" * 40)
    print(f"File saved to: {OUTPUT_PARQUET}")
    print(f"File size:     {os.path.getsize(OUTPUT_PARQUET) / (1024*1024):.2f} MB")
    print(f"Total rows:    {len(lookup_df):,}")
    print("-" * 40)
    
    # Mumbai + Perseids 2025-08-12 sample (or closest year)
    # The request said Perseids 2025-08-12, but we are running for next 365 days.
    # Current date is 2026-03-26. So 2025-08-12 is in the past.
    # I will check for the next Perseids peak in the range. 
    # Perseids peak around Aug 12. So Aug 12, 2026.
    sample_city = "Mumbai"
    sample_shower = "PER"
    sample_date = "2026-08-12"
    
    sample = lookup_df[(lookup_df['city'] == sample_city) & 
                       (lookup_df['shower_code'] == sample_shower) & 
                       (lookup_df['date'] == sample_date)]
    
    if not sample.empty:
        print(f"\n[!] Sample for {sample_city} | {sample_shower} | {sample_date}:")
        print(sample.to_string(index=False))
    else:
        # Fallback to any Mumbai sample
        mumbai_sample = lookup_df[lookup_df['city'] == sample_city].head(1)
        if not mumbai_sample.empty:
             print(f"\n[!] (Sample {sample_date} not in range, showing {sample_city} first entry):")
             print(mumbai_sample.to_string(index=False))
