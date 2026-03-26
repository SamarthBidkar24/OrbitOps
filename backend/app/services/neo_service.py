import joblib
from app.core.config import settings

class NeoService:
    def __init__(self):
        self.model = None

    def load(self):
        self.model = joblib.load(settings.NEO_MODEL_PATH)

    def predict(self, features: dict):
        if self.model is None:
            raise RuntimeError("NEO model not loaded.")
        # TODO: preprocess features and run inference
        return {}

neo_service = NeoService()
