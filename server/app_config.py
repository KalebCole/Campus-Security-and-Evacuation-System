from dotenv import load_dotenv
import os
from pathlib import Path

# Get the project root directory (one level up from server)
project_root = Path(__file__).parent.parent
dotenv_path = project_root / '.env'

# Load the .env file with the explicit path
load_dotenv(dotenv_path)
# TODO: create a hashed topic for the ntfy endpoint and make that a secret


class Config:
    SUPABASE_URL = os.getenv('SUPABASE_URL')
    SUPABASE_API_KEY = os.getenv('SUPABASE_API_KEY')
    SUPABASE_USER_TABLE = 'User Entries'
    SUPABASE_STORAGE_BUCKET = 'Campus-Security-and-Evacuation-System'
    SUPABASE_USER_ENTRIES_STORAGE_PATH = 'user-entries'
    TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
    TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
    TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER')
    BASE_URL = "http://localhost:5000"
    SESSION_ID = 1
    MOCK_VALUE = False
    SESSION_TIMEOUT = 15  # seconds
    SIMILARITY_THRESHOLD = 0.7  # 70% similarity threshold
