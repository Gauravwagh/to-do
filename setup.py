#!/usr/bin/env python
"""
Setup script for Evernote Clone Django project.
This script helps set up the project for development.
"""

import os
import sys
import subprocess
import argparse


def run_command(command, description):
    """Run a shell command and print status."""
    print(f"\n🔄 {description}...")
    try:
        subprocess.run(command, shell=True, check=True)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error during {description}: {e}")
        return False


def setup_development():
    """Set up the project for development."""
    print("🚀 Setting up Evernote Clone for development...")
    
    # Check if virtual environment is activated
    if not hasattr(sys, 'real_prefix') and not sys.base_prefix != sys.prefix:
        print("⚠️  Warning: Virtual environment not detected. It's recommended to use a virtual environment.")
        response = input("Continue anyway? (y/N): ")
        if response.lower() != 'y':
            print("Setup cancelled.")
            return False
    
    # Install dependencies
    if not run_command("pip install -r requirements/local.txt", "Installing dependencies"):
        return False
    
    # Create .env file if it doesn't exist
    if not os.path.exists('.env'):
        if os.path.exists('.env.example'):
            run_command("cp .env.example .env", "Creating .env file")
            print("📝 Please edit .env file with your settings")
        else:
            print("⚠️  .env.example not found. Creating basic .env file...")
            with open('.env', 'w') as f:
                f.write("DEBUG=True\n")
                f.write("SECRET_KEY=django-insecure-change-me-in-production\n")
                f.write("DJANGO_SETTINGS_MODULE=config.settings.local\n")
    
    # Run migrations
    if not run_command("python manage.py makemigrations", "Creating migrations"):
        return False
    
    if not run_command("python manage.py migrate", "Running migrations"):
        return False
    
    # Create superuser
    print("\n👤 Creating superuser account...")
    try:
        subprocess.run("python manage.py createsuperuser", shell=True, check=True)
        print("✅ Superuser created successfully")
    except subprocess.CalledProcessError:
        print("⚠️  Superuser creation skipped or failed")
    
    # Collect static files
    run_command("python manage.py collectstatic --noinput", "Collecting static files")
    
    print("\n🎉 Setup completed successfully!")
    print("\n📋 Next steps:")
    print("1. Edit .env file with your settings if needed")
    print("2. Run: python manage.py runserver")
    print("3. Visit: http://127.0.0.1:8000")
    print("4. Optional: Run setup initial data with your superuser email:")
    print("   python manage.py setup_initial_data --user-email your-email@example.com")
    
    return True


def setup_production():
    """Set up the project for production using Docker."""
    print("🐳 Setting up Evernote Clone for production with Docker...")
    
    # Check if docker-compose is available
    try:
        subprocess.run("docker-compose --version", shell=True, check=True, 
                      capture_output=True)
    except subprocess.CalledProcessError:
        print("❌ Docker Compose not found. Please install Docker and Docker Compose first.")
        return False
    
    print("⚠️  Make sure to update docker-compose.yml with your production settings!")
    print("   - Set strong SECRET_KEY")
    print("   - Update database passwords")
    print("   - Configure ALLOWED_HOSTS")
    
    response = input("Continue with Docker setup? (y/N): ")
    if response.lower() != 'y':
        print("Setup cancelled.")
        return False
    
    # Build and start containers
    if not run_command("docker-compose up -d --build", "Building and starting containers"):
        return False
    
    # Run migrations
    if not run_command("docker-compose exec web python manage.py migrate", 
                      "Running migrations in container"):
        return False
    
    # Collect static files
    run_command("docker-compose exec web python manage.py collectstatic --noinput", 
               "Collecting static files in container")
    
    print("\n🎉 Production setup completed!")
    print("\n📋 Next steps:")
    print("1. Create superuser: docker-compose exec web python manage.py createsuperuser")
    print("2. Visit: http://localhost")
    print("3. Optional: Set up initial data:")
    print("   docker-compose exec web python manage.py setup_initial_data --user-email your-email@example.com")
    
    return True


def main():
    """Main setup function."""
    parser = argparse.ArgumentParser(description='Setup Evernote Clone Django project')
    parser.add_argument('--production', action='store_true', 
                       help='Setup for production using Docker')
    parser.add_argument('--development', action='store_true', 
                       help='Setup for development (default)')
    
    args = parser.parse_args()
    
    if args.production:
        success = setup_production()
    else:
        success = setup_development()
    
    if success:
        print("\n🎊 Welcome to Evernote Clone!")
    else:
        print("\n💥 Setup failed. Please check the errors above.")
        sys.exit(1)


if __name__ == '__main__':
    main()









