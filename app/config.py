from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    API_KEY: str
    SUPABASE_URL: str
    SUPABASE_KEY: str
    OCR_SPACE_API_KEY: str
    GEMINI_API_KEY: str = ""
    
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

@lru_cache
def get_settings():
    return Settings()
