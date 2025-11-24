#!/bin/bash
# Activation script for Evernote Clone UV virtual environment

echo "🚀 Activating Evernote Clone UV Virtual Environment..."
source .venv/bin/activate

# Set environment variables
export DJANGO_SETTINGS_MODULE=config.settings.local

echo "✅ Virtual environment activated!"
echo "📍 Python: $(which python)"
echo "📦 Pip: $(which pip)"
echo "🔧 Django Settings: $DJANGO_SETTINGS_MODULE"
echo ""
echo "💡 Available commands:"
echo "   python manage.py runserver    - Start development server"
echo "   python manage.py shell        - Django shell"
echo "   python manage.py makemigrations - Create migrations"
echo "   python manage.py migrate      - Run migrations"
echo ""
echo "To deactivate: deactivate"









