# Cleanvid Docker Image
FROM python:3.11-slim

# Install FFmpeg and system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user matching NAS user
ARG UID=1026
ARG GID=100
RUN groupadd -g ${GID} cleanvid || true && \
    useradd -u ${UID} -g ${GID} -m cleanvid || true

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

# Create directories for volumes and set ownership
RUN mkdir -p /input /output /config /logs && \
    chown -R ${UID}:${GID} /app /input /output /config /logs

# Create entrypoint wrapper to set umask
RUN echo '#!/bin/sh' > /entrypoint.sh && \
    echo 'umask 002' >> /entrypoint.sh && \
    echo 'exec "$@"' >> /entrypoint.sh && \
    chmod +x /entrypoint.sh

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Expose web dashboard port
EXPOSE 8080

# Switch to non-root user
USER ${UID}:${GID}

# Use entrypoint wrapper
ENTRYPOINT ["/entrypoint.sh", "cleanvid"]
CMD ["--help"]
