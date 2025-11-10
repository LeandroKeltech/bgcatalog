# Use Python 3.10 slim image
FROM python:3.10-slim

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

# Collect static files for production
RUN python manage.py collectstatic --noinput

# Create startup script
RUN echo '#!/bin/sh\n\
set -e\n\
echo "Resetting database schema..."\n\
python reset_db.py || echo "Reset failed, continuing..."\n\
echo "Running migrations..."\n\
python manage.py migrate --noinput\n\
echo "Creating admin user..."\n\
python manage.py shell < create_admin.py || echo "Admin creation failed or already exists"\n\
echo "Starting gunicorn..."\n\
exec gunicorn bgcatalog_project.wsgi:application --bind 0.0.0.0:8000 --workers 2 --access-logfile - --error-logfile - --log-level info' > /app/start.sh && \
chmod +x /app/start.sh

# Run startup script
CMD ["/app/start.sh"]
