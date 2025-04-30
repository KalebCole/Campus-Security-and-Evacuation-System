import logging
from typing import Optional
from flask import current_app
from supabase import Client
from urllib.parse import urlparse  # Added for URL parsing

logger = logging.getLogger(__name__)


def upload_image_to_supabase(image_bytes: bytes, file_name: str) -> Optional[str]:
    """Uploads image bytes to Supabase Storage and returns the public URL.

    Args:
        image_bytes: The raw bytes of the image file.
        file_name: The desired file name (including extension and any folder path)
                   to use in the bucket.
                   e.g., "employees/employee_uuid.jpg" or "verification_images/session_id.jpg".

    Returns:
        The public URL of the uploaded file, or None if the upload failed.
    """
    try:
        # Get Supabase client and bucket name from Flask app context
        supabase: Client = current_app.supabase_client
        bucket_name: str = current_app.config.get('SUPABASE_BUCKET_NAME')

        if not supabase:
            logger.error(
                "Supabase client not initialized or available in app context.")
            return None
        if not bucket_name:
            logger.error("SUPABASE_BUCKET_NAME not configured in Flask app.")
            return None

        # Content type will be
        content_type = 'image/jpeg'  # Default assumption
        # Extract file extension correctly even with folders in the path
        if '.' in file_name:
            ext = file_name.rsplit('.', 1)[1].lower()
            if ext == 'png':
                content_type = 'image/png'
            elif ext == 'gif':
                content_type = 'image/gif'
        # else: handle cases without extension if needed

        logger.info(
            f"Uploading {file_name} ({content_type}) to Supabase bucket '{bucket_name}'")

        # --- Using newer supabase-py v2 style (which raises exceptions on failure) ---
        upload_response = supabase.storage.from_(bucket_name).upload(
            path=file_name,
            file=image_bytes,
            file_options={"content-type": content_type,
                          "cache-control": "3600"}
        )
        # If no exception is raised, upload is presumed successful in v2
        # Log raw response if needed
        logger.debug(f"Supabase upload response raw: {upload_response}")
        # ---------------------------------------------------------------------

        # Get the public URL (ensure bucket is public)
        public_url_response = supabase.storage.from_(
            bucket_name).get_public_url(file_name)

        # Check if the response is a URL string (newer versions return the URL directly)
        if isinstance(public_url_response, str):
            logger.info(
                f"Successfully uploaded {file_name}. Public URL: {public_url_response}")
            return public_url_response
        else:
            # Handle older response format or potential errors if needed
            logger.error(
                f"Could not get public URL for {file_name}. Response: {public_url_response}")
            return None

    except Exception as e:
        # Catch specific Supabase exceptions if the library defines them
        logger.error(
            f"Error uploading {file_name} to Supabase: {e}", exc_info=True)
        return None


def extract_object_path_from_url(url: str) -> Optional[str]:
    """Extracts the object path (e.g., 'folder/file.jpg') from a Supabase public URL.

    Assumes the URL format is like:
    https://<project_ref>.supabase.co/storage/v1/object/public/<bucket_name>/<object_path>

    Args:
        url: The full public URL from Supabase Storage.

    Returns:
        The extracted object path (e.g., 'employees/uuid_profile.jpg') or None if parsing fails.
    """
    if not url:
        return None
    try:
        parsed_url = urlparse(url)
        path_parts = parsed_url.path.split('/')
        # Find the index of 'public' and expect bucket name and path afterwards
        # Example path: /storage/v1/object/public/cses-images/employees/image.jpg
        # Indices:        0       1  2      3       4       5            6...
        if 'public' in path_parts:
            public_index = path_parts.index('public')
            # Bucket name is next, path starts after bucket name
            if len(path_parts) > public_index + 2:
                # Join the rest of the parts to form the object path
                object_path = '/'.join(path_parts[public_index + 2:])
                logger.debug(
                    f"Extracted object path '{object_path}' from URL '{url}'")
                return object_path
            else:
                logger.warning(
                    f"URL path '{parsed_url.path}' doesn't contain enough parts after '/public/'")
                return None
        else:
            logger.warning(
                f"'/public/' not found in URL path: {parsed_url.path}")
            return None
    except Exception as e:
        logger.error(f"Error parsing URL '{url}': {e}", exc_info=True)
        return None


def delete_image_from_supabase(object_path: str) -> bool:
    """Deletes an object from Supabase Storage based on its path within the bucket.

    Args:
        object_path: The path to the object within the bucket (e.g., "employees/uuid.jpg").

    Returns:
        True if deletion was successful or the object didn't exist, False otherwise.
    """
    if not object_path:
        logger.warning("Deletion skipped: object_path is empty.")
        return False

    try:
        # Get Supabase client and bucket name from Flask app context
        supabase: Client = current_app.supabase_client
        bucket_name: str = current_app.config.get('SUPABASE_BUCKET_NAME')

        if not supabase:
            logger.error(
                "Supabase client not initialized or available in app context. Cannot delete.")
            return False
        if not bucket_name:
            logger.error("SUPABASE_BUCKET_NAME not configured. Cannot delete.")
            return False

        logger.info(
            f"Attempting to delete object '{object_path}' from bucket '{bucket_name}'...")

        # Supabase storage remove method expects a list of paths
        response = supabase.storage.from_(bucket_name).remove([object_path])

        # Check response (newer versions might return data or raise exceptions)
        # Log the response for debugging
        logger.debug(f"Supabase delete response: {response}")

        # Basic check: If no exception occurred, assume success or file didn't exist.
        # More specific error handling might be needed based on supabase-py version behavior.
        # For example, check if response indicates success or 'Not Found'.
        # If response is a list, check if the relevant item indicates success.
        # For now, we assume absence of exception means it's okay.
        logger.info(
            f"Delete operation completed for object '{object_path}'.")
        return True

    except Exception as e:
        # Catch specific Supabase exceptions if available, e.g., StorageError
        # Check if the error indicates the file was not found (which is okay for deletion)
        # This depends heavily on the exception types raised by supabase-py
        error_message = str(e).lower()
        if 'not found' in error_message or 'does not exist' in error_message:
            logger.warning(
                f"Object '{object_path}' not found during deletion attempt, considering successful.")
            return True  # Treat "not found" as success for a delete operation
        else:
            logger.error(
                f"Error deleting object '{object_path}' from Supabase: {e}", exc_info=True)
            return False
