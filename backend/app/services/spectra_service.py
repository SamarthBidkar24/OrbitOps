import joblib
from app.core.config import settings

class SpectraService:
    def __init__(self):
        self.model = None

    def load(self):
        self.model = joblib.load(settings.SPECTRA_MODEL_PATH)

    def predict(self, features: dict):
        if self.model is None:
            raise RuntimeError("Spectra model not loaded.")
        # TODO: preprocess features and run inference
        return {}

spectra_service = SpectraService()
