# Build stage
FROM node:18-alpine AS builder

WORKDIR /app

# Copy package files
COPY package.json ./
COPY tsconfig.json ./
COPY tsconfig.node.json ./
COPY vite.config.ts ./

# Install dependencies
RUN npm ci

# Copy source files
COPY src/ ./src/
COPY index.html ./

# Build the application
RUN npm run build

# Production stage
FROM python:3.9-slim

WORKDIR /app

# Install Python dependencies
RUN pip install fastapi uvicorn python-multipart python-dotenv

# Copy built files from builder
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/package.json ./

# Copy server and config files
COPY server.py ./
COPY .env ./

# Copy parent directory files for agent
COPY ../agent_v2.py ./
COPY ../utils.py ./
COPY ../.env ./

# Create a non-root user
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# Expose ports
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/').raise_for_status()" || exit 1

# Start the server
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
