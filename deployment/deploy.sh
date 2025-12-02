#!/bin/bash

# Evernote Clone Deployment Script
# This script deploys the Django application to a production server

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
SERVER_IP="46.224.109.101"
SERVER_USER="root"
APP_NAME="evernote_clone"
APP_DIR="/var/www/${APP_NAME}"
REPO_URL="https://github.com/yourusername/${APP_NAME}.git"  # Update this if using git

echo -e "${GREEN}=== Evernote Clone Deployment Script ===${NC}"
echo ""

# Function to print colored messages
print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

print_info() {
    echo -e "${YELLOW}[i]${NC} $1"
}

# Test SSH connection
print_info "Testing SSH connection to ${SERVER_USER}@${SERVER_IP}..."
if ssh -o ConnectTimeout=5 -o BatchMode=yes ${SERVER_USER}@${SERVER_IP} echo "SSH connection successful" 2>/dev/null; then
    print_status "SSH connection successful"
else
    print_error "Cannot connect to server. Please check your SSH configuration."
    exit 1
fi

# Deploy to server
print_info "Starting deployment to ${SERVER_IP}..."

ssh ${SERVER_USER}@${SERVER_IP} << 'ENDSSH'
set -e

echo "=== Step 1: Update system packages ==="
apt-get update
apt-get upgrade -y

echo "=== Step 2: Install required packages ==="
apt-get install -y \
    python3.12 \
    python3.12-venv \
    python3-pip \
    postgresql \
    postgresql-contrib \
    redis-server \
    nginx \
    git \
    curl

echo "=== Step 3: Configure PostgreSQL ==="
systemctl start postgresql
systemctl enable postgresql

# Create database and user
sudo -u postgres psql << EOF
-- Create user if not exists
DO \$\$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_user WHERE usename = 'evernote_user') THEN
        CREATE USER evernote_user WITH PASSWORD 'evernote_secure_password_123';
    END IF;
END
\$\$;

-- Create database if not exists
SELECT 'CREATE DATABASE evernote_clone OWNER evernote_user'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'evernote_clone')\gexec

-- Grant privileges
ALTER ROLE evernote_user SET client_encoding TO 'utf8';
ALTER ROLE evernote_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE evernote_user SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE evernote_clone TO evernote_user;
EOF

echo "=== Step 4: Configure Redis ==="
systemctl start redis-server
systemctl enable redis-server

echo "=== Step 5: Create application directory ==="
mkdir -p /var/www/evernote_clone
mkdir -p /var/www/evernote_clone/logs
cd /var/www/evernote_clone

echo "Deployment setup complete on server!"
ENDSSH

print_status "Server setup complete!"

# Copy application files to server
print_info "Copying application files to server..."
rsync -avz --exclude='.git' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.venv' \
    --exclude='db.sqlite3' \
    --exclude='media' \
    --exclude='staticfiles' \
    --exclude='.vscode' \
    --exclude='.claude' \
    --exclude='node_modules' \
    ../ ${SERVER_USER}@${SERVER_IP}:${APP_DIR}/

print_status "Files copied successfully!"

# Continue deployment on server
print_info "Continuing deployment on server..."

ssh ${SERVER_USER}@${SERVER_IP} << 'ENDSSH'
set -e

cd /var/www/evernote_clone

echo "=== Step 6: Create Python virtual environment ==="
python3.12 -m venv venv
source venv/bin/activate

echo "=== Step 7: Install Python dependencies ==="
pip install --upgrade pip
pip install -r requirements/production.txt

echo "=== Step 8: Generate SECRET_KEY ==="
SECRET_KEY=$(python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')

echo "=== Step 9: Create .env file ==="
cat > .env << EOF
# Django Settings
DJANGO_SETTINGS_MODULE=config.settings.production
SECRET_KEY=${SECRET_KEY}

# Allowed Hosts
ALLOWED_HOSTS=46.224.109.101

# Database Configuration
DATABASE_NAME=evernote_clone
DATABASE_USER=evernote_user
DATABASE_PASSWORD=evernote_secure_password_123
DATABASE_HOST=localhost
DATABASE_PORT=5432

# Redis Configuration
REDIS_URL=redis://127.0.0.1:6379/1

# Security Settings
SECURE_SSL_REDIRECT=False
EOF

echo "=== Step 10: Run Django migrations ==="
source venv/bin/activate
export $(cat .env | xargs)
python manage.py migrate --noinput

echo "=== Step 11: Collect static files ==="
python manage.py collectstatic --noinput

echo "=== Step 12: Create Django superuser (optional - skip if exists) ==="
# Uncomment and modify if you want to create a superuser automatically
# python manage.py createsuperuser --noinput --username admin --email admin@example.com || true

echo "=== Step 13: Set permissions ==="
chown -R www-data:www-data /var/www/evernote_clone
chmod -R 755 /var/www/evernote_clone
chmod -R 775 /var/www/evernote_clone/media
chmod -R 775 /var/www/evernote_clone/logs

ENDSSH

print_status "Application setup complete!"

# Setup Nginx and Gunicorn
print_info "Setting up Nginx and Gunicorn..."

# Copy nginx configuration
scp deployment/nginx.conf ${SERVER_USER}@${SERVER_IP}:/etc/nginx/sites-available/${APP_NAME}

# Copy gunicorn service file
scp deployment/gunicorn.service ${SERVER_USER}@${SERVER_IP}:/etc/systemd/system/${APP_NAME}.service

ssh ${SERVER_USER}@${SERVER_IP} << 'ENDSSH'
set -e

echo "=== Step 14: Configure Nginx ==="
# Remove default site if it exists
rm -f /etc/nginx/sites-enabled/default

# Enable our site
ln -sf /etc/nginx/sites-available/evernote_clone /etc/nginx/sites-enabled/

# Test nginx configuration
nginx -t

echo "=== Step 15: Start services ==="
# Reload systemd
systemctl daemon-reload

# Start and enable Gunicorn
systemctl start evernote_clone
systemctl enable evernote_clone

# Restart Nginx
systemctl restart nginx

echo "=== Step 16: Check service status ==="
systemctl status evernote_clone --no-pager || true
systemctl status nginx --no-pager || true

ENDSSH

print_status "Services configured and started!"

echo ""
echo -e "${GREEN}=== Deployment Complete! ===${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Visit http://${SERVER_IP} to see your application"
echo "2. Create a superuser: ssh ${SERVER_USER}@${SERVER_IP} 'cd ${APP_DIR} && source venv/bin/activate && python manage.py createsuperuser'"
echo "3. Access admin panel at: http://${SERVER_IP}/admin/"
echo ""
echo -e "${YELLOW}Useful commands:${NC}"
echo "- View logs: ssh ${SERVER_USER}@${SERVER_IP} 'tail -f ${APP_DIR}/logs/gunicorn-error.log'"
echo "- Restart app: ssh ${SERVER_USER}@${SERVER_IP} 'systemctl restart ${APP_NAME}'"
echo "- Check status: ssh ${SERVER_USER}@${SERVER_IP} 'systemctl status ${APP_NAME}'"
echo ""
