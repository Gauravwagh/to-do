# UV Virtual Environment Setup for Evernote Clone

This document explains how to set up and use the UV virtual environment for the Evernote Clone project.

## 🚀 Quick Start

The project is now configured with a UV virtual environment located at `~/.venv/evernote_clone`.

### Activate the Environment

```bash
# Method 1: Direct activation
source ~/.venv/evernote_clone/bin/activate

# Method 2: Use the convenience script
source activate_env.sh
```

### Verify Environment

```bash
which python
# Should show: /Users/gauravwagh/.venv/evernote_clone/bin/python

python --version
# Should show: Python 3.12.11
```

## 🔧 Project Structure

```
evernote_clone/
├── ~/.venv/evernote_clone/     # UV virtual environment (external)
├── .python-version             # pyenv Python version specification
├── pyproject.toml              # Modern Python project configuration
├── activate_env.sh             # Environment activation script
├── scripts/dev_setup.sh        # Automated development setup
└── ... (rest of Django project)
```

## 📦 Dependencies Management

### Install Dependencies
```bash
# Using UV (faster)
uv pip install -r requirements/local.txt

# Using regular pip
pip install -r requirements/local.txt

# Install from pyproject.toml
uv pip install -e .
```

### Add New Dependencies
```bash
# Add to requirements file and install
echo "new-package>=1.0.0" >> requirements/local.txt
uv pip install new-package

# Or install directly
uv pip install new-package
```

## 🛠️ Development Commands

With the environment activated:

```bash
# Django commands
python manage.py runserver
python manage.py shell
python manage.py makemigrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Setup initial data
python manage.py setup_initial_data --user-email your-email@example.com

# Run tests
python manage.py test
pytest  # if using pytest
```

## 🔄 Environment Management

### Deactivate Environment
```bash
deactivate
```

### Recreate Environment
```bash
# Remove existing environment
rm -rf ~/.venv/evernote_clone

# Create new environment
uv venv ~/.venv/evernote_clone --python $(which python)
source ~/.venv/evernote_clone/bin/activate
uv pip install -r requirements/local.txt
```

### Update Dependencies
```bash
# Update all packages
uv pip install --upgrade -r requirements/local.txt

# Update specific package
uv pip install --upgrade django
```

## 🐍 Python Version Management

The project uses pyenv for Python version management:

- **Current version**: Python 3.12.11 (specified in `.python-version`)
- **UV environment**: Uses the pyenv Python version
- **Compatibility**: Python 3.11+ required

### Change Python Version
```bash
# Change pyenv version
pyenv local 3.11.9  # or any compatible version

# Recreate UV environment with new Python
rm -rf ~/.venv/evernote_clone
uv venv ~/.venv/evernote_clone --python $(which python)
source ~/.venv/evernote_clone/bin/activate
uv pip install -r requirements/local.txt
```

## 📊 Benefits of UV

1. **Speed**: UV is significantly faster than pip for package installation
2. **Reliability**: Better dependency resolution
3. **Modern**: Built with Rust, designed for modern Python workflows
4. **Compatibility**: Drop-in replacement for pip in most cases

## 🚨 Troubleshooting

### Environment Not Found
```bash
# Recreate the environment
uv venv ~/.venv/evernote_clone --python $(which python)
```

### Permission Issues
```bash
# Check ownership
ls -la ~/.venv/evernote_clone/
# Fix if needed
sudo chown -R $(whoami) ~/.venv/evernote_clone/
```

### Package Installation Issues
```bash
# Clear UV cache
uv cache clean

# Use pip as fallback
pip install -r requirements/local.txt
```

### Django Issues
```bash
# Check Django installation
python -c "import django; print(django.get_version())"

# Run system checks
python manage.py check

# Check database
python manage.py showmigrations
```

## 🔗 Useful Scripts

- `activate_env.sh` - Activate environment with helpful information
- `scripts/dev_setup.sh` - Complete development setup automation
- `setup.py` - Legacy setup script (still works)

## 📝 Environment Variables

The project uses these environment variables (in `.env` file):

```env
DEBUG=True
SECRET_KEY=your-secret-key-here
DJANGO_SETTINGS_MODULE=config.settings.local
```

## 🎯 Next Steps

1. **Activate the environment**: `source ~/.venv/evernote_clone/bin/activate`
2. **Create a superuser**: `python manage.py createsuperuser`
3. **Start the server**: `python manage.py runserver`
4. **Visit the app**: http://127.0.0.1:8000

The UV virtual environment is now ready for development! 🎉









