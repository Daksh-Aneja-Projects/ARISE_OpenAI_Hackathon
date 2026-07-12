# ============================================================
# ARISE Frontend — Production Multi-Stage Dockerfile
# Stage 1: Build Vite/React app
# Stage 2: Serve with Nginx (Alpine)
# ============================================================

# ─── Stage 1: Node Builder ────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

# Install deps first (cache layer)
COPY package.json package-lock.json ./
RUN npm ci --ignore-scripts

# Copy source and build
COPY . .

# Production build
ARG VITE_API_BASE=http://localhost:8000
ENV VITE_API_BASE=$VITE_API_BASE

RUN npm run build


# ─── Stage 2: Nginx Production Server ─────────────────────────
FROM nginx:1.27-alpine AS production

LABEL maintainer="ARISE Team"
LABEL org.opencontainers.image.title="ARISE Frontend"
LABEL org.opencontainers.image.description="ARISE — React/Vite SPA served via Nginx"

# Copy built assets
COPY --from=builder /app/dist /usr/share/nginx/html

# Nginx config — SPA routing + security headers + gzip
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Non-root nginx
RUN chown -R nginx:nginx /usr/share/nginx/html && \
    chmod -R 755 /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -qO- http://localhost/health || exit 1

CMD ["nginx", "-g", "daemon off;"]
