import os
import base64
import requests  # Make sure to install this: pip install requests
import json
import sys
from datetime import datetime  # Added for timestamp in file
import logging
from PIL import Image
import io


# current path: Senior Capstone/api/utils/generate_embeddings_for_sample_data.py
# --- Configuration ---
# Paths are relative to this script's location (api/src/utils)
SAMPLE_IMAGE_DIR = os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "..",  "static", "images", "employees"))
SAMPLE_DATA_SQL_FILE = os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "database", "sample_data.sql"))
# URL of your running DeepFace service (when script runs on HOST)
FACE_REC_EMBED_URL = "http://localhost:5001"
# --- End Configuration ---

logger = logging.getLogger(__name__)


def get_employee_images(image_dir):
    """Finds employee image files and extracts RFID tags."""
    employee_files = {}
    abs_image_dir = os.path.abspath(image_dir)  # Get absolute path for clarity
    if not os.path.isdir(abs_image_dir):
        print(
            f"Error: Image directory not found at '{abs_image_dir}'", file=sys.stderr)
        return None

    print(f"Scanning directory: {abs_image_dir}")
    for filename in os.listdir(abs_image_dir):
        if filename.lower().endswith((".jpg", ".jpeg", ".png")):
            # Assuming filename format is EMPXXX.jpg
            rfid_tag = os.path.splitext(filename)[0].upper()
            if rfid_tag.startswith("EMP"):
                employee_files[rfid_tag] = os.path.join(
                    abs_image_dir, filename)  # Store absolute path
    print(f"Found {len(employee_files)} employee images.")
    return employee_files


def get_embedding(image_path):
    """Gets embedding for a single image file via DeepFace /represent endpoint.
       Includes conversion to standard JPEG format first.
    """
    print(f"  Processing {os.path.basename(image_path)}...")
    try:
        # --- Read original image bytes ---
        with open(image_path, "rb") as f:
            original_image_bytes = f.read()

        # --- Convert to standard RGB JPEG using Pillow ---
        converted_jpeg_bytes = None
        try:
            img = Image.open(io.BytesIO(original_image_bytes))
            # Ensure image is in RGB format (handles grayscale, RGBA etc.)
            img = img.convert('RGB')
            # Save to an in-memory buffer as JPEG
            output_buffer = io.BytesIO()
            img.save(output_buffer, format='JPEG')
            converted_jpeg_bytes = output_buffer.getvalue()
            logger.debug(
                f"Successfully converted image {os.path.basename(image_path)} to JPEG format.")
        except Exception as convert_err:
            logger.error(
                f"    -> Pillow conversion failed for {image_path}: {convert_err}", exc_info=True)
            # Fallback: try sending original bytes if conversion fails? Or just fail?
            # For now, let's fail if conversion fails, as the original might be the problem.
            return None
        # ----------------------------------------------------

        # Use converted bytes for Base64 encoding
        image_base64_raw = base64.b64encode(
            converted_jpeg_bytes).decode("utf-8")
        # Now always use jpeg for the data URI prefix
        image_base64_data_uri = f"data:image/jpeg;base64,{image_base64_raw}"

        # Construct the correct URL and payload for DeepFace /represent
        endpoint = f"{FACE_REC_EMBED_URL}/represent"
        payload = {
            "img_path": image_base64_data_uri,
            "model_name": "GhostFaceNet",
            "detector_backend": "opencv"
        }

        logger.debug(
            f"Sending request to {endpoint} with payload keys: {list(payload.keys())}")
        response = requests.post(
            endpoint, json=payload, timeout=15)  # Target /represent
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)

        result = response.json()

        # Updated response parsing for DeepFace /represent
        results_list = result.get("results")
        if isinstance(results_list, list) and len(results_list) > 0:
            embedding = results_list[0].get("embedding")
            if isinstance(embedding, list):
                print(
                    f"    -> Embedding received ({len(embedding)} dimensions).")
                return embedding
            else:
                print(
                    f"    -> Error: 'embedding' key missing/invalid in DeepFace result: {results_list[0]}", file=sys.stderr)
                return None
        else:
            print(
                f"    -> Error: 'results' key missing or not a list in DeepFace response: {result}", file=sys.stderr)
            return None

    except FileNotFoundError:
        print(f"    -> Error: File not found at {image_path}", file=sys.stderr)
        return None
    except requests.exceptions.RequestException as e:
        print(
            f"    -> Error: Failed to connect or communicate with DeepFace service at {endpoint}: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(
            f"    -> Error: An unexpected error occurred processing {image_path}: {e}", file=sys.stderr)
        return None


def format_embedding_for_sql(embedding_vector):
    """Formats a list of floats into PostgreSQL ARRAY string format."""
    if not embedding_vector:
        return "NULL"
    # Convert elements to string, handling potential precision
    str_elements = [f"{val:.8f}" for val in embedding_vector]
    return f"ARRAY[{','.join(str_elements)}]"


def generate_update_statements(employee_images):
    """Generates SQL UPDATE statements for each employee embedding."""
    sql_statements = []
    print("\nGenerating SQL UPDATE statements...")
    for rfid_tag, image_path in employee_images.items():
        embedding = get_embedding(image_path)
        if embedding:
            sql_embedding = format_embedding_for_sql(embedding)
            statement = f"UPDATE employees SET face_embedding = {sql_embedding} WHERE rfid_tag = '{rfid_tag}';"
            sql_statements.append(statement)
        else:
            print(
                f"    -> Skipping SQL generation for {rfid_tag} due to previous errors.")

    return sql_statements


def append_sql_to_file(sql_file_path, statements):
    """Appends the generated SQL statements to the specified file."""
    abs_sql_file_path = os.path.abspath(sql_file_path)
    if not statements:
        print("\nNo SQL statements generated, skipping file update.", file=sys.stderr)
        return False

    if not os.path.isfile(abs_sql_file_path):
        print(
            f"\nError: Target SQL file not found at '{abs_sql_file_path}'", file=sys.stderr)
        return False

    print(
        f"\nAppending {len(statements)} SQL statements to {abs_sql_file_path}...")
    try:
        with open(abs_sql_file_path, 'a', encoding='utf-8') as f:  # Open in append mode
            f.write("\n\n-- Auto-generated Embeddings ({}) --\n".format(
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            for stmt in statements:
                f.write(stmt + "\n")  # Write each statement on a new line
            f.write("-- End Auto-generated Embeddings --\n")
        print("Successfully appended statements to file.")
        return True
    except IOError as e:
        print(
            f"Error writing to SQL file '{abs_sql_file_path}': {e}", file=sys.stderr)
        return False
    except Exception as e:
        print(
            f"An unexpected error occurred while writing to file: {e}", file=sys.stderr)
        return False


# --- Main Execution ---
if __name__ == "__main__":
    employee_image_map = get_employee_images(SAMPLE_IMAGE_DIR)

    if employee_image_map:
        update_statements = generate_update_statements(employee_image_map)

        # Append generated statements to the SQL file
        append_sql_to_file(SAMPLE_DATA_SQL_FILE, update_statements)

        # Optionally, still print them for verification
        if update_statements:
            print("\n--- Generated SQL Statements (also appended to file) ---")
            for stmt in update_statements:
                print(stmt)
            print("\n--- End of SQL statements ---")
        else:
            print("\nNo SQL statements were generated.", file=sys.stderr)

    else:
        print("\nCould not find employee images. Script aborted.", file=sys.stderr)
