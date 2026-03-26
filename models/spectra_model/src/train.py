"""
train.py — Stellar Spectra Classifier Trainer
==============================================
Uses Bus-DeMeo taxonomy data to classify asteroid spectra.
"""

import pandas as pd
import joblib
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.ensemble import ExtraTreesClassifier
from sklearn.metrics import accuracy_score
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).parent.parent.resolve()
DATA_PATH = BASE_DIR / "data" / "spectra_combined.csv"
MODEL_SAVE_PATH = BASE_DIR / "saved" / "spectra_model.pkl"

def train():
    print(f"[→] Loading data from {DATA_PATH} …")
    if not DATA_PATH.exists():
        print(f"[✗] Dataset not found! Run download_smass_manual.py first.")
        return

    df = pd.read_csv(DATA_PATH)

    # Pivot wavelengths into features: [asteroid_id, wl1, wl2, wl3...]
    print("[→] Reshaping spectra into feature vectors …")
    pivot_df = df.pivot(index='asteroid_id', columns='wavelength_nm', values='reflectance').reset_index()
    labels = df.drop_duplicates('asteroid_id')[['asteroid_id', 'class_label']]
    final_df = pivot_df.merge(labels, on='asteroid_id')

    # Drop NaNs
    final_df = final_df.dropna()

    X = final_df.drop(columns=['asteroid_id', 'class_label'])
    y = final_df['class_label']

    le = LabelEncoder()
    y_encoded = le.fit_transform(y)

    X_train, X_test, y_train, y_test = train_test_split(X, y_encoded, test_size=0.2, random_state=42)

    print(f"[→] Training Extra Trees Classifier …")
    clf = ExtraTreesClassifier(n_estimators=200)
    clf.fit(X_train, y_train)

    # Eval
    score = accuracy_score(y_test, clf.predict(X_test))
    print(f"\nAccuracy Score: {score:.4f}")

    # Save
    BASE_DIR.joinpath("saved").mkdir(exist_ok=True)
    joblib.dump({"model": clf, "encoder": le}, MODEL_SAVE_PATH)
    print(f"[✓] Model and Encoder saved → {MODEL_SAVE_PATH}")

if __name__ == "__main__":
    train()
