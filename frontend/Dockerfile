FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm install

FROM node:20-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
# These must be declared as ARGs so Next.js can inline them at build time.
# NEXT_PUBLIC_* vars are baked into the JS bundle during `next build`; they
# are NOT read from the container environment at runtime.
ARG NEXT_PUBLIC_API_URL=http://localhost:8300
ARG NEXT_PUBLIC_WS_URL=ws://localhost:18789
ARG REWRITE_BACKEND_URL=http://host.docker.internal:8300
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_WS_URL=$NEXT_PUBLIC_WS_URL
ENV REWRITE_BACKEND_URL=$REWRITE_BACKEND_URL
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public
EXPOSE 3000
CMD ["node", "server.js"]
