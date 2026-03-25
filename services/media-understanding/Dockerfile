FROM node:22-slim
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*
WORKDIR /app
RUN npm install @dymoo/media-understanding express
COPY server.js .
EXPOSE 18796
CMD ["node", "server.js"]
