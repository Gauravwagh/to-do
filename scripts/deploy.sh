#!/bin/bash
set -e

echo "=== Evernote Clone Deployment Script ==="
echo "Starting deployment at $(date)"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Project directory
PROJECT_DIR="/var/www/evernote_clone"
BRANCH="${1:-feature/deployment-and-mobile-responsive}"

echo -e "${YELLOW}Deploying branch: $BRANCH${NC}"

# Change to project directory
cd $PROJECT_DIR

# Backup database before deployment
echo -e "${YELLOW}Creating database backup...${NC}"
if [ -f db.sqlite3 ]; then
    cp db.sqlite3 /root/db.sqlite3.backup.$(date +%Y%m%d_%H%M%S)
    echo -e "${GREEN}Database backed up${NC}"
fi

# Stash any local changes
echo -e "${YELLOW}Stashing local changes...${NC}"
git stash

# Fetch latest changes
echo -e "${YELLOW}Fetching latest changes from GitHub...${NC}"
git fetch origin $BRANCH

# Pull the latest code
echo -e "${YELLOW}Pulling latest code...${NC}"
git pull origin $BRANCH

# Install/update Python dependencies
echo -e "${YELLOW}Installing Python dependencies...${NC}"
source venv/bin/activate
pip install -r requirements/production.txt --quiet

# Run database migrations
echo -e "${YELLOW}Running database migrations...${NC}"
python manage.py migrate --noinput

# Create/update superuser
echo -e "${YELLOW}Creating/updating superuser...${NC}"
python manage.py create_superuser

# Collect static files
echo -e "${YELLOW}Collecting static files...${NC}"
python manage.py collectstatic --noinput --clear

# Fix permissions
echo -e "${YELLOW}Fixing file permissions...${NC}"
chown -R www-data:www-data $PROJECT_DIR
chmod -R 755 $PROJECT_DIR/staticfiles
chmod 644 $PROJECT_DIR/.env

# Clear Python cache
echo -e "${YELLOW}Clearing Python cache...${NC}"
find . -type d -name "__pycache__" -exec rm -r {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true

# Restart Gunicorn service
echo -e "${YELLOW}Restarting Gunicorn service...${NC}"
systemctl restart evernote_clone.service

# Wait for service to start
sleep 3

# Check service status
if systemctl is-active --quiet evernote_clone.service; then
    echo -e "${GREEN}✓ Deployment completed successfully!${NC}"
    echo -e "${GREEN}✓ Service is running${NC}"
    systemctl status evernote_clone.service --no-pager -l | head -20
else
    echo -e "${RED}✗ Deployment failed - service is not running${NC}"
    systemctl status evernote_clone.service --no-pager -l | head -20
    exit 1
fi

echo "Deployment finished at $(date)"
echo "=== Deployment Complete ==="
