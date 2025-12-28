# Cleanvid Docker Image
FROM python:3.11-slim

# Install FFmpeg and system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy application files
COPY requirements.txt .
COPY setup.py .
COPY README.md .
COPY src/ ./src/
COPY config/ ./config/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir -e .

# Create directories for volumes
RUN mkdir -p /input /output /config /logs

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Expose web dashboard port
EXPOSE 8080

# Default command
ENTRYPOINT ["cleanvid"]
CMD ["--help"]
