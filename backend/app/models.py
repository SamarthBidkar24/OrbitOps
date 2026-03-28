from pathlib import Path
import pickle
import os
from app.core.config import settings

# Global variables for models
neo_model = None
spectra_model = None

def load_neo_model():
    global neo_model
    path = settings.NEO_MODEL_PATH
    if os.path.exists(path):
        with open(path, 'rb') as f:
            neo_model = pickle.load(f)
        print("✓ NEO Model Loaded")
    else:
        print(f"✘ NEO Model NOT Found at {path}")

def load_spectra_model():
    global spectra_model
    path = settings.SPECTRA_MODEL_PATH
    if os.path.exists(path):
        with open(path, 'rb') as f:
            spectra_model = pickle.load(f)
        print("✓ Spectra Model Loaded")
    else:
        print(f"✘ Spectra Model NOT Found at {path}")
