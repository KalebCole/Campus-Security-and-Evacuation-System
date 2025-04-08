FROM python:3.11-slim

# Set timezone
ENV TZ=America/New_York
RUN apt-get update && apt-get install -y \
    tzdata \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && ln -fs /usr/share/zoneinfo/$TZ /etc/localtime \
    && dpkg-reconfigure -f noninteractive tzdata \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY ./service/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the face recognition code
COPY . /app/face_recognition

# Create models directory
RUN mkdir -p /app/models

# Set environment variables
ENV PYTHONPATH=/app
ENV MODEL_PATH=/app/models/ghostfacenets.h5

# Expose the port for the face recognition service
EXPOSE 5001

# Run the face recognition service using gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5001", "face_recognition.service.app:create_app()"] 