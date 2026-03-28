import joblib
from app.core.config import settings

class MeteorService:
    def __init__(self):
        self.model = None

    def load(self):
        self.model = joblib.load(settings.METEOR_MODEL_PATH)

    def predict(self, features: dict):
        if self.model is None:
            raise RuntimeError("Meteor model not loaded.")
        # TODO: preprocess features and run inference
        return {}

meteor_service = MeteorService()
