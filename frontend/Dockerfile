# ── Stage 1: Build Angular app ─────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

# Install dependencies first (layer cache)
COPY package*.json ./
RUN npm ci --legacy-peer-deps

# Copy source and build
COPY . .
RUN npm run build -- --configuration production

# ── Stage 2: Serve with nginx ───────────────────────────────
FROM nginx:alpine

# Copy built Angular files
COPY --from=builder /app/dist/frontend/browser /usr/share/nginx/html

# Copy custom nginx config (handles Angular routing)
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
