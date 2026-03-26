from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    APP_ENV: str = "development"
    SECRET_KEY: str = "change-me"
    ALLOWED_ORIGINS: List[str] = ["http://localhost:5173"]
    DATABASE_URL: str = "sqlite:///./orbitops.db"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    NEO_MODEL_PATH: str = "../models/neo_model/saved/neo_model.pkl"
    SPECTRA_MODEL_PATH: str = "../models/spectra_model/saved/spectra_model.pkl"
    METEOR_MODEL_PATH: str = "../models/meteor_model/saved/meteor_model.pkl"

    class Config:
        env_file = ".env"

settings = Settings()
class Settings(BaseSettings):
    APP_ENV: str = "development"
    SECRET_KEY: str = "change-me"

    # CHANGED: store raw string from .env
    ALLOWED_ORIGINS: str = "http://localhost:5173"

    DATABASE_URL: str = "sqlite:///./orbitops.db"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    NEO_MODEL_PATH: str = "../models/neo_model/saved/neo_model.pkl"
    SPECTRA_MODEL_PATH: str = "../models/spectra_model/saved/spectra_model.pkl"
    METEOR_MODEL_PATH: str = "../models/meteor_model/saved/meteor_model.pkl"

    ANTHROPIC_API_KEY: str = ""
    NASA_API_KEY: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("ALLOWED_ORIGINS", mode="after")
    @classmethod
    def normalize_origins(cls, v: str) -> str:
        # just strip spaces; splitting will be done elsewhere
        return ",".join([p.strip() for p in v.split(",") if p.strip()])

settings = Settings()

def get_allowed_origins() -> list[str]:
    return [o.strip() for o in settings.ALLOWED_ORIGINS.split(",") if o.strip()]
