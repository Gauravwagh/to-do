#!/bin/bash
# Development setup script using UV

set -e

PROJECT_NAME="evernote_clone"
VENV_PATH="$HOME/.venv/$PROJECT_NAME"

echo "🚀 Setting up $PROJECT_NAME development environment with UV..."

# Check if UV is installed
if ! command -v uv &> /dev/null; then
    echo "❌ UV is not installed. Please install it first:"
    echo "   curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Check if pyenv is available and get Python version
if command -v pyenv &> /dev/null; then
    PYTHON_VERSION=$(python --version | cut -d' ' -f2)
    echo "🐍 Using Python $PYTHON_VERSION from pyenv"
    PYTHON_PATH=$(which python)
else
    echo "⚠️  pyenv not found, using system Python"
    PYTHON_PATH="python3"
fi

# Create UV virtual environment
echo "📦 Creating UV virtual environment at $VENV_PATH..."
uv venv "$VENV_PATH" --python "$PYTHON_PATH"

# Activate environment
echo "🔌 Activating virtual environment..."
source "$VENV_PATH/bin/activate"

# Install dependencies
echo "📚 Installing dependencies with UV..."
uv pip install -r requirements/local.txt

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file..."
    cat > .env << EOF
DEBUG=True
SECRET_KEY=django-insecure-dev-key-$(openssl rand -base64 32)
DJANGO_SETTINGS_MODULE=config.settings.local
EOF
    echo "✅ Created .env file with development settings"
fi

# Run migrations
echo "🗃️  Running database migrations..."
python manage.py makemigrations
python manage.py migrate

# Collect static files
echo "📁 Collecting static files..."
python manage.py collectstatic --noinput

echo ""
echo "🎉 Setup completed successfully!"
echo ""
echo "📋 Next steps:"
echo "1. Activate the environment: source ~/.venv/$PROJECT_NAME/bin/activate"
echo "   Or use: source activate_env.sh"
echo "2. Create a superuser: python manage.py createsuperuser"
echo "3. Run the server: python manage.py runserver"
echo "4. Visit: http://127.0.0.1:8000"
echo ""
echo "💡 Useful commands:"
echo "   python manage.py setup_initial_data --user-email your-email@example.com"
echo "   python manage.py shell"
echo "   python manage.py test"









