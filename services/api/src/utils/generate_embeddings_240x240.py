import os
import base64
import requests  # Make sure to install this: pip install requests
import json
import sys
from datetime import datetime
import logging
from PIL import Image, ImageOps  # Added ImageOps
import io

# --- Configuration ---
# Paths are relative to this script's location (api/src/utils)
SAMPLE_IMAGE_DIR = os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "..",  "static", "images", "employees"))
SAMPLE_DATA_SQL_FILE = os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "database", "sample_data.sql"))
# URL of your running DeepFace service
# Assuming DeepFace runs on the host
FACE_REC_EMBED_URL = "http://localhost:5001"
TARGET_RESOLUTION = (240, 240)
# --- End Configuration ---

# Setup basic logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def get_employee_images(image_dir):
    """Finds employee image files and extracts RFID tags."""
    employee_files = {}
    if not os.path.isdir(image_dir):
        logger.error(f"Error: Image directory not found at '{image_dir}'")
        return None

    logger.info(f"Scanning directory: {image_dir}")
    count = 0
    for filename in os.listdir(image_dir):
        if filename.lower().endswith((".jpg", ".jpeg", ".png")):
            # Assuming filename format is EMPXXX.jpg
            rfid_tag = os.path.splitext(filename)[0].upper()
            if rfid_tag.startswith("EMP"):
                employee_files[rfid_tag] = os.path.join(image_dir, filename)
                count += 1
    logger.info(f"Found {count} potential employee images.")
    return employee_files


def get_embedding_for_resized(image_path):
    """Resizes image to TARGET_RESOLUTION, converts to JPEG, and gets embedding."""
    logger.info(f"  Processing {os.path.basename(image_path)}...")
    try:
        # --- Read original image bytes ---
        with open(image_path, "rb") as f:
            original_image_bytes = f.read()

        # --- Open image with Pillow ---
        img = Image.open(io.BytesIO(original_image_bytes))

        # --- Resize the image ---
        # Use thumbnail + padding to maintain aspect ratio and prevent distortion
        img.thumbnail(TARGET_RESOLUTION, Image.Resampling.LANCZOS)
        # Create a new image with a black background (or white: (255, 255, 255))
        new_img = Image.new("RGB", TARGET_RESOLUTION, (0, 0, 0))
        # Calculate position to paste the thumbnail centered
        paste_x = (TARGET_RESOLUTION[0] - img.width) // 2
        paste_y = (TARGET_RESOLUTION[1] - img.height) // 2
        new_img.paste(img, (paste_x, paste_y))
        img = new_img  # Use the padded/resized image
        logger.info(f"    Resized and padded image to {TARGET_RESOLUTION}")

        # --- Convert to standard RGB JPEG ---
        # Ensure image is in RGB format (handles grayscale, RGBA etc.)
        img = img.convert('RGB')
        output_buffer = io.BytesIO()
        img.save(output_buffer, format='JPEG', quality=95)  # Save as JPEG
        converted_jpeg_bytes = output_buffer.getvalue()
        logger.debug(
            f"    Successfully converted resized image to JPEG format.")

        # --- Get Embedding ---
        image_base64_raw = base64.b64encode(
            converted_jpeg_bytes).decode("utf-8")
        image_base64_data_uri = f"data:image/jpeg;base64,{image_base64_raw}"

        endpoint = f"{FACE_REC_EMBED_URL}/represent"
        payload = {
            "img_path": image_base64_data_uri,
            "model_name": "GhostFaceNet",  # Ensure this matches runtime model
            "detector_backend": "retinaface",  # Match runtime detector if possible
            # Allow processing even if face isn't detected by this call
            "enforce_detection": False,
            "align": True,
            "normalization": "base"
        }

        logger.debug(f"    Sending request to {endpoint} for embedding...")
        response = requests.post(
            endpoint, json=payload, timeout=30)  # Increased timeout
        response.raise_for_status()

        result = response.json()

        results_list = result.get("results")
        if isinstance(results_list, list) and len(results_list) > 0:
            # Handle potential multiple faces - take the first one for simplicity
            # TODO: Could add logic to handle multiple faces if needed
            embedding = results_list[0].get("embedding")
            if isinstance(embedding, list):
                logger.info(
                    f"    -> Embedding received ({len(embedding)} dimensions).")
                return embedding
            else:
                logger.error(
                    f"    -> Error: 'embedding' key missing/invalid in DeepFace result: {results_list[0]}")
                return None
        elif isinstance(result.get("embedding"), list):  # Handle older DeepFace format?
            logger.warning(
                "    Received embedding directly, not in 'results' list (older DeepFace format?).")
            return result.get("embedding")
        else:
            # Log cases where no face might have been detected by the /represent call
            logger.error(
                f"    -> Error: Could not find 'results' or 'embedding' in DeepFace response: {result}")
            return None

    except FileNotFoundError:
        logger.error(f"    -> Error: File not found at {image_path}")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(
            f"    -> Error: Failed to connect or communicate with DeepFace service at {FACE_REC_EMBED_URL}: {e}")
        return None
    except Image.UnidentifiedImageError:
        logger.error(
            f"    -> Error: Cannot identify image file (corrupted or unsupported format?): {image_path}")
        return None
    except Exception as e:
        logger.error(
            f"    -> Error: An unexpected error occurred processing {image_path}: {e}", exc_info=True)
        return None


