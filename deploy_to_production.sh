#!/bin/bash
set -e

echo "=== Deploying to Production Server ==="

# Configuration
SERVER="root@46.224.109.101"
BRANCH="${1:-feature/deployment-and-mobile-responsive}"

echo "Branch: $BRANCH"
echo "Server: $SERVER"
echo ""

# Run deployment script on server
ssh $SERVER "bash /var/www/evernote_clone/scripts/deploy.sh $BRANCH"

echo ""
echo "=== Deployment Complete ==="
echo "Site URL: http://46.224.109.101"
echo "Admin URL: http://46.224.109.101/admin/"
