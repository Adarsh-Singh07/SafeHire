from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "OfferShield"
    DEBUG: bool = True
    DATABASE_URL: str = "sqlite+aiosqlite:///./offershield.db"
    
    # AI / LLM APIs
    GROQ_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    HF_TOKEN: str = ""
    GOV_API_KEY: str = ""
    OGD_API_KEY: str = ""  # Fallback naming alias
    SERPER_API_KEY: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'

settings = Settings()
