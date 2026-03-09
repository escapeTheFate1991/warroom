FROM python:3.11-slim AS base

# System deps for audio processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    libsndfile1 ffmpeg git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install PyTorch with CUDA support first (large layer, cache it)
RUN pip install --no-cache-dir torch torchaudio --index-url https://download.pytorch.org/whl/cu121

# Install chatterbox and server deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Voice reference clips directory
RUN mkdir -p /app/voices

EXPOSE 8400

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8400"]
