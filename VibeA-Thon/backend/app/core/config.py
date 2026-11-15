from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_url: str = "sqlite:///./spendsense.db"
    secret_key: str = "development-only-change-this-secret-key"
    access_token_minutes: int = 10080
    model_config = SettingsConfigDict(env_file=(Path(__file__).resolve().parents[2] / ".env", Path(__file__).resolve().parents[3] / ".env"), extra="ignore")

settings = Settings()
