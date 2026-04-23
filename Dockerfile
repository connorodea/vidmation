FROM python:3.11-slim

# Install ffmpeg
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir -e .

# Copy application
COPY . .

# Create directories
RUN mkdir -p data output assets/fonts assets/music channel_profiles

# Expose web port
EXPOSE 8000

# Default: run web server
CMD ["uvicorn", "aividio.web.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
