"""
train.py — Meteor Shower Recommender Logic
===========================================
Recommenda showers visible at a specific Lat/Lon and Solar Longitude.
"""

import pandas as pd
import joblib
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).parent.parent.resolve()
DATA_PATH = BASE_DIR / "data" / "iau_meteor_showers.csv"
MODEL_SAVE_PATH = BASE_DIR / "saved" / "meteor_lookup.pkl"

def prepare_recommender():
    print(f"[→] Loading meteorite data from {DATA_PATH} …")
    if not DATA_PATH.exists():
        print(f"[✗] Dataset not found! Run download.py first.")
        return

    df = pd.read_csv(DATA_PATH)
    
    # Instead of an ML model, we optimize the lookup logic
    # We serialize the full cleaned dataframe as a lookup object
    records = df.dropna(subset=['ra_radiant', 'dec_radiant', 'solar_long_peak']).to_dict('records')
    
    # Save the ready-to-query dataset
    BASE_DIR.joinpath("saved").mkdir(exist_ok=True)
    joblib.dump(records, MODEL_SAVE_PATH)
    print(f"[✓] Recommendation data saved → {MODEL_SAVE_PATH}")

if __name__ == "__main__":
    prepare_recommender()
