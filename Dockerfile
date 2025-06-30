# Multi-stage Dockerfile for Video Comparison Tool - Google Cloud Run
FROM ubuntu:22.04 as base

# Avoid prompts from apt
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies including FFMPEG
RUN apt-get update && \
    apt-get install -y \
        python3 \
        python3-pip \
        python3-venv \
        ffmpeg \
        && rm -rf /var/lib/apt/lists/*

# Create app directory and non-root user
RUN useradd --create-home --shell /bin/bash app
WORKDIR /home/app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy application files
COPY app.py index.html ./
COPY --chown=app:app . .

# Create necessary directories
RUN mkdir -p uploads outputs && \
    chown -R app:app uploads outputs

# Switch to non-root user
USER app

# Expose port (Cloud Run will set PORT env var)
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python3 -c "import requests; requests.get('http://localhost:8080/health')" || exit 1

# Use Gunicorn for production
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "1", "--timeout", "300", "--worker-class", "sync", "app:app"]
