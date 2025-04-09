"""
User repository module to handle all user-related database operations.
"""
import logging
import time
from typing import List, Dict, Optional, Any, Union
from app_config import Config

# Configure logging
logger = logging.getLogger(__name__)


class UserRepository:
    """
    Repository class for user-related database operations.
    Handles interactions with both mock data and actual database.
    """

    def __init__(self, supabase_client=None, mock_mode=None):
        """
        Initialize the user repository.

        Args:
            supabase_client: Supabase client instance for database operations
            mock_mode: Whether to use mock data (defaults to Config.MOCK_VALUE if None)
        """
        self.supabase = supabase_client
        self.mock_mode = Config.MOCK_VALUE if mock_mode is None else mock_mode

        # Mocked user data for testing
        self.mock_db = [
            {
                "id": 1,
                "name": "Bob",
                "role": "Supervisor",
                "rfid_tag": "123456",
                "facial_embedding": [0.1] * 128,
                "image_url": "https://images.pexels.com/photos/1222271/pexels-photo-1222271.jpeg?cs=srgb&dl=pexels-justin-shaifer-501272-1222271.jpg&fm=jpg"
            },
            {
                "id": 2,
                "name": "Rob",
                "rfid_tag": "654321",
                "facial_embedding": [0.2] * 128,
                "role": "Software Engineer",
                "image_url": "https://images.pexels.com/photos/1222271/pexels-photo-1222271.jpeg?cs=srgb&dl=pexels-justin-shaifer-501272-1222271.jpg&fm=jpg"
            },
            {
                "id": 3,
                "name": "Charlie",
                "rfid_tag": "789012",
                "facial_embedding": [0.3] * 128,
                "role": "Hardware Engineer",
                "image_url": "https://images.pexels.com/photos/1222271/pexels-photo-1222271.jpeg?cs=srgb&dl=pexels-justin-shaifer-501272-1222271.jpg&fm=jpg"
            }
        ]

    def get_user_by_rfid(self, rfid_tag: str, mock: bool = None) -> Optional[Dict[str, Any]]:
        """
        Query user by RFID tag from either mock database or actual database.

        Args:
            rfid_tag: The RFID tag to search for
            mock: Whether to use mock data (overrides instance setting if provided)

        Returns:
            User data dictionary if found, None otherwise
        """
        use_mock = self.mock_mode if mock is None else mock
        logger.info(
            f"[DB Query] Starting RFID query operation - RFID: {rfid_tag}, Mock Mode: {use_mock}")
        start_time = time.time()

        if use_mock:
            logger.debug(f"[Mock DB] Searching for RFID {rfid_tag}")
            for user in self.mock_db:
                if user["rfid_tag"] == rfid_tag:
                    logger.info(
                        f"[Mock DB] Found user for RFID {rfid_tag}: {user['name']}")
                    return user
            logger.info(f"[Mock DB] No user found for RFID {rfid_tag}")
            return None
        else:
            # Use actual database
            if not self.supabase:
                logger.error("[Real DB] No Supabase client provided")
                return None

            logger.debug(f"[Real DB] Querying database for RFID {rfid_tag}")
            try:
                response = self.supabase.table('users').select(
                    '*').eq('rfid_tag', rfid_tag).execute()
                if response.data:
                    return response.data[0]
            except Exception as e:
                logger.error(f"[Real DB] Error querying database: {e}")
            return None

    def get_all_users(self, mock: bool = None) -> List[Dict[str, Any]]:
        """
        Query all users from either mock database or actual database.

        Args:
            mock: Whether to use mock data (overrides instance setting if provided)

        Returns:
            List of user data dictionaries
        """
        use_mock = self.mock_mode if mock is None else mock

        if use_mock:
            logger.debug("[Mock DB] Returning all users")
            return self.mock_db
        else:
            # Use actual database
            if not self.supabase:
                logger.error("[Real DB] No Supabase client provided")
                return []

            logger.debug("[Real DB] Querying all users from database")
            try:
                response = self.supabase.table('users').select('*').execute()
                return response.data if response.data else []
            except Exception as e:
                logger.error(f"[Real DB] Error querying database: {e}")
            return []

    def create_user(self, user_data: Dict[str, Any], mock: bool = None) -> Optional[Dict[str, Any]]:
        """
        Create a new user in the database.

        Args:
            user_data: User data dictionary
            mock: Whether to use mock data (overrides instance setting if provided)

        Returns:
            Created user data if successful, None otherwise
        """
        use_mock = self.mock_mode if mock is None else mock

        if use_mock:
            # Generate a new ID
            new_id = max([user["id"] for user in self.mock_db]) + 1
            user_data["id"] = new_id
            self.mock_db.append(user_data)
            logger.info(f"[Mock DB] Created user: {user_data['name']}")
            return user_data
        else:
            # Use actual database
            if not self.supabase:
                logger.error("[Real DB] No Supabase client provided")
                return None

            logger.debug(
                f"[Real DB] Creating user: {user_data.get('name', 'unknown')}")
            try:
                response = self.supabase.table(
                    'users').insert(user_data).execute()
                if response.data:
                    return response.data[0]
            except Exception as e:
                logger.error(f"[Real DB] Error creating user: {e}")
            return None
