#!/bin/bash
set -e

echo "=== Django Startup Script ==="

# Wait for database to be ready
echo "Waiting for database..."
sleep 5

# Run database migrations
echo "Running database migrations..."
python manage.py migrate --noinput

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput --clear

# Create superuser
echo "Creating/updating superuser..."
python manage.py create_superuser

echo "=== Startup Complete ==="
