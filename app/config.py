import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    IBM_API_KEY = os.getenv("IBM_API_KEY")
    IBM_BASE_MODEL = os.getenv("IBM_BASE_MODEL", "granite-13b-instruct-v2")
    IBM_PROJECT_ID = os.getenv("IBM_PROJECT_ID", "demo-project-123")
    INITIAL_BUDGET = float(os.getenv("INITIAL_BUDGET", 1000000))
    NEWS_API_KEY = os.getenv("NEWS_API_KEY", "")
    SERPER_API_KEY = os.getenv("SERPER_API_KEY", "")
    IBM_BASE_URL = "https://us-south.ml.cloud.ibm.com"
    
    # Database settings
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./ai_trading.db")
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DB_NAME = os.getenv("DB_NAME", "ai_trading_db")
    DB_USER = os.getenv("DB_USER", "trading_user")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "trading_pass")

settings = Settings()
