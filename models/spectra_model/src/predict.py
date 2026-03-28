import os
import torch
import torch.nn as nn
import joblib
import json
import numpy as np
from pathlib import Path
from sklearn.metrics.pairwise import cosine_similarity

# ── Paths ─────────────────────────────────────────────────────────────────────
SRC_DIR = Path(__file__).parent.resolve()
BASE_DIR = SRC_DIR.parent
DATA_DIR = BASE_DIR / "data"
SAVED_DIR = BASE_DIR / "saved"

# ── Model Architectures (Must match training) ──────────────────────────────────
class EncoderOnly(nn.Module):
    def __init__(self, input_dim=41):
        super(EncoderOnly, self).__init__()
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, 32),
            nn.BatchNorm1d(32),
            nn.ReLU(),
            nn.Linear(32, 16),
            nn.BatchNorm1d(16),
            nn.ReLU(),
            nn.Linear(16, 8),
            nn.BatchNorm1d(8),
            nn.ReLU()
        )
    def forward(self, x):
        return self.encoder(x)

# ── Module Level Loading ───────────────────────────────────────────────────────
print("[->] Loading spectral inference components...")
try:
    # 1. Feature Preprocessing
    scaler = joblib.load(SAVED_DIR / "scaler.pkl")
    
    # 2. Encoder (PyTorch)
    encoder = EncoderOnly(input_dim=41)
    encoder.encoder.load_state_dict(torch.load(SAVED_DIR / "encoder.pt", map_location=torch.device('cpu')))
    encoder.eval()
    
    # 3. Supervised Classification
    rf_clf = joblib.load(SAVED_DIR / "rf_classifier.pkl")
    label_encoder = joblib.load(SAVED_DIR / "label_encoder.pkl")
    
    # 4. Unsupervised Clustering (Fallback)
    kmeans = joblib.load(SAVED_DIR / "kmeans.pkl")
    cluster_map = joblib.load(SAVED_DIR / "cluster_to_class_map.pkl")
    
    # 5. Metadata and Knowledge Base
    with open(SAVED_DIR / "class_descriptions.json", "r") as f:
        class_descriptions = json.load(f)
        
    embeddings_all = np.load(SAVED_DIR / "embeddings.npy")
    X_processed_all = np.load(DATA_DIR / "X_processed.npy")
    y_labels_all = np.load(DATA_DIR / "y_labels.npy", allow_pickle=True)
    asteroid_ids_all = np.load(DATA_DIR / "asteroid_ids.npy", allow_pickle=True)
    
except Exception as e:
    print(f"[!] Error loading inference module: {e}")
    encoder = None
    rf_clf = None

# ── Constants ──────────────────────────────────────────────────────────────────
TARGET_WAVELENGTHS = np.arange(450, 2451, 50) # 41 points

# Realistic mineralogy breakdowns per class
COMPOSITION_BREAKDOWN = {
    "S": [{"mineral": "Olivine", "percent": 40}, {"mineral": "Pyroxene", "percent": 30}, {"mineral": "Iron-Nickel", "percent": 20}, {"mineral": "Feldspar", "percent": 10}],
    "C": [{"mineral": "Carbon compounds", "percent": 50}, {"mineral": "Silicates", "percent": 30}, {"mineral": "Water ice", "percent": 20}],
    "X": [{"mineral": "Iron-Nickel", "percent": 60}, {"mineral": "Silicates", "percent": 25}, {"mineral": "Other metals", "percent": 15}],
    "D": [{"mineral": "Organic compounds", "percent": 55}, {"mineral": "Silicates", "percent": 30}, {"mineral": "Ice", "percent": 15}],
    "V": [{"mineral": "Pyroxene", "percent": 65}, {"mineral": "Olivine", "percent": 20}, {"mineral": "Plagioclase", "percent": 15}],
    "B": [{"mineral": "Phyllosilicates", "percent": 45}, {"mineral": "Carbon", "percent": 35}, {"mineral": "Magnetite", "percent": 20}],
    "Q": [{"mineral": "Olivine", "percent": 45}, {"mineral": "Pyroxene", "percent": 35}, {"mineral": "Iron-Nickel", "percent": 20}]
}

