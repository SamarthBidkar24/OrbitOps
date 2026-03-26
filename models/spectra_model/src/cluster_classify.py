import os
import joblib
import json
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score, classification_report, accuracy_score
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import cross_val_score, StratifiedKFold
from collections import Counter

# ── Paths ─────────────────────────────────────────────────────────────────────
SRC_DIR = Path(__file__).parent.resolve()
BASE_DIR = SRC_DIR.parent
DATA_DIR = BASE_DIR / "data"
SAVED_DIR = BASE_DIR / "saved"

# Load Data
print("[→] Loading embeddings and labels...")
embeddings = np.load(SAVED_DIR / "embeddings.npy")
y_labels = np.load(DATA_DIR / "y_labels.npy", allow_pickle=True)
asteroid_ids = np.load(DATA_DIR / "asteroid_ids.npy", allow_pickle=True)

# ── PART A: KMeans Clustering ─────────────────────────────────────────────────
print("\n" + "="*40)
print("PART A: KMEANS CLUSTERING")
print("="*40)
k_values = [5, 7, 9, 12]
best_k = 0
best_score = -1
best_kmeans = None

for k in k_values:
    # Handle small datasets gracefully
    if k >= len(embeddings): continue
    
    kmeans = KMeans(n_clusters=k, n_init=10, random_state=42)
    cluster_labels = kmeans.fit_predict(embeddings)
    score = silhouette_score(embeddings, cluster_labels)
    print(f"k = {k:2d} | Silhouette Score: {score:.4f}")
    
    if score > best_score:
        best_score = score
        best_k = k
        best_kmeans = kmeans

print(f"[✓] Selected best k = {best_k} (Silhouette: {best_score:.4f})")

# Fit final model (already done for best_k in loop above, but re-init for clarity)
best_kmeans = KMeans(n_clusters=best_k, n_init=10, random_state=42)
final_clusters = best_kmeans.fit_predict(embeddings)

# Map each cluster to its dominant Bus-DeMeo class label
cluster_to_class_map = {}
for i in range(best_k):
    # Get indices of asteroids in this cluster
    indices = np.where(final_clusters == i)[0]
    # Get their true labels
    cluster_labels = [y_labels[idx] for idx in indices if y_labels[idx]]
    
    if cluster_labels:
        # Majority vote
        dominant_label = Counter(cluster_labels).most_common(1)[0][0]
    else:
        dominant_label = "Unknown"
        
    cluster_to_class_map[i] = dominant_label
    print(f"Cluster {i:2d}: Dominant Label = {dominant_label:3s} ({len(indices)} members)")

# Save KMeans models
joblib.dump(best_kmeans, SAVED_DIR / "kmeans.pkl")
joblib.dump(cluster_to_class_map, SAVED_DIR / "cluster_to_class_map.pkl")
print(f"[✓] Saved KMeans results to {SAVED_DIR.name}")

# ── PART B: Random Forest Classifier ──────────────────────────────────────────
print("\n" + "="*40)
print("PART B: RANDOM FOREST CLASSIFICATION")
print("="*40)

# Filter labeled subset
labeled_mask = (y_labels != None) & (y_labels != "") & (y_labels != "nan")
if hasattr(y_labels, "astype"): # Handle potential dtype issues
    labeled_mask = labeled_mask & (y_labels.astype(str) != "nan")

X_labeled = embeddings[labeled_mask]
y_labeled = y_labels[labeled_mask]

print(f"[→] Labeled dataset size: {len(X_labeled)}")

# Encode labels
le = LabelEncoder()
y_encoded = le.fit_transform(y_labeled)

# Train Classifier
rf = RandomForestClassifier(n_estimators=300, max_depth=15, class_weight='balanced', random_state=42)

# 5-fold cross-validation
skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
cv_scores = cross_val_score(rf, X_labeled, y_encoded, cv=skf)
print(f"Cross-Validation Accuracy: {cv_scores.mean():.4f} +/- {cv_scores.std():.4f}")

# Final fit
rf.fit(X_labeled, y_encoded)

