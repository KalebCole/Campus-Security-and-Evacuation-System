FROM python:3.10-slim

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


# Install Python dependencies - simplified for reliability
RUN pip install numpy==1.23.5 && \
    pip install tensorflow==2.11.0 && \
    pip install -r requirements.txt

# for future, --no-cache-dir
# RUN pip install --no-deps --no-cache-dir -r requirements.txt

# Copy the application code
COPY ./service /app/service
COPY ./core /app/core
COPY ./config /app/config

# Create models directory and copy model
RUN mkdir -p /app/core/models
COPY ./core/models/ghostfacenets.h5 /app/core/models/

# Set environment variables
ENV PYTHONPATH=/app
ENV MODEL_PATH=/app/core/models/ghostfacenets.h5

# Expose the port for the face recognition service
EXPOSE 5001

# Run the face recognition service using gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5001", "service.app:create_app()"]