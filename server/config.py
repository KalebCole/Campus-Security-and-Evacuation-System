from dotenv import load_dotenv
import os

load_dotenv()

class Config:
    SUPABASE_URL = os.getenv('SUPABASE_URL')
    SUPABASE_API_KEY = os.getenv('SUPABASE_API_KEY')
