FROM python:3.11-slim

# Install build tools and PostgreSQL dev headers required for pgvector
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    build-essential \
    python3-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Copy the requirements.txt file into the container
COPY requirements.txt .

# Upgrade pip and related tools first
RUN pip install --upgrade pip setuptools wheel

# Install the dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy .env file into container
COPY ../.env .env

# Copy the rest of the application code into the container
COPY . .

# Expose the port that the application listens on
EXPOSE 8080

# Run the application
CMD ["python", "app.py"]
