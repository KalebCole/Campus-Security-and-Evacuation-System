from supabase import create_client, Client
from app_config import Config
from dotenv import load_dotenv
import os
from pathlib import Path

# Explicit path to .env
project_root = Path(__file__).parent.parent
dotenv_path = project_root / '.env'

# Load .env first
load_dotenv(dotenv_path)

# Then import config which depends on env vars

# Create Supabase client

supabase_url = Config.SUPABASE_URL
supabase_key = Config.SUPABASE_API_KEY

print(f"SUPABASE_URL: {supabase_url}")
print(f"SUPABASE_KEY exists: {bool(supabase_key)}")

supabase: Client = create_client(supabase_url, supabase_key)
