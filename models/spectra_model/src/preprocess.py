import os
import pandas as pd
import numpy as np
import joblib
from pathlib import Path
from sklearn.preprocessing import StandardScaler

# ── Paths ─────────────────────────────────────────────────────────────────────
SRC_DIR = Path(__file__).parent.resolve()
BASE_DIR = SRC_DIR.parent
DATA_DIR = BASE_DIR / "data"
SAVED_DIR = BASE_DIR / "saved"

INPUT_CSV = DATA_DIR / "spectra_combined.csv"

# Ensure directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
SAVED_DIR.mkdir(parents=True, exist_ok=True)

def preprocess():
    if not INPUT_CSV.exists():
        print(f"[!] Input file missing: {INPUT_CSV}")
        return

    print(f"[→] Loading {INPUT_CSV.name}...")
    df_long = pd.read_csv(INPUT_CSV)
    
    # Store mapping of asteroid_id to class_label before pivoting
    # Assuming one label per asteroid
    label_map = df_long.groupby('asteroid_id')['class_label'].first()
    original_count = len(label_map)

    # 1. Pivot wide
    print("[→] Pivoting to wide format...")
    df_wide = df_long.pivot(index='asteroid_id', columns='wavelength_nm', values='reflectance')
    
    # Target wavelengths: 450 to 2450 in steps of 50
    target_wavelengths = np.arange(450, 2451, 50)
    
    # Reindex to include all target wavelengths (adds NaNs for missing ones)
    df_wide = df_wide.reindex(columns=target_wavelengths)
    
    # Linear interpolation per row
    print("[→] Interpolating missing values...")
    # axis=1 for row-wise interpolation
    df_wide = df_wide.interpolate(method='linear', axis=1, limit_direction='both')
    
    # 2. Normalize by 550nm
    print("[→] Normalizing by reflectance at 550nm...")
    if 550.0 not in df_wide.columns:
        print("[!] 550nm column missing after reindexing. Check wavelength range.")
        return
        
    norm_val = df_wide[550.0]
    
    # Drop where 550nm is 0 or NaN
    valid_mask = (norm_val > 0) & (norm_val.notna())
    df_wide = df_wide[valid_mask]
    norm_val = norm_val[valid_mask]
    
    # Divide all columns by 550nm value
    df_wide = df_wide.div(norm_val, axis=0)
    
    # 3. Drop rows with > 30% NaN after interpolation
    print("[→] Removing spectra with more than 30% missing data...")
    nan_threshold = 0.3
    mask_low_nan = df_wide.isnull().mean(axis=1) <= nan_threshold
    df_wide = df_wide[mask_low_nan]
    
    # Final check: any remaining NaNs (e.g. if everything was NaN before interp)
    # Fill remaining NaNs with 0 or drop? User said "Drop rows that still have more than 30% NaN".
    # I'll drop any row that has ANY NaN left just to be safe for ML, 
    # but the instructions say specifically 30% threshold.
    # However, interpolation with limit_direction='both' usually fills everything if there are at least 2 points.
    # If the asteroid had only 1 data point, it would still have NaNs.
    df_wide = df_wide.dropna() # Final cleaning for ML readiness
    
    # 4. Separate features (X), labels (y), and metadata
    asteroid_ids = df_wide.index.values
    X = df_wide.values
    y = label_map.loc[asteroid_ids].values
    
    # 5. Fit Scaler
    print("[→] Fitting StandardScaler...")
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # 6. Save results
    print("[→] Saving processed data...")
    np.save(DATA_DIR / "X_processed.npy", X_scaled)
    np.save(DATA_DIR / "y_labels.npy", y)
    np.save(DATA_DIR / "asteroid_ids.npy", asteroid_ids)
    np.save(DATA_DIR / "wavelengths.npy", target_wavelengths)
    joblib.dump(scaler, SAVED_DIR / "scaler.pkl")
    
    # ── Final Stats ──────────────────────────────────────────────────────────
    print("\n" + "="*40)
    print("PREPROCESSING SUMMARY")
    print("="*40)
    print(f"Shape of X:           {X_scaled.shape}")
    print(f"Asteroids retained:   {len(df_wide)} ({len(df_wide)/original_count:.1%})")
    print("-" * 40)
    print("Class Distribution:")
    print(pd.Series(y).value_counts().to_string())
    print("="*40)

if __name__ == "__main__":
    preprocess()
