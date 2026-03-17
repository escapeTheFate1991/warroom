FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies (lightweight for Phase 1)
RUN pip install --no-cache-dir \
    fastapi \
    uvicorn \
    python-multipart \
    pydantic \
    httpx

# Copy the FastAPI server
COPY server.py .

# Create directories for voices and cache
RUN mkdir -p /app/voices /app/cache

EXPOSE 8400

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8400"]