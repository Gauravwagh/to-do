#!/bin/bash

# Evernote Clone Deployment Script (Password Authentication)
# This script will prompt for password when needed

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

SERVER_IP="46.224.109.101"
SERVER_USER="root"
APP_DIR="/var/www/evernote_clone"

echo -e "${GREEN}=== Evernote Clone Deployment ===${NC}"
echo ""
echo "This script will deploy your application to ${SERVER_IP}"
echo "You will be prompted for the server password multiple times."
echo ""

echo -e "\n${YELLOW}Step 1: Installing system packages...${NC}"
ssh ${SERVER_USER}@${SERVER_IP} << 'ENDSSH'
set -e
export DEBIAN_FRONTEND=noninteractive

echo "Updating package lists..."
apt-get update -qq

echo "Installing required packages..."
apt-get install -y -qq \
    python3.12 \
    python3.12-venv \
    python3-pip \
    postgresql \
    postgresql-contrib \
    redis-server \
    nginx \
    git \
    curl \
    ufw

echo "Packages installed successfully!"
ENDSSH

echo -e "${GREEN}✓ System packages installed${NC}"

echo -e "\n${YELLOW}Step 2: Configuring PostgreSQL...${NC}"
ssh ${SERVER_USER}@${SERVER_IP} << 'ENDSSH'
set -e

systemctl start postgresql
systemctl enable postgresql

sudo -u postgres psql << EOF
-- Create user
DO \$\$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_user WHERE usename = 'evernote_user') THEN
        CREATE USER evernote_user WITH PASSWORD 'evernote_secure_password_123';
    END IF;
END
\$\$;

-- Create database
SELECT 'CREATE DATABASE evernote_clone OWNER evernote_user'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'evernote_clone')\gexec

-- Grant privileges
ALTER ROLE evernote_user SET client_encoding TO 'utf8';
ALTER ROLE evernote_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE evernote_user SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE evernote_clone TO evernote_user;
EOF

echo "PostgreSQL configured successfully!"
ENDSSH

echo -e "${GREEN}✓ PostgreSQL configured${NC}"

echo -e "\n${YELLOW}Step 3: Configuring Redis...${NC}"
ssh ${SERVER_USER}@${SERVER_IP} << 'ENDSSH'
systemctl start redis-server
systemctl enable redis-server
echo "Redis configured successfully!"
ENDSSH

echo -e "${GREEN}✓ Redis configured${NC}"

echo -e "\n${YELLOW}Step 4: Creating application directory...${NC}"
ssh ${SERVER_USER}@${SERVER_IP} << ENDSSH
mkdir -p ${APP_DIR}/logs
echo "Application directory created!"
ENDSSH

echo -e "${GREEN}✓ Directory created${NC}"

echo -e "\n${YELLOW}Step 5: Copying application files (this may take a moment)...${NC}"
scp -r \
    ../accounts \
    ../api \
    ../calendar_app \
    ../config \
    ../core \
    ../notes \
    ../scripts \
    ../static \
    ../templates \
    ../vault \
    ../manage.py \
    ../pyproject.toml \
    ${SERVER_USER}@${SERVER_IP}:${APP_DIR}/

echo -e "${GREEN}✓ Main files copied${NC}"

echo -e "\n${YELLOW}Step 6: Copying requirements...${NC}"
scp -r ../requirements ${SERVER_USER}@${SERVER_IP}:${APP_DIR}/

echo -e "${GREEN}✓ Requirements copied${NC}"

echo -e "\n${YELLOW}Step 7: Setting up Python environment and installing dependencies...${NC}"
ssh ${SERVER_USER}@${SERVER_IP} << ENDSSH
cd ${APP_DIR}

echo "Creating virtual environment..."
python3.12 -m venv venv

echo "Installing dependencies..."
source venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements/production.txt -q

echo "Dependencies installed!"
ENDSSH

echo -e "${GREEN}✓ Python environment ready${NC}"

echo -e "\n${YELLOW}Step 8: Configuring environment...${NC}"
ssh ${SERVER_USER}@${SERVER_IP} << 'ENDSSH'
cd /var/www/evernote_clone

