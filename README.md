# Evernote Clone

A production-ready Django application that replicates core Evernote functionality with modern web technologies.

## 🚀 Features

- **User Authentication**: Custom user model with email-based authentication
- **Notes Management**: Create, edit, delete, and organize notes
- **Rich Text Editor**: TinyMCE integration for rich text editing
- **Notebooks**: Organize notes into customizable notebooks
- **Tagging System**: Tag notes for better organization
- **Search Functionality**: Full-text search across notes and tags
- **Pin & Archive**: Pin important notes and archive old ones
- **File Attachments**: Upload and attach files to notes
- **Responsive Design**: Modern Bootstrap 5 UI that works on all devices
- **Production Ready**: Docker, Nginx, PostgreSQL, Redis configuration

## 🛠️ Technology Stack

- **Backend**: Django 5.2.6, Python 3.11+
- **Database**: PostgreSQL (production), SQLite (development)
- **Frontend**: Bootstrap 5, TinyMCE, Font Awesome
- **Caching**: Redis
- **Web Server**: Nginx + Gunicorn
- **Containerization**: Docker & Docker Compose

## 📋 Prerequisites

- Python 3.11+
- Node.js (for development)
- Docker & Docker Compose (for production)
- PostgreSQL (for production)

## 🏃‍♂️ Quick Start

### Development Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd evernote_clone
   ```

2. **Create UV virtual environment**
   ```bash
   # Using UV (recommended)
   uv venv ~/.venv/evernote_clone --python $(which python)
   source ~/.venv/evernote_clone/bin/activate
   
   # Or use the convenience script
   source activate_env.sh
   ```

3. **Install dependencies**
   ```bash
   # Using UV (faster)
   uv pip install -r requirements/local.txt
   
   # Or using regular pip
   pip install -r requirements/local.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

5. **Run migrations**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

6. **Create superuser**
   ```bash
   python manage.py createsuperuser
   ```

7. **Run development server**
   ```bash
   python manage.py runserver
   ```

Visit `http://127.0.0.1:8000` to access the application.

### Production Deployment with Docker

1. **Clone and configure**
   ```bash
   git clone <repository-url>
   cd evernote_clone
   ```

2. **Update environment variables**
   ```bash
   # Edit docker-compose.yml with your production settings
   # Set strong SECRET_KEY, database passwords, etc.
   ```

3. **Build and run**
   ```bash
   docker-compose up -d --build
   ```

4. **Run initial setup**
   ```bash
   docker-compose exec web python manage.py migrate
   docker-compose exec web python manage.py createsuperuser
   ```

The application will be available at `http://localhost`.

## 📁 Project Structure

```
evernote_clone/
├── config/                 # Django configuration
│   ├── settings/          # Environment-based settings
│   │   ├── base.py       # Base settings
│   │   ├── local.py      # Development settings
│   │   └── production.py # Production settings
│   ├── urls.py           # Main URL configuration
│   ├── wsgi.py           # WSGI configuration
│   └── asgi.py           # ASGI configuration
├── accounts/              # User authentication app
├── notes/                 # Notes management app
├── core/                  # Shared utilities
├── templates/             # Django templates
├── static/                # Static files (CSS, JS, images)
├── media/                 # User uploads
├── requirements/          # Python dependencies
│   ├── base.txt          # Base requirements
│   ├── local.txt         # Development requirements
│   └── production.txt    # Production requirements
├── Dockerfile            # Docker configuration
├── docker-compose.yml    # Docker Compose configuration
├── nginx.conf            # Nginx configuration
└── manage.py             # Django management script
```

## 🔧 Configuration

### Environment Variables

Key environment variables for production:

- `SECRET_KEY`: Django secret key
- `DEBUG`: Set to `False` for production
- `ALLOWED_HOSTS`: Comma-separated list of allowed hosts
- `DATABASE_*`: Database configuration
- `EMAIL_*`: Email configuration
- `REDIS_URL`: Redis connection string

### Settings

The project uses environment-based settings:

- **Development**: `config.settings.local`
- **Production**: `config.settings.production`

## 🔐 Security Features

- CSRF protection enabled
- SQL injection protection via Django ORM
- XSS protection with content sanitization
- Secure headers configuration
- HTTPS enforcement in production
- Session security settings

## 📱 API Endpoints

### Authentication
- `POST /accounts/login/` - User login
- `POST /accounts/logout/` - User logout
- `POST /accounts/signup/` - User registration

### Notes
- `GET /` - Dashboard (list notes)
- `GET /note/<slug>/` - Note detail
- `POST /note/new/` - Create note
- `PUT /note/<slug>/edit/` - Update note
- `DELETE /note/<slug>/delete/` - Delete note

### Notebooks
- `GET /notebooks/` - List notebooks
- `GET /notebook/<slug>/` - Notebook detail
- `POST /notebook/new/` - Create notebook

### Search
- `GET /search/?q=<query>` - Search notes

## 🧪 Testing

Run tests:
```bash
python manage.py test
```

With coverage:
```bash
coverage run --source='.' manage.py test
coverage report
```

## 📈 Performance Optimization

- Database query optimization with `select_related` and `prefetch_related`
- Static files compression and caching
- Redis caching for sessions and frequently accessed data
- Pagination for large datasets
- Optimized Docker images

## 🚀 Deployment

### Docker Deployment

The project includes production-ready Docker configuration:

1. Multi-stage Docker builds for optimization
2. Nginx for static file serving and reverse proxy
3. PostgreSQL for robust data storage
4. Redis for caching and sessions

### Manual Deployment

For manual deployment on a server:

1. Set up PostgreSQL and Redis
2. Configure Nginx with the provided configuration
3. Use Gunicorn as the WSGI server
4. Set appropriate environment variables
5. Run migrations and collect static files

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run tests and ensure they pass
6. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:

1. Check the documentation
2. Search existing issues
3. Create a new issue with detailed information

## 🔄 Changelog

### v1.0.0
- Initial release
- User authentication system
- Notes and notebooks management
- Rich text editor integration
- Search functionality
- Production-ready deployment configuration