def format_embedding_for_sql(embedding_vector):
    """Formats a list of floats into PostgreSQL vector string format."""
    if not embedding_vector or not isinstance(embedding_vector, list):
        logger.warning("Cannot format invalid embedding vector.")
        return "NULL"
    # Convert elements to string, ensuring sufficient precision
    str_elements = [f"{float(val):.10f}" for val in embedding_vector]
    # Format for pgvector: '[1.2,3.4,...]'
    inner_vector_string = "[" + ",".join(str_elements) + "]"
    # Return the string literal enclosed in single quotes for SQL
    return "'" + inner_vector_string + "'"


def generate_update_statements(employee_images):
    """Generates SQL UPDATE statements for each employee's resized embedding."""
    sql_statements = []
    logger.info("Generating SQL UPDATE statements for resized images...")
    processed_count = 0
    error_count = 0
    for rfid_tag, image_path in employee_images.items():
        embedding = get_embedding_for_resized(
            image_path)  # Call the modified function
        if embedding:
            sql_embedding = format_embedding_for_sql(embedding)
            # Ensure rfid_tag is properly quoted if it's a string
            statement = f"UPDATE employees SET face_embedding = {sql_embedding} WHERE rfid_tag = '{rfid_tag}';"
            sql_statements.append(statement)
            processed_count += 1
        else:
            logger.warning(
                f"    -> Skipping SQL generation for {rfid_tag} due to embedding error.")
            error_count += 1

    logger.info(
        f"Finished processing images. Success: {processed_count}, Errors: {error_count}")
    return sql_statements


def append_sql_to_file(sql_file_path, statements):
    """Appends the generated SQL statements to the specified file."""
    if not statements:
        logger.warning("No SQL statements generated, skipping file update.")
        return False

    if not os.path.isfile(sql_file_path):
        # Attempt to create the directory if it doesn't exist
        sql_dir = os.path.dirname(sql_file_path)
        try:
            os.makedirs(sql_dir, exist_ok=True)
            logger.info(f"Created directory for SQL file: {sql_dir}")
            # Now try opening the file in write mode to create it
            with open(sql_file_path, 'w', encoding='utf-8') as f:
                f.write("-- Sample Data --\n")  # Use escaped newline
            logger.info(f"Created new SQL file: {sql_file_path}")
        except OSError as e:
            # Use escaped newline
            logger.error(
                "\nError: Could not create directory or file at '{sql_file_path}': {e}")
            return False
        except IOError as e:
            logger.error(f"Error creating new SQL file '{sql_file_path}': {e}")
            return False

    logger.info(
        f"Appending {len(statements)} SQL statements to {sql_file_path}...")
    try:
        with open(sql_file_path, 'a', encoding='utf-8') as f:
            f.write("\n-- Auto-generated Embeddings (240x240) ({}) --\n".format(
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            for stmt in statements:
                f.write(stmt + "\n")
            # Use escaped newline
            f.write("-- End Auto-generated Embeddings --\n")
        logger.info("Successfully appended statements to file.")
        return True
    except IOError as e:
        logger.error(f"Error writing to SQL file '{sql_file_path}': {e}")
        return False
    except Exception as e:
        logger.error(
            f"An unexpected error occurred while writing to file: {e}")
        return False


# --- Main Execution ---
if __name__ == "__main__":
    logger.info(
        "Starting script to generate embeddings for resized (240x240) images.")
    logger.info(f"Using DeepFace service at: {FACE_REC_EMBED_URL}")
    logger.info(f"Looking for images in: {SAMPLE_IMAGE_DIR}")
    logger.info(f"Appending SQL statements to: {SAMPLE_DATA_SQL_FILE}")

    employee_image_map = get_employee_images(SAMPLE_IMAGE_DIR)

    if employee_image_map:
        update_statements = generate_update_statements(employee_image_map)
        append_sql_to_file(SAMPLE_DATA_SQL_FILE, update_statements)

        if update_statements:
            logger.info(
                "\n--- Generated SQL Statements (also appended to file) ---")
            # Log only first few and last few for brevity
            limit = 5
            if len(update_statements) > 2 * limit:
                for stmt in update_statements[:limit]:
                    print(stmt)
                print("...")
                for stmt in update_statements[-limit:]:
                    print(stmt)
            else:
                for stmt in update_statements:
                    print(stmt)
            # Use escaped newline
            logger.info("\n--- End of SQL statements ---")
        else:
            # Use escaped newline
            logger.warning("\nNo SQL statements were generated.")
    else:
        # Use escaped newline
        logger.error(
            "\nCould not find employee images or directory. Script aborted.")

    logger.info("Script finished.")
