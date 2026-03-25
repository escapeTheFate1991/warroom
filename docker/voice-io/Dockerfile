FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    alsa-utils \
    pulseaudio \
    ffmpeg \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy all voice-io files
COPY . .

# Create transcribe temp directory
RUN mkdir -p /tmp/warroom-transcribe

# Ensure scripts are executable
RUN chmod +x scripts/*.py scripts/*.sh

# Expose voice server port
EXPOSE 18793

# Default command runs the voice server
CMD ["python3", "scripts/transcribe_server.py"]