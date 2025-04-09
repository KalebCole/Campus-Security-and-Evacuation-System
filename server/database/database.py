"""
Database initialization and management module.
Provides centralized access to database connections and repositories.
"""
import logging
from app_config import Config
from supabase_client import supabase
from data.repositories.user_repository import UserRepository

# Configure logging
logger = logging.getLogger(__name__)

# Initialize Supabase client (or use None if in mock mode)
if not Config.MOCK_VALUE:
    try:
        db_client = supabase
        logger.info("Supabase client initialized")
    except Exception as e:
        logger.error(f"Failed to initialize Supabase client: {e}")
        db_client = None
else:
    logger.info("Using mock mode, Supabase client not initialized")
    db_client = None

# Initialize repositories
user_repo = UserRepository(supabase_client=db_client)


def get_user_repository():
    """
    Get the UserRepository instance.

    Returns:
        UserRepository: The UserRepository instance
    """
    return user_repo
