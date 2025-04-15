import os
import base64
import requests # Make sure to install this: pip install requests
import json
import sys
from datetime import datetime # Added for timestamp in file

# --- Configuration ---
# Adjust paths if your script is not run from the 'api' directory
SAMPLE_IMAGE_DIR = os.path.join("..", "static", "images", "employees") 
# Path to your sample data SQL file
SAMPLE_DATA_SQL_FILE = os.path.join("..", "..", "database", "sample_data.sql") 
# URL of your running face recognition service's embedding endpoint
FACE_REC_EMBED_URL = "http://localhost:5001/embed" 
# --- End Configuration ---

def get_employee_images(image_dir):
    """Finds employee image files and extracts RFID tags."""
    employee_files = {}
    abs_image_dir = os.path.abspath(image_dir) # Get absolute path for clarity
    if not os.path.isdir(abs_image_dir):
        print(f"Error: Image directory not found at '{abs_image_dir}'", file=sys.stderr)
        return None
        
    print(f"Scanning directory: {abs_image_dir}")
    for filename in os.listdir(abs_image_dir):
        if filename.lower().endswith((".jpg", ".jpeg", ".png")):
            # Assuming filename format is EMPXXX.jpg
            rfid_tag = os.path.splitext(filename)[0].upper() 
            if rfid_tag.startswith("EMP"):
                employee_files[rfid_tag] = os.path.join(abs_image_dir, filename) # Store absolute path
    print(f"Found {len(employee_files)} employee images.")
    return employee_files

def get_embedding(image_path):
    """Gets embedding for a single image file."""
    print(f"  Processing {os.path.basename(image_path)}...")
    try:
        with open(image_path, "rb") as f:
            image_bytes = f.read()
        
        image_base64 = base64.b64encode(image_bytes).decode("utf-8")
        
        payload = {"image": image_base64}
        
        response = requests.post(FACE_REC_EMBED_URL, json=payload, timeout=15) # Added timeout
        response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
        
        result = response.json()
        
        if "embedding" in result and isinstance(result["embedding"], list):
            print(f"    -> Embedding received ({len(result['embedding'])} dimensions).")
            return result["embedding"]
        else:
            print(f"    -> Error: Unexpected response format from embedding service: {result}", file=sys.stderr)
            return None
            
    except FileNotFoundError:
        print(f"    -> Error: File not found at {image_path}", file=sys.stderr)
        return None
    except requests.exceptions.RequestException as e:
        print(f"    -> Error: Failed to connect or communicate with face recognition service at {FACE_REC_EMBED_URL}: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"    -> Error: An unexpected error occurred processing {image_path}: {e}", file=sys.stderr)
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
            print(f"    -> Skipping SQL generation for {rfid_tag} due to previous errors.")
            
    return sql_statements

def append_sql_to_file(sql_file_path, statements):
    """Appends the generated SQL statements to the specified file."""
    abs_sql_file_path = os.path.abspath(sql_file_path)
    if not statements:
        print("\nNo SQL statements generated, skipping file update.", file=sys.stderr)
        return False
        
    if not os.path.isfile(abs_sql_file_path):
        print(f"\nError: Target SQL file not found at '{abs_sql_file_path}'", file=sys.stderr)
        return False

    print(f"\nAppending {len(statements)} SQL statements to {abs_sql_file_path}...")
    try:
        with open(abs_sql_file_path, 'a', encoding='utf-8') as f: # Open in append mode
            f.write("\n\n-- Auto-generated Embeddings ({}) --\n".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            for stmt in statements:
                f.write(stmt + "\n") # Write each statement on a new line
            f.write("-- End Auto-generated Embeddings --\n")
        print("Successfully appended statements to file.")
        return True
    except IOError as e:
        print(f"Error writing to SQL file '{abs_sql_file_path}': {e}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"An unexpected error occurred while writing to file: {e}", file=sys.stderr)
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