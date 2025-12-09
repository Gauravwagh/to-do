# Deployment Guide

This project uses Git-based deployment with automated scripts for easy and reliable deployments to production.

## Quick Deployment

To deploy the latest code to production, simply run:

```bash
./deploy_to_production.sh
```

This will automatically:
1. Connect to the production server
2. Pull the latest code from GitHub
3. Install/update dependencies
4. Run database migrations
5. Create/update superuser
6. Collect static files
7. Restart the application service

## Deployment Setup

### Production Server Setup

The production server is configured with:
- **Server**: root@46.224.109.101
- **Project Directory**: `/var/www/evernote_clone`
- **Branch**: `feature/deployment-and-mobile-responsive`
- **Service**: `evernote_clone.service` (systemd)

### Git Repository

The production server is now a proper Git repository that tracks the remote repository:
```
https://github.com/Gauravwagh/to-do.git
```

### Environment Variables

Environment variables are stored in `/var/www/evernote_clone/.env` and include:
- Database credentials
- Django settings
- Secret keys
- Sentry configuration
- Superuser credentials (for auto-creation)

**Important**: The `.env` file is NOT tracked by Git and persists across deployments.

## Deployment Scripts

### Local Script: `deploy_to_production.sh`

Run this from your local machine to trigger a deployment:

```bash
./deploy_to_production.sh [branch-name]
```

- Default branch: `feature/deployment-and-mobile-responsive`
- Requires SSH access to production server

### Server Script: `scripts/deploy.sh`

This runs on the production server and performs the actual deployment:

```bash
# On production server
cd /var/www/evernote_clone
./scripts/deploy.sh [branch-name]
```

The script performs:
1. **Database Backup**: Automatically backs up the database before deployment
2. **Git Pull**: Fetches and pulls latest code from GitHub
3. **Dependencies**: Attempts to install/update Python packages
4. **Migrations**: Runs database migrations
5. **Superuser**: Creates or updates the superuser account
6. **Static Files**: Collects and organizes static files
7. **Permissions**: Fixes file ownership and permissions
8. **Cache Cleanup**: Removes Python cache files
9. **Service Restart**: Restarts Gunicorn service
10. **Verification**: Checks that the service is running correctly

## Systemd Service

The application runs as a systemd service that automatically:
- Runs migrations on start
- Creates/updates superuser
- Collects static files
- Starts Gunicorn with 3 workers

Service commands:
```bash
# Restart the service
sudo systemctl restart evernote_clone.service

# Check status
sudo systemctl status evernote_clone.service

# View logs
sudo journalctl -u evernote_clone.service -f
```

## Manual Deployment Steps

If you need to deploy manually:

```bash
# 1. SSH to production server
ssh root@46.224.109.101

# 2. Navigate to project directory
cd /var/www/evernote_clone

# 3. Pull latest code
git pull origin feature/deployment-and-mobile-responsive

# 4. Activate virtual environment
source venv/bin/activate

# 5. Install dependencies (if needed)
pip install -r requirements/production.txt

# 6. Run migrations
python manage.py migrate

# 7. Collect static files
python manage.py collectstatic --noinput

# 8. Restart service
sudo systemctl restart evernote_clone.service
```

## Rollback

To rollback to a previous version:

```bash
# On production server
cd /var/www/evernote_clone
git log --oneline  # Find the commit to rollback to
git reset --hard <commit-hash>
./scripts/deploy.sh
```

## Database Backups

Automatic backups are created before each deployment:
```
/root/db.sqlite3.backup.YYYYMMDD_HHMMSS
```

To restore a backup:
```bash
cd /var/www/evernote_clone
sudo systemctl stop evernote_clone.service
cp /root/db.sqlite3.backup.YYYYMMDD_HHMMSS db.sqlite3
sudo systemctl start evernote_clone.service
```

## Troubleshooting

### Deployment fails with dependency errors

The deployment script is configured to continue even if pip install fails (some dependencies may have conflicts). As long as the required packages are already installed, the deployment will succeed.

### Service fails to start

Check the logs:
```bash
sudo journalctl -u evernote_clone.service -n 50
```

Common issues:
- Missing environment variables in `.env`
- Database connection issues
- Missing Python dependencies

### Permission errors

Fix ownership:
```bash
cd /var/www/evernote_clone
sudo chown -R www-data:www-data .
sudo chmod -R 755 staticfiles
```

## Production URLs

- **Main Site**: http://46.224.109.101
- **Admin Panel**: http://46.224.109.101/admin/
- **Domain**: agspace.in (configured in ALLOWED_HOSTS)

## Superuser Accounts

The following superuser accounts are configured:

1. **Admin Account** (auto-created from .env):
   - Email: admin@agspace.in
   - Username: admin
   - Password: admin123

2. **Developer Account**:
   - Email: waghgaurav.g@gmail.com
   - Username: gauravwagh
   - Password: Admin@2025!

Credentials are managed via environment variables in `/var/www/evernote_clone/.env`.
