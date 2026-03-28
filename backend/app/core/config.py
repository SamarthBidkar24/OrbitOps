from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Application settings
    APP_ENV: str = "development"
    SECRET_KEY: str = "your-default-secret-key-for-dev"
    
    DATABASE_URL: str = "sqlite:///./orbitops.db"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # Model paths
    NEO_MODEL_PATH: str = "../models/neo_model/saved/threat_classifier.pkl"
    SPECTRA_MODEL_PATH: str = "../models/spectra_model/saved/rf_classifier.pkl"
    METEOR_MODEL_PATH: str = "../models/meteor_model/saved/visibility_lookup.parquet"

    # API keys
    ANTHROPIC_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    NASA_API_KEY: str = ""

    # Note: ALLOWED_ORIGINS is NOT here as requested by USER.
    # No complex parsing logic/validators here.
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
