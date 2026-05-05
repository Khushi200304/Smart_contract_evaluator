from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    groq_base_url: str = "https://api.groq.com/openai/v1"
    database_url: str = "sqlite:///./data/contracts.db"
    upload_dir: str = "./data/uploads"
    chroma_path: str = "./data/chroma"
    alert_upcoming_days: int = 7
    scheduler_interval_minutes: int = 5


settings = Settings()
