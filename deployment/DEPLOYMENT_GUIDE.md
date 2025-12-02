# Evernote Clone - Production Deployment Guide

This guide will help you deploy your Evernote Clone application to your Hetzner server at `46.224.109.101`.

## Prerequisites

- Server IP: `46.224.109.101`
- Server User: `root`
- Server OS: Ubuntu/Debian (recommended)

## Option 1: Quick Deployment (Recommended after SSH setup)

### Step 1: Setup SSH Key Authentication (One-time setup)

Open a terminal and run:

```bash
# Generate SSH key if you don't have one
ssh-keygen -t rsa -b 4096

# Copy SSH key to server (enter password when prompted)
ssh-copy-id -i ~/.ssh/id_rsa.pub root@46.224.109.101
```

### Step 2: Run Automated Deployment

```bash
cd deployment
./deploy.sh
```

## Option 2: Manual Step-by-Step Deployment

If you prefer to deploy manually or the automated script doesn't work, follow these steps:

### 1. Connect to Server

```bash
ssh root@46.224.109.101
```

### 2. Update System and Install Dependencies

```bash
# Update system
apt-get update && apt-get upgrade -y

# Install required packages
apt-get install -y \
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
```

### 3. Configure PostgreSQL

```bash
# Start PostgreSQL
systemctl start postgresql
systemctl enable postgresql

# Create database and user
sudo -u postgres psql << EOF
CREATE USER evernote_user WITH PASSWORD 'evernote_secure_password_123';
CREATE DATABASE evernote_clone OWNER evernote_user;
ALTER ROLE evernote_user SET client_encoding TO 'utf8';
ALTER ROLE evernote_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE evernote_user SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE evernote_clone TO evernote_user;
\q
EOF
```

### 4. Configure Redis

```bash
systemctl start redis-server
systemctl enable redis-server
```

### 5. Create Application Directory

```bash
mkdir -p /var/www/evernote_clone/logs
cd /var/www/evernote_clone
```

### 6. Upload Application Files

From your **local machine**, run:

```bash
# Go to project directory
cd /Users/gauravwagh/Documents/Projects/evernote_clone

# Upload files to server
scp -r accounts api calendar_app config core notes scripts static templates vault manage.py pyproject.toml requirements root@46.224.109.101:/var/www/evernote_clone/
```

### 7. Setup Python Environment (on server)

```bash
cd /var/www/evernote_clone

# Create virtual environment
python3.12 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements/production.txt
```

### 8. Create Environment File

```bash
cd /var/www/evernote_clone

# Generate SECRET_KEY
SECRET_KEY=$(python3.12 -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')

# Create .env file
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
```

### 9. Run Django Setup

```bash
cd /var/www/evernote_clone
source venv/bin/activate

# Load environment variables
export $(cat .env | xargs)

# Run migrations
python manage.py migrate

# Collect static files
python manage.py collectstatic --noinput

# Create superuser (interactive)
python manage.py createsuperuser
```

### 10. Setup Nginx

From your **local machine**:

```bash
scp deployment/nginx.conf root@46.224.109.101:/etc/nginx/sites-available/evernote_clone
```

On the **server**:

```bash
# Remove default site
rm -f /etc/nginx/sites-enabled/default

# Enable our site
ln -s /etc/nginx/sites-available/evernote_clone /etc/nginx/sites-enabled/

# Test nginx configuration
nginx -t

# Restart nginx
systemctl restart nginx
systemctl enable nginx
```

### 11. Setup Gunicorn Service

From your **local machine**:

```bash
scp deployment/gunicorn.service root@46.224.109.101:/etc/systemd/system/evernote_clone.service
```

On the **server**:

```bash
# Reload systemd
systemctl daemon-reload

# Start Gunicorn service
systemctl start evernote_clone
systemctl enable evernote_clone

# Check status
systemctl status evernote_clone
```

### 12. Configure Firewall

```bash
# Allow necessary ports
ufw allow 22/tcp   # SSH
ufw allow 80/tcp   # HTTP
ufw allow 443/tcp  # HTTPS

# Enable firewall
ufw --force enable

# Check status
ufw status
```

### 13. Set Permissions

```bash
chown -R www-data:www-data /var/www/evernote_clone
chmod -R 755 /var/www/evernote_clone
chmod -R 775 /var/www/evernote_clone/media
chmod -R 775 /var/www/evernote_clone/logs
```

## Post-Deployment

### Access Your Application

- **Main Site**: http://46.224.109.101
- **Admin Panel**: http://46.224.109.101/admin/
- **API Documentation**: http://46.224.109.101/api/v1/docs/

### Useful Commands

```bash
# View application logs
ssh root@46.224.109.101 'tail -f /var/www/evernote_clone/logs/gunicorn-error.log'

# Restart application
ssh root@46.224.109.101 'systemctl restart evernote_clone'

# Check service status
ssh root@46.224.109.101 'systemctl status evernote_clone'

# View nginx logs
ssh root@46.224.109.101 'tail -f /var/log/nginx/error.log'

# Connect to PostgreSQL
ssh root@46.224.109.101 'sudo -u postgres psql evernote_clone'
```

### Updating the Application

```bash
# From local machine, upload new code
cd /Users/gauravwagh/Documents/Projects/evernote_clone
scp -r accounts api config core notes vault root@46.224.109.101:/var/www/evernote_clone/

# On server, run migrations and restart
ssh root@46.224.109.101 << 'EOF'
cd /var/www/evernote_clone
source venv/bin/activate
export $(cat .env | xargs)
python manage.py migrate
python manage.py collectstatic --noinput
systemctl restart evernote_clone
EOF
```

## Troubleshooting

### Application won't start

Check logs:
```bash
journalctl -u evernote_clone -n 50
tail -f /var/www/evernote_clone/logs/gunicorn-error.log
```

### Database connection errors

Check PostgreSQL:
```bash
systemctl status postgresql
sudo -u postgres psql -l
```

### Static files not loading

```bash
cd /var/www/evernote_clone
source venv/bin/activate
python manage.py collectstatic --noinput
systemctl restart nginx
```

### Permission errors

```bash
chown -R www-data:www-data /var/www/evernote_clone
chmod -R 755 /var/www/evernote_clone
```

## Security Recommendations (Production)

1. **Use HTTPS**: Install Let's Encrypt SSL certificate
   ```bash
   apt-get install certbot python3-certbot-nginx
   certbot --nginx -d yourdomain.com
   ```

2. **Change Database Password**: Use a strong, unique password in production

3. **Update SECRET_KEY**: The deployment script generates a random one automatically

4. **Configure Email**: Set up proper SMTP settings in .env for email functionality

5. **Regular Backups**: Set up automated database backups
   ```bash
   pg_dump -U evernote_user evernote_clone > backup.sql
   ```

6. **Monitor Logs**: Set up log rotation and monitoring

7. **Update Dependencies**: Regularly update system packages and Python dependencies
