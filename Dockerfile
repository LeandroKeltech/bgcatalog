# Keep the container runtime on the supported Python line used by Vercel.
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    gcc \
    python3-dev \
    libpq-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Copy a robust startup script and make it executable (start.sh handles DB waits, migrations and gunicorn)
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

RUN useradd --create-home app && chown -R app:app /app
USER app

# Run startup script
CMD ["/app/start.sh"]
