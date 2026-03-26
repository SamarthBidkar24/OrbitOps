"""
train.py — NEO Model Training Script
====================================
Trains three models for OrbitOps:
1. Threat Classifier (Alert/Watch/Monitor)
2. Observatory Recommender (Location selection)
3. Threat Score Regressor (Continuous risk assessment)
"""

import os
import pandas as pd
import numpy as np
import joblib
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestClassifier, GradientBoostingRegressor
from sklearn.metrics import (
    classification_report, 
    confusion_matrix, 
    accuracy_score, 
    r2_score, 
    mean_absolute_error
)

# ── Configuration ─────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent.parent.resolve()
DATA_PATH = BASE_DIR / "data" / "neo_features.csv"
SAVED_DIR = BASE_DIR / "saved"

FEATURES = [
    'dist_km', 'diameter_km', 'v_rel', 'h', 'threat_score',
    'kinetic_energy_megatons', 'days_from_now', 'month'
]

def format_kb(path):
    size_bytes = path.stat().st_size
    return f"{size_bytes / 1024:.2f} KB"

def train_models():
    # 1. Load Data
    if not DATA_PATH.exists():
        print(f"[✗] Dataset not found: {DATA_PATH}")
        return

    print(f"[->] Loading features from {DATA_PATH.name}...")
    df = pd.read_csv(DATA_PATH)
    
    # Save feature names early
    SAVED_DIR.mkdir(exist_ok=True)
    feature_names_path = SAVED_DIR / "feature_names.pkl"
    joblib.dump(FEATURES, feature_names_path)

    # ── MODEL 1: Threat Classifier ───────────────────────────────────────────
    print("\n" + "="*50)
    print("TRAINING MODEL 1: Threat Classifier")
    print("="*50)
    
    X = df[FEATURES]
    y = df['threat_category']
    
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    clf_pipeline = Pipeline([
        ('scaler', StandardScaler()),
        ('rf', RandomForestClassifier(
            n_estimators=200, 
            max_depth=12, 
            class_weight='balanced',
            random_state=42
        ))
    ])
    
    clf_pipeline.fit(X_train, y_train)
    y_pred = clf_pipeline.predict(X_test)
    
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred))
    
    print("\nConfusion Matrix:")
    print(confusion_matrix(y_test, y_pred))
    
    # Feature Importances
    importances = clf_pipeline.named_steps['rf'].feature_importances_
    feat_imp = sorted(zip(FEATURES, importances), key=lambda x: x[1], reverse=True)
    print("\nRanked Feature Importances:")
    for feat, val in feat_imp:
        print(f"  {feat:<25}: {val:.4f}")
        
    model1_path = SAVED_DIR / "threat_classifier.pkl"
    joblib.dump(clf_pipeline, model1_path)

    # ── MODEL 2: Observatory Recommender ─────────────────────────────────────
    print("\n" + "="*50)
    print("TRAINING MODEL 2: Observatory Recommender")
    print("="*50)
    
    # Filter only visible from India
    df_visible = df[df['india_visible'] == 1].copy()
    
    if len(df_visible) < 10:
        print("[!] Not enough visible data to train Observatory Recommender.")
    else:
        X2 = df_visible[FEATURES]
        y2 = df_visible['best_observatory']
        
        X_train2, X_test2, y_train2, y_test2 = train_test_split(X2, y2, test_size=0.2, random_state=42)
        
        rec_pipeline = Pipeline([
            ('scaler', StandardScaler()),
            ('rf', RandomForestClassifier(n_estimators=100, random_state=42))
        ])
        
        rec_pipeline.fit(X_train2, y_train2)
        y_pred2 = rec_pipeline.predict(X_test2)
        
        acc = accuracy_score(y_test2, y_pred2)
        print(f"\nModel Accuracy: {acc:.4f}")
        
        model2_path = SAVED_DIR / "observatory_recommender.pkl"
        joblib.dump(rec_pipeline, model2_path)

    # ── MODEL 3: Threat Score Regressor ──────────────────────────────────────
    print("\n" + "="*50)
    print("TRAINING MODEL 3: Threat Score Regressor")
    print("="*50)
    
    # Note: Target is threat_score. We will drop threat_score from FEATURES for THIS model 
    # to avoid trivial prediction (data leakage), or use it as feature if requested?
    # User said: FEATURES to use includes 'threat_score'. 
    # But target is 'threat_score'. Usually we don't have target in features.
    # However, for a "bonus" regressor, maybe I should use all features EXCEPT threat_score as inputs? 
    # Let's check user list again.
    # User: "Target: threat_score (continuous)"
    # Features requested: includes 'threat_score'. 
    # I'll exclude threat_score from input features for Model 3 to make it realistic.
    
    FEATURES_REG = [f for f in FEATURES if f != 'threat_score']
    
    X3 = df[FEATURES_REG]
    y3 = df['threat_score']
    
    X_train3, X_test3, y_train3, y_test3 = train_test_split(X3, y3, test_size=0.2, random_state=42)
    
    reg_pipeline = Pipeline([
        ('scaler', StandardScaler()),
        ('gbr', GradientBoostingRegressor(n_estimators=100, random_state=42))
    ])
    
    reg_pipeline.fit(X_train3, y_train3)
    y_pred3 = reg_pipeline.predict(X_test3)
    
    r2 = r2_score(y_test3, y_pred3)
    mae = mean_absolute_error(y_test3, y_pred3)
    
    print(f"\nR² Score: {r2:.4f}")
    print(f"MAE     : {mae:.4e}")
    
    model3_path = SAVED_DIR / "threat_regressor.pkl"
    joblib.dump(reg_pipeline, model3_path)

    # ── Final Summary ────────────────────────────────────────────────────────
    print("\n" + "═"*50)
    print("NEO models saved successfully")
    print("═"*50)
    print(f"  • threat_classifier.pkl   : {format_kb(model1_path)}")
    if (SAVED_DIR / "observatory_recommender.pkl").exists():
        print(f"  • observatory_recommender.pkl: {format_kb(SAVED_DIR / 'observatory_recommender.pkl')}")
    print(f"  • threat_regressor.pkl     : {format_kb(model3_path)}")
    print(f"  • feature_names.pkl        : {format_kb(feature_names_path)}")
    print("═"*50)

if __name__ == "__main__":
    train_models()
