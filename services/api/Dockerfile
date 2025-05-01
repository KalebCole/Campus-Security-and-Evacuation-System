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

# Ensure the certs directory exists in the container
RUN mkdir -p /app/certs

# Copy the certificate into the container (assuming certs is still in services/api/)
COPY certs/emqxsl-ca.crt /app/certs/

# Copy the application source code into the container's src directory
COPY src/ /app/src

# Copy the templates and static folders into the container
COPY templates/ /app/templates/
COPY static/ /app/static/

# Expose the port that the application listens on
EXPOSE 8080

# Run the application from its new location in src/
CMD ["python", "-m", "src.app"]
