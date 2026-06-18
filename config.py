from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    openai_api_key: str
    firecrawl_api_key: str
    google_service_account_json: str
    google_service_account_file: str = "service_account.json"
    google_sheet_id: str
    confidence_threshold: float = 0.75

    # Security
    admin_api_key: Optional[str] = None   # Set this in .env for production
    allowed_origin: str = "*"             # Set to your Railway URL in production
    app_env: str = "development"

    class Config:
        env_file = ".env"


settings = Settings()
