"""Utility script to generate sample verification images for testing."""

import os
import requests
import time
import base64
from pathlib import Path


def download_ai_face():
    """Download a face from thispersondoesnotexist.com."""
    url = "https://thispersondoesnotexist.com/"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.content
        else:
            print(
                f"Failed to download image: Status code {response.status_code}")
            return None
    except Exception as e:
        print(f"Error downloading image: {e}")
        return None


def save_sample_images(num_images=5, output_dir="static/sample_images"):
    """Download and save multiple AI-generated faces."""
    # Create output directory if it doesn't exist
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    print(f"Downloading {num_images} sample images...")

    # Store base64 encoded images for easy access
    image_data = []

    for i in range(num_images):
        print(f"Downloading image {i+1}/{num_images}...")
        image_bytes = download_ai_face()

        if image_bytes:
            # Save the file
            file_path = output_path / f"sample_face_{i+1}.jpg"
            with open(file_path, "wb") as f:
                f.write(image_bytes)
            print(f"Saved {file_path}")

            # Store base64 encoded version
            base64_image = base64.b64encode(image_bytes).decode('utf-8')
            image_data.append({
                'file_path': str(file_path),
                'base64': base64_image
            })

            # Wait a bit between requests to be nice to the server
            time.sleep(1)
        else:
            print(f"Failed to download image {i+1}")

    # Save base64 data to a text file for easy access
    with open(output_path / "sample_images.txt", "w") as f:
        for data in image_data:
            f.write(f"File: {data['file_path']}\n")
            f.write(f"Base64: {data['base64']}\n\n")

    print(f"\nDownloaded {len(image_data)} images successfully")
    print(f"Images saved in: {output_path.absolute()}")
    return image_data


if __name__ == "__main__":
    # Download 5 sample images
    save_sample_images()
