from dotenv import load_dotenv
import os

load_dotenv()
# TODO: create a hashed topic for the ntfy endpoint and make that a secret
class Config:
    SUPABASE_URL = os.getenv('SUPABASE_URL')
    SUPABASE_API_KEY = os.getenv('SUPABASE_API_KEY')
    SUPABASE_USER_TABLE = 'User Entries'
    SUPABASE_STORAGE_BUCKET = 'Campus-Security-and-Evacuation-System'
    SUPABASE_USER_ENTRIES_STORAGE_PATH = 'user-entries'