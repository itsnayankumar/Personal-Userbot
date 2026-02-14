import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    API_ID = int(os.environ.get("API_ID", 0))
    API_HASH = os.environ.get("API_HASH", "")
    SESSION_STRING = os.environ.get("SESSION_STRING", "")
    PORT = int(os.environ.get("PORT", 10000))
    
    # Telegram Channels
    DUMP_CHANNEL_ID = int(os.environ.get("DUMP_CHANNEL_ID", 0))
    LOG_CHANNEL_ID = int(os.environ.get("LOG_CHANNEL_ID", 0))
    
    # Web Security
    DASH_PASSWORD = os.environ.get("DASH_PASSWORD", "admin")
    FLASK_SECRET = os.environ.get("FLASK_SECRET", "super_secret_key")
