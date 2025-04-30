import os
import uuid
import sys
import re
from datetime import datetime, timedelta
import random
from urllib.parse import urlparse, urlunparse

# --- Load .env variables first ---
from dotenv import load_dotenv
load_dotenv()  # Searches for .env file and loads variables into environment

# --- Add project root to path to allow imports from config, models, etc. ---
# Adjust the number of '..' based on the script's location relative to the project root
project_root = os.path.abspath(os.path.join(
    os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from supabase import create_client, Client
    import sqlalchemy
    from sqlalchemy import create_engine, text, select
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.exc import NoResultFound, MultipleResultsFound

    # Assuming config.py is in the 'api' directory, one level up from 'utils'
    from api.config import Config
    # Assuming models are in api/models
    from api.models.employee import Employee  # Need this for DB query
    # ADDED: Import AccessLog for SQLAlchemy relationship resolution
    from api.models.access_log import AccessLog
    # ADDED: Import VerificationImage too!
    from api.models.verification_image import VerificationImage
except ImportError as e:
    print(f"Error importing necessary modules: {e}")
    print("Please ensure supabase-py, SQLAlchemy, psycopg2-binary are installed and config/models are accessible.")
    sys.exit(1)


# --- Configuration ---
# Construct the absolute path to the image folder relative to this script's location
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
API_DIR = os.path.abspath(os.path.join(
    SCRIPT_DIR, '..'))  # Go up one level to api/
MOCK_IMAGE_FOLDER = os.path.join(
    API_DIR, "static", "images", "verification_images")

# MOCK_IMAGE_FOLDER = "../api/static/images/verification_images/" # Previous incorrect path
SUPABASE_BUCKET = Config.SUPABASE_BUCKET_NAME
# Make output path relative too
OUTPUT_SQL_FILE = os.path.join(API_DIR, "..", "database", "sample_data.sql")
DATABASE_URL = Config.DATABASE_URL  # Get DB URL from config
MOCK_DEVICE_ID = "mock-esp32-001"  # Default device ID for mock logs

# --- Initialize Supabase Client ---
try:
    supabase: Client = create_client(
        Config.SUPABASE_URL, Config.SUPABASE_SERVICE_KEY)
    print("Supabase client initialized.")
except Exception as e:
    print(f"Error initializing Supabase client: {e}")
    sys.exit(1)

# --- Initialize Database Connection ---
try:
    # Parse the original DATABASE_URL
    original_db_url = Config.DATABASE_URL
    parsed_url = urlparse(original_db_url)

    # Replace hostname 'db' with 'localhost' for script execution
    # Keep original user, password, port (if specified), database name
    # Default to port 5432 if not specified in the original URL
    host_port = parsed_url.netloc.split('@')[-1]  # Gets host:port or host
    original_host = host_port.split(':')[0]
    original_port = parsed_url.port if parsed_url.port else 5432  # Default port

    if original_host == 'db':
        host_db_url = urlunparse((
            parsed_url.scheme,
            # Construct netloc with localhost
            f"{parsed_url.username}:{parsed_url.password}@localhost:{original_port}",
            parsed_url.path,
            parsed_url.params,
            parsed_url.query,
            parsed_url.fragment
        ))
        # Hide password in log
        print(
            f"Adjusted DB URL for host script: {host_db_url.replace(parsed_url.password, '****')}")
    else:
        host_db_url = original_db_url  # Use original if hostname isn't 'db'
        print(
            f"Using original DB URL: {host_db_url.replace(parsed_url.password, '****')}")

    # Use the adjusted URL to create the engine
    engine = create_engine(host_db_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    print("Database engine created.")
except Exception as e:
    print(f"Error creating database engine: {e}")
    sys.exit(1)

# --- Helper Functions ---


def parse_filename_for_scenario(filename):
    """
    Parses the filename based on the convention using regex:
    <EmployeeNameOrUNKNOWN>_<VerificationMethod>_<InitialStatus>_<AccessGrantedOrNA>_<ConfidenceIfApplicable>.[ext]
    Returns a dictionary with parsed values or None if parsing fails.
    """
    # Regex to capture the 5 parts, ignoring the extension(s) at the end
    # Allows methods/status to contain multiple words if needed in future (though current convention is single)
    pattern = r"^([A-Za-z]+(?:[A-Z][a-z]*)*|UNKNOWN)_([A-Za-z_]+)_([a-z]+)_([a-zA-Z]+)_([0-9.]+|NA)(?=\.).*$"
    match = re.match(pattern, filename)

    if not match:
        print(
            f"  Warning: Filename '{filename}' does not match expected regex pattern. Skipping.")
        return None

    groups = match.groups()
    employee_name_raw = groups[0]
    verification_method = groups[1]
    initial_status = groups[2]
    access_granted_or_na = groups[3]
    confidence_str = groups[4]

    # Determine original extension (less critical now, but good practice)
    # Find the position of the confidence value string in the original filename
    base_name_part_before_ext = "_".join(groups)
    ext_start_index = filename.find(confidence_str) + len(confidence_str)
    original_extension = filename[ext_start_index:].split(
        '.')[1]  # Get first part after dot
    original_extension = f".{original_extension}" if original_extension else ".unknown"

    # Convert CamelCase name back to space-separated
    if employee_name_raw != "UNKNOWN":
        employee_name = re.sub(r'(?<!^)(?=[A-Z])', ' ', employee_name_raw)
    else:
        employee_name = "UNKNOWN"

    # Parse confidence
    confidence = None
    if confidence_str.lower() != 'na':
        try:
            confidence = float(confidence_str)
        except ValueError:
            print(
                f"  Warning: Invalid confidence value '{confidence_str}' in '{filename}'. Treating as NA.")
            confidence_str = 'NA'  # Ensure confidence is None if parse fails

    return {
        "employee_name_raw": employee_name_raw,
        "employee_name": employee_name,
        "verification_method": verification_method,
        "initial_status": initial_status,
        "access_granted_or_na": access_granted_or_na,
        "confidence_str": confidence_str,
        "confidence": confidence,
        "extension": original_extension  # Use the determined extension
    }


def get_employee_id_from_name(db_session, name):
    """Queries the database for the employee ID based on their name."""
    if name == "UNKNOWN" or not name:
        return None
    try:
        stmt = select(Employee.id).where(Employee.name == name)
        result = db_session.execute(
            stmt).scalar_one_or_none()  # Use scalar_one_or_none
        if result:
            print(f"  Found employee_id for '{name}': {result}")
            return result
        else:
            print(f"  Warning: Employee '{name}' not found in the database.")
            return None
    except MultipleResultsFound:
        print(
            f"  Error: Multiple employees found with name '{name}'. Cannot determine ID.")
        return None
    except Exception as e:
        print(f"  Error querying employee ID for '{name}': {e}")
        return None


def generate_random_past_timestamp():
    """Generates a timestamp within the last 24 hours."""
    return datetime.now() - timedelta(minutes=random.randint(1, 60 * 24))


# --- Main Script Logic ---
generated_sql = [
    f"\n-- Mock Verification Images and Logs ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')}) --"]
markdown_logs = ["## Access Logs Scenarios (Generated from Mock Images)",
                 "| Scenario Description                | Employee Name     | Verification Method        | Initial Status | Access Granted | Confidence | `session_id` (Example)                 |"]
markdown_logs.append(
    "| :---------------------------------- | :---------------- | :------------------------- | :------------- | :------------- | :--------- | :------------------------------------- |")
markdown_images = ["## Verification Images (Generated from Mock Images)",
                   "| `session_id` (Example)                 | Captured Image URL (Supabase)                                                    | Associated Scenario                |"]
markdown_images.append(
    "| :------------------------------------- | :------------------------------------------------------------------------------- | :--------------------------------- |")

processed_files = 0
skipped_files = 0

# Get a database session
db = SessionLocal()

try:
    print(f"Scanning folder: {MOCK_IMAGE_FOLDER}")
    if not os.path.isdir(MOCK_IMAGE_FOLDER):
        print(f"Error: Input folder '{MOCK_IMAGE_FOLDER}' not found.")
        sys.exit(1)

    image_files = [f for f in os.listdir(
        MOCK_IMAGE_FOLDER) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    print(f"Found {len(image_files)} potential image files.")

    for filename in image_files:
        local_path = os.path.join(MOCK_IMAGE_FOLDER, filename)
        print(f"\nProcessing {filename}...")

        # --- Parse Filename ---
        scenario = parse_filename_for_scenario(filename)
        if not scenario:
            skipped_files += 1
            continue

        # --- Get Employee ID ---
        employee_id = None
        employee_id_sql = "NULL"
        if scenario["employee_name"] != "UNKNOWN":
            employee_id = get_employee_id_from_name(
                db, scenario["employee_name"])
            if employee_id:
                employee_id_sql = f"'{employee_id}'"  # Prepare for SQL string
            else:
                print(
                    f"  Skipping {filename} because employee '{scenario['employee_name']}' lookup failed.")
                skipped_files += 1
                continue  # Skip if employee needed but not found

        # --- Generate Session ID ---
        session_id = str(uuid.uuid4())
        supabase_path = f"verification_images/session_{session_id}{scenario['extension']}"

        # --- Determine Access Granted for SQL ---
        access_granted_sql = "FALSE"  # Default for pending or denied
        if scenario["access_granted_or_na"].lower() == 'granted':
            access_granted_sql = "TRUE"

        # --- Determine Confidence for SQL ---
        confidence_sql = "NULL"
        if scenario["confidence"] is not None:
            confidence_sql = str(scenario["confidence"])

        # --- Determine Timestamp ---
        timestamp = generate_random_past_timestamp()
        timestamp_sql = f"'{timestamp.isoformat()}'"

        # --- Determine 'processed' status for verification_images ---
        processed_sql = "FALSE" if scenario["initial_status"].lower(
        ) == 'pending' else "TRUE"

        try:
            # --- Upload to Supabase ---
            print(f"  Uploading {filename} to Supabase as {supabase_path}...")
            with open(local_path, 'rb') as f:
                # Determine content type (simple approach)
                content_type = 'image/png' if scenario['extension'].lower(
                ) == '.png' else 'image/jpeg'
                res = supabase.storage.from_(SUPABASE_BUCKET).upload(
                    path=supabase_path,
                    file=f,
                    file_options={"content-type": content_type,
                                  "cache-control": "3600", "upsert": "false"}
                )
                # Basic check: Supabase client might raise an error on failure
                print(
                    f"  Supabase upload initiated (check Supabase dashboard for status).")

            # --- Get Public URL ---
            public_url_res = supabase.storage.from_(
                SUPABASE_BUCKET).get_public_url(supabase_path)
            supabase_url = public_url_res  # Assuming URL string is directly returned

            if not supabase_url or "error" in supabase_url.lower():  # Basic check
                print(
                    f"  Error: Failed to get public URL for {supabase_path}. Result: {public_url_res}")
                skipped_files += 1
                continue

            print(f"  Supabase public URL: {supabase_url}")

            # --- Generate SQL Statements ---
            # Access Log
            sql_log = (
                f"INSERT INTO access_logs (employee_id, timestamp, access_granted, verification_method, session_id, verification_confidence, review_status) VALUES ("
                f"{employee_id_sql}, {timestamp_sql}, {access_granted_sql}, '{scenario['verification_method']}', '{session_id}', {confidence_sql}, '{scenario['initial_status']}'"
                f");"
            )
            # Verification Image
            sql_image = (
                f"INSERT INTO verification_images (session_id, storage_url, timestamp, processed, embedding, confidence, matched_employee_id, device_id) VALUES ("
                f"'{session_id}', '{supabase_url}', {timestamp_sql}, {processed_sql}, NULL, {confidence_sql}, {employee_id_sql}, '{MOCK_DEVICE_ID}'"
                f");"
            )

            generated_sql.append(sql_log)
            generated_sql.append(sql_image)

            # --- Prepare Markdown ---
            scenario_desc = filename.replace('_', ' ').replace(
                scenario['extension'], '')  # Simple description
            log_access_granted_md = scenario['access_granted_or_na'].capitalize(
            )
            md_log_row = f"| {scenario_desc:<35} | {scenario['employee_name']:<17} | {scenario['verification_method']:<26} | {scenario['initial_status']:<14} | {log_access_granted_md:<14} | {scenario['confidence_str']:<10} | `{session_id}` |"
            md_image_row = f"| `{session_id}` | `{supabase_url}` | {scenario_desc:<35} |"

            markdown_logs.append(md_log_row)
            markdown_images.append(md_image_row)

            processed_files += 1

        except Exception as e:
            print(f"  ERROR processing or uploading {filename}: {e}")
            skipped_files += 1
            # Optionally: try to delete partially uploaded file from Supabase if needed

finally:
    # Ensure the session is closed
    db.close()
    print("\nDatabase session closed.")

# --- Append SQL to file ---
if processed_files > 0:
    print(
        f"\nAppending {len(generated_sql) - 1} SQL statements to {OUTPUT_SQL_FILE}...")
    try:
        with open(OUTPUT_SQL_FILE, "a") as f:
            f.write("\n".join(generated_sql))
            f.write("\n")
        print(f"Successfully appended SQL to {OUTPUT_SQL_FILE}")
    except IOError as e:
        print(f"Error writing SQL to {OUTPUT_SQL_FILE}: {e}")

# --- Print Markdown ---
print("\n--- Generated Markdown for initial_data.md ---")
print("(Copy and paste the following tables into database/initial_data.md if desired)")
print("\n".join(markdown_logs))
print("\n" + "\n".join(markdown_images))
print("---------------------------------------------")

print(
    f"\nScript finished. Processed: {processed_files}, Skipped: {skipped_files}.")
