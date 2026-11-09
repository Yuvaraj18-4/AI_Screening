# Stage 1: Build frontend
FROM node:20-alpine AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Python app + static files
FROM python:3.11-slim AS runtime
WORKDIR /app

# Create non-root user
RUN useradd -m -u 1000 appuser

# Install Python dependencies
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code, scripts, and sample data
COPY backend/ ./backend/
COPY scripts/ ./scripts/
COPY data/ ./data/

# Copy built frontend
COPY --from=frontend-build /app/frontend/dist ./frontend/dist

# Set ownership to non-root user
RUN chown -R appuser:appuser /app

# Non-root user
USER appuser

# Environment defaults
ENV PYTHONUNBUFFERED=1 \
    PORT=8000

EXPOSE ${PORT}

# Health check on /api/health
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import os, urllib.request; p = os.environ.get('PORT', '8000'); urllib.request.urlopen(f'http://127.0.0.1:{p}/api/health')" || exit 1

# Start uvicorn honoring $PORT
CMD ["sh", "-c", "cd backend && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