SECRET_KEY=$(python3.12 -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')

cat > .env << EOF
DJANGO_SETTINGS_MODULE=config.settings.production
SECRET_KEY=${SECRET_KEY}
ALLOWED_HOSTS=46.224.109.101
DATABASE_NAME=evernote_clone
DATABASE_USER=evernote_user
DATABASE_PASSWORD=evernote_secure_password_123
DATABASE_HOST=localhost
DATABASE_PORT=5432
REDIS_URL=redis://127.0.0.1:6379/1
SECURE_SSL_REDIRECT=False
EOF

echo "Environment configured!"
ENDSSH

echo -e "${GREEN}✓ Environment configured${NC}"

echo -e "\n${YELLOW}Step 9: Running Django migrations...${NC}"
ssh ${SERVER_USER}@${SERVER_IP} << 'ENDSSH'
cd /var/www/evernote_clone
source venv/bin/activate
export $(cat .env | xargs)
python manage.py migrate --noinput
echo "Migrations complete!"
ENDSSH

echo -e "${GREEN}✓ Migrations complete${NC}"

echo -e "\n${YELLOW}Step 10: Collecting static files...${NC}"
ssh ${SERVER_USER}@${SERVER_IP} << 'ENDSSH'
cd /var/www/evernote_clone
source venv/bin/activate
export $(cat .env | xargs)
python manage.py collectstatic --noinput
echo "Static files collected!"
ENDSSH

echo -e "${GREEN}✓ Static files collected${NC}"

echo -e "\n${YELLOW}Step 11: Copying Nginx configuration...${NC}"
scp nginx.conf ${SERVER_USER}@${SERVER_IP}:/etc/nginx/sites-available/evernote_clone

echo -e "${GREEN}✓ Nginx config copied${NC}"

echo -e "\n${YELLOW}Step 12: Copying Gunicorn service...${NC}"
scp gunicorn.service ${SERVER_USER}@${SERVER_IP}:/etc/systemd/system/evernote_clone.service

echo -e "${GREEN}✓ Gunicorn service copied${NC}"

echo -e "\n${YELLOW}Step 13: Setting permissions...${NC}"
ssh ${SERVER_USER}@${SERVER_IP} << 'ENDSSH'
chown -R www-data:www-data /var/www/evernote_clone
chmod -R 755 /var/www/evernote_clone
chmod -R 775 /var/www/evernote_clone/media
chmod -R 775 /var/www/evernote_clone/logs
echo "Permissions set!"
ENDSSH

echo -e "${GREEN}✓ Permissions set${NC}"

echo -e "\n${YELLOW}Step 14: Configuring and starting services...${NC}"
ssh ${SERVER_USER}@${SERVER_IP} << 'ENDSSH'
# Remove default nginx site
rm -f /etc/nginx/sites-enabled/default

# Enable our site
ln -sf /etc/nginx/sites-available/evernote_clone /etc/nginx/sites-enabled/

# Test nginx config
nginx -t

# Reload systemd
systemctl daemon-reload

# Start services
systemctl start evernote_clone
systemctl enable evernote_clone
systemctl restart nginx

echo "Services started!"
ENDSSH

echo -e "${GREEN}✓ Services started${NC}"

echo -e "\n${YELLOW}Step 15: Configuring firewall...${NC}"
ssh ${SERVER_USER}@${SERVER_IP} << 'ENDSSH'
# Allow SSH, HTTP, and HTTPS
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp

# Enable firewall (if not already enabled)
ufw --force enable

echo "Firewall configured!"
ENDSSH

echo -e "${GREEN}✓ Firewall configured${NC}"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   Deployment Complete! 🎉${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${YELLOW}Your application is now running at:${NC}"
echo -e "  ${GREEN}http://46.224.109.101${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "  1. Create a superuser account:"
echo "     ssh root@46.224.109.101 'cd /var/www/evernote_clone && source venv/bin/activate && python manage.py createsuperuser'"
echo ""
echo "  2. Access admin panel:"
echo "     http://46.224.109.101/admin/"
echo ""
echo -e "${YELLOW}Useful commands:${NC}"
echo "  - View application logs:"
echo "    ssh root@46.224.109.101 'tail -f /var/www/evernote_clone/logs/gunicorn-error.log'"
echo ""
echo "  - Restart application:"
echo "    ssh root@46.224.109.101 'systemctl restart evernote_clone'"
echo ""
echo "  - Check service status:"
echo "    ssh root@46.224.109.101 'systemctl status evernote_clone'"
echo ""
