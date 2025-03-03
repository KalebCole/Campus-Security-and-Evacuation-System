import base64
import json
import uuid
from supabase import create_client, Client
from app_config import Config

# Initialize Supabase client
supabase_url = Config.SUPABASE_URL
supabase_key = Config.SUPABASE_API_KEY
supabase: Client = create_client(supabase_url, supabase_key)

# Supabase tables and storage
user_table = supabase.table(Config.SUPABASE_USER_TABLE)
storage_bucket = supabase.storage.get_bucket(Config.SUPABASE_STORAGE_BUCKET)
user_entries_storage_path = Config.SUPABASE_USER_ENTRIES_STORAGE_PATH

print(storage_bucket)

# Load the base64 images from the JSON file
with open('./data/base64_images.json', 'r') as file:
    base64_images = json.load(file)


def seed_user_table():
    # Clear the table
    user_table.delete().neq('id', '-1').execute()

    # Seed the images from the storage
    seed_user_entries_storage()

    # Get the image URLs from the storage
    images = storage_bucket.list(user_entries_storage_path)
    users = []
    for image in images:
        if image["name"] != ".emptyFolderPlaceholder":
            image_url = storage_bucket.get_public_url(image["name"])
            users.append({"photo_url": image_url})

    # Insert the users into the table
    for user in users:
        response = user_table.insert(user).execute()
        print(response)


def seed_user_entries_storage():
    # clear the storage
    files = storage_bucket.list(user_entries_storage_path)
    remove_path = user_entries_storage_path + "/"

    # Remove all files in the storage
    for file in files:
        print(remove_path + file["name"])
        storage_bucket.remove(remove_path + file["name"])

    # Upload the base64images to the storage, decode them first and then upload
    for image in base64_images:
        base64_image_data = image["base64_image"].split(
            ',')[1] if ',' in image["base64_image"] else image["base64_image"]
        image_bytes = base64.b64decode(base64_image_data)

        # Generate a unique filename
        unique_filename = str(uuid.uuid4()) + '.jpg'
        path_on_supastorage = f'{user_entries_storage_path}/{unique_filename}'

        # Upload the image to the storage bucket
        response = storage_bucket.upload(
            path=path_on_supastorage, file=image_bytes, file_options={
                "content-type": "image/jpeg"}
        )
        print(response)


if __name__ == "__main__":
    seed_user_table()
