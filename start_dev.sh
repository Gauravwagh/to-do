#!/bin/bash
# Development startup script for Evernote Clone

echo "🚀 Starting Evernote Clone Development Environment..."
echo "=================================================="

# Activate virtual environment
source .venv/bin/activate

# Set environment variables
export DJANGO_SETTINGS_MODULE=config.settings.local

echo "✅ Virtual environment activated!"
echo "📍 Python: $(which python)"
echo "📦 Pip: $(which pip)"
echo "🔧 Django Settings: $DJANGO_SETTINGS_MODULE"
echo ""

# Check if database needs migrations
echo "🔍 Checking database status..."
python manage.py showmigrations --plan | grep -q "\[ \]" && echo "⚠️  Database migrations pending" || echo "✅ Database up to date"

echo ""
echo "💡 Available commands:"
echo "   python manage.py runserver    - Start development server"
echo "   python manage.py shell        - Django shell"
echo "   python manage.py makemigrations - Create migrations"
echo "   python manage.py migrate      - Run migrations"
echo "   python manage.py createsuperuser - Create admin user"
echo "   python verify_setup.py        - Verify environment setup"
echo ""
echo "🌐 To start the development server:"
echo "   python manage.py runserver"
echo ""
echo "To deactivate: deactivate"
