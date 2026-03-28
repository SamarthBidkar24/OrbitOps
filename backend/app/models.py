import joblib
import os

# Global variables to store models for inference
neo_model = None
spectra_model = None

class DummyModel:
    """Mock model to provide fallback predictions if actual weights are missing."""
    def predict(self, *args, **kwargs):
        # Return a sample prediction structure
        return {"label": "safe", "confidence": 0.55, "dummy": True}

def load_neo_model():
    """Load NEO model from joblib file or fallback to dummy implementation."""
    global neo_model
    # Try multiple common relative paths for development and production
    possible_paths = [
        "models/neo_model.joblib",
        "../../models/neo_model/saved/neo_model.joblib",
        "../models/neo_model/saved/neo_model.joblib"
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            try:
                neo_model = joblib.load(path)
                print("Model loaded: NEO")
                return neo_model
            except Exception as e:
                print(f"Error reading NEO model at {path}: {e}")
                
    neo_model = DummyModel()
    print("Model loaded: NEO (Dummy)")
    return neo_model

def load_spectra_model():
    """Load Spectra classifier from joblib file or fallback to dummy implementation."""
    global spectra_model
    possible_paths = [
        "models/spectra_model.joblib",
        "../../models/spectra_model/saved/spectra_model.joblib",
        "../models/spectra_model/saved/spectra_model.joblib"
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            try:
                spectra_model = joblib.load(path)
                print("Model loaded: Spectra")
                return spectra_model
            except Exception as e:
                print(f"Error reading Spectra model at {path}: {e}")
                
    spectra_model = DummyModel()
    print("Model loaded: Spectra (Dummy)")
    return spectra_model