# Classification Report (on self for sanity/overfit check, CV is better metric)
y_pred = rf.predict(X_labeled)
print("\nIndividual Class Performance (Training Set):")
print(classification_report(y_encoded, y_pred, target_names=le.classes_))

# Save RF models
joblib.dump(rf, SAVED_DIR / "rf_classifier.pkl")
joblib.dump(le, SAVED_DIR / "label_encoder.pkl")
print(f"[✓] Saved Random Forest results to {SAVED_DIR.name}")

# ── PART C: Composition Descriptions ──────────────────────────────────────────
print("\n" + "="*40)
print("PART C: COMPOSITION DICTIONARY")
print("="*40)

descriptions = {
    "S": {
        "full_name": "Silicaceous (Stony)",
        "composition": "Silicate minerals such as olivine and pyroxene. Rocky and metallic layers.",
        "common_examples": ["Eros", "Itokawa", "Gaspra", "Iris", "Massalia"],
        "mining_potential": "High",
        "mining_reason": "Rich in iron-nickel alloys, magnesium, and precious metals. Solid rock structure favorable for anchoring.",
        "india_connection": "Predominantly linked to Ordinary Chondrite meteorites often found in the Deccan Traps and Rajasthan."
    },
    "C": {
        "full_name": "Carbonaceous",
        "composition": "Hydrated silicates, organics, and carbon. Very low albedo (dark).",
        "common_examples": ["Ceres", "Hygiea", "Mathilde", "Bennu (B-variant)"],
        "mining_potential": "Very High",
        "mining_reason": "High water content (ice/hydrates) which can be split into rocket fuel (H2/O2). Organic compounds for sustainable space farming.",
        "india_connection": "Corresponds to rare Carbonaceous Chondrites like the Vissannapeta fall in Andhra Pradesh."
    },
    "X": {
        "full_name": "Metallic / Core-Representative",
        "composition": "Likely purely Nickel-Iron (M-type) or enstatite chondrites (E-type).",
        "common_examples": ["Psyche", "Kalliope", "Lutetia"],
        "mining_potential": "Extreme",
        "mining_reason": "Rich in high-purity iron, nickel, and Platinum Group Metals (PGMs) worth trillions of dollars.",
        "india_connection": "Metal-rich fragments found near the Lonar Crater impact site share similar metallic properties."
    },
    "D": {
        "full_name": "Dark / Primitive",
        "composition": "Organic-rich silicates, carbon, and anhydrous silicates. Reddish in color.",
        "common_examples": ["Hektor", "Patroclus", "Arrokoth (KBO similarity)"],
        "mining_potential": "Medium",
        "mining_reason": "Critical for understanding early solar system chemistry. Source of complex organics.",
        "india_connection": "Remnant materials from the proto-solar disk, similar to deep-space ice fragments found in Antarctic ice-melt studies in India."
    },
    "V": {
        "full_name": "Vesta-like (Basaltic)",
        "composition": "Basaltic crustal material similar to terrestrial volcanic rock. Rich in pyroxene.",
        "common_examples": ["Vesta", "Magnya"],
        "mining_potential": "Medium",
        "mining_reason": "Differentiated body materials — good for construction materials (regolith) and rare Earth elements.",
        "india_connection": "Direct link to HED meteorites (Howardite, Eucrite, Diogenite) which are studied at PRL, Ahmedabad."
    },
    "B": {
        "full_name": "Blue / Hydrated Carbonaceous",
        "composition": "Sub-type of C-complex. Blue-sloped spectra indicating potential surface alterations or fine grains.",
        "common_examples": ["Pallas", "Bennu", "Ryugu"],
        "mining_potential": "High",
        "mining_reason": "Easily accessible near-Earth targets with high hydration levels. Ideal for water extraction missions.",
        "india_connection": "Similar to the mineralogy of the 2013 Mukundpura CM2 carbonaceous chondrite fall."
    }
}

# Save Descriptions
with open(SAVED_DIR / "class_descriptions.json", "w") as f:
    json.dump(descriptions, f, indent=2)
print(f"[✓] Saved class descriptions to {SAVED_DIR / 'class_descriptions.json'}")
