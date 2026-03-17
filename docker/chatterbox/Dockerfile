FROM chatterbox-base:gpu-cu124

WORKDIR /app

COPY server.py .

RUN mkdir -p /app/voices /app/cache

EXPOSE 8400

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8400"]