# ── Inference Logic ────────────────────────────────────────────────────────────
def classify_spectrum(wavelengths: list, reflectances: list) -> dict:
    """
    wavelengths: list of floats in nm (e.g. [450, 500, 550, ...])
    reflectances: list of floats matching wavelengths
    """
    if encoder is None:
        return {"error": "Inference module components (Encoder/RF) failed to load."}

    # 1. Interpolate onto standard grid (450-2450nm)
    clean_reflectances = np.interp(TARGET_WAVELENGTHS, wavelengths, reflectances)
    clean_reflectances = np.clip(clean_reflectances, 0, 3.0)
    
    # 2. Normalize to 550nm = 1.0
    val_550 = clean_reflectances[2]
    norm_reflectance = clean_reflectances / val_550 if val_550 > 0 else clean_reflectances
        
    # 3. Apply StandardScaler
    scaled_feats = scaler.transform(norm_reflectance.reshape(1, -1))
    
    # 4. Extract 8-dim embedding via Encoder
    with torch.no_grad():
        feats_tensor = torch.FloatTensor(scaled_feats)
        embedding = encoder(feats_tensor).cpu().numpy() # (1, 8)
        
    # 5. Predict Classification
    try:
        if rf_clf is not None:
            probs = rf_clf.predict_proba(embedding)
            conf = float(np.max(probs))
            class_idx = np.argmax(probs)
            pred_class = label_encoder.classes_[class_idx]
        else:
            cluster_id = kmeans.predict(embedding)[0]
            pred_class = cluster_map.get(cluster_id, "Unknown")
            conf = 0.5
    except:
        pred_class = "Unknown"
        conf = 0.0

    # 6. Metadata Lookup
    base_class = pred_class[:1]
    if pred_class.startswith("Sq") or pred_class.startswith("Sw"): base_class = "S"
    if pred_class.startswith("Ch"): base_class = "C"
    
    info = class_descriptions.get(base_class, {})
    
    # 7. Mean Class Spectrum
    # Find all training samples of this class
    class_indices = np.where(y_labels_all == pred_class)[0]
    if len(class_indices) > 0:
        mean_scaled = np.mean(X_processed_all[class_indices], axis=0)
        # Inverse transform using scaler
        mean_raw = scaler.inverse_transform(mean_scaled.reshape(1, -1)).flatten()
    else:
        # Fallback to current spectrum if class unknown or no samples
        mean_raw = norm_reflectance
        
    mean_spectrum_list = [
        {"wavelength": int(TARGET_WAVELENGTHS[i]), "reflectance": round(float(mean_raw[i]), 4)}
        for i in range(len(TARGET_WAVELENGTHS))
    ]
    
    # 8. Nearest Asteroids from Latent Space (Cosine Similarity on 8-dim embeddings)
    similarities = cosine_similarity(embedding, embeddings_all).flatten()
    nearest_indices = np.argsort(similarities)[::-1][:3]
    nearest_asteroids = asteroid_ids_all[nearest_indices].tolist()

    # 9. Result Construction
    return {
        "predicted_class": pred_class,
        "class_full_name": info.get("full_name", "Unknown"),
        "confidence": round(conf, 2),
        "composition": info.get("composition"),
        "mining_potential": info.get("mining_potential"),
        "mining_reason": info.get("mining_reason"),
        "india_connection": info.get("india_connection"),
        "composition_breakdown": COMPOSITION_BREAKDOWN.get(base_class, COMPOSITION_BREAKDOWN["S"]),
        "nearest_known_asteroids": nearest_asteroids,
        "mean_class_spectrum": mean_spectrum_list,
        "spectral_profile": {
            "wavelengths": TARGET_WAVELENGTHS.tolist(),
            "reflectances": norm_reflectance.tolist()
        }
    }

# ── Module Test ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    test_wav = [500, 1000, 1500, 2000, 2400]
    test_ref = [0.9,  0.8,  1.2,  1.1,  1.3]
    
    print("\n--- Testing classify_spectrum with synthetic curve ---")
    result = classify_spectrum(test_wav, test_ref)
    
    if "error" in result:
        print(f"FAILED: {result['error']}")
    else:
        print(f"Prediction: {result['predicted_class']} ({result['class_full_name']})")
        print(f"Confidence: {result['confidence'] * 100}%")
        print(f"Composition Breakdown: {result['composition_breakdown']}")
        print(f"Mean Spectrum Count:  {len(result['mean_class_spectrum'])} points")
        print(f"Nearest:    {result['nearest_known_asteroids']}")
