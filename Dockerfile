# Multi-stage build for optimized image

# Stage 1: Build TypeScript
FROM node:20-alpine AS frontend-builder

WORKDIR /app

# Copy package files
COPY package.json package-lock.json* ./

# Install dependencies
RUN npm install

# Copy TypeScript source
COPY src ./src
COPY tsconfig.json ./
COPY webpack.config.js ./

# Build TypeScript
RUN npm run build

# Stage 2: Python runtime
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    ffmpeg \
    wget \
    gnupg \
    xvfb \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libx11-xcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

# Install Google Chrome
RUN mkdir -p /etc/apt/keyrings \
    && wget -q -O /etc/apt/keyrings/google-chrome.gpg https://dl.google.com/linux/linux_signing_key.pub \
    && echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# Install Playwright (Python) and Chromium browser
RUN pip install playwright && playwright install --with-deps chromium

# Copy Python requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy Flask application
COPY app.py .
COPY squidly ./squidly
COPY templates ./templates
COPY static ./static

# Copy built assets from frontend stage
COPY --from=frontend-builder /app/static/dist ./static/dist

# Create logs directory
RUN mkdir -p /logs

# Disable Python output buffering
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 5000

# Run with gunicorn for production
# Using --preload to load app before forking workers (runs validation once)
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--preload", "--timeout", "120", "--access-logfile", "/logs/gunicorn_access.log", "--error-logfile", "/logs/gunicorn_error.log", "app:app"]
