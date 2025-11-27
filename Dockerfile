# Oracle Cloud Instance Manager - Admin Panel
# Multi-stage build for optimized image size

FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Production stage
FROM python:3.11-slim

WORKDIR /app

# Copy Python packages from builder
COPY --from=builder /root/.local /root/.local

# Ensure scripts in .local are usable
ENV PATH=/root/.local/bin:$PATH

# Copy application files
COPY app.py .
COPY templates/ templates/

# Create data directories
RUN mkdir -p /app/logs /app/data

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV FLASK_ENV=production
ENV WEB_HOST=0.0.0.0
ENV WEB_PORT=5000

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/login')" || exit 1

# Run the application
CMD ["python", "app.py"]
