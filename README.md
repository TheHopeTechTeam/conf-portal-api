# Conference APP Backend

## 🛠️ Tech Stack

-   **Backend Framework**: FastAPI + Django 5.1
-   **CMS**: Wagtail 6.3
-   **Database**: PostgreSQL
-   **Cache**: Redis
-   **Authentication**: Firebase Admin SDK
-   **File Storage**: AWS S3
-   **Monitoring**: Sentry
-   **Container**: Docker
-   **Package Manager**: Poetry
-   **Python Version**: 3.11+

## 📋 Prerequisites

-   Python 3.11+
-   PostgreSQL
-   Redis
-   Docker (optional)
-   Firebase project with credentials
-   AWS S3 bucket (for file storage)

## 🚀 Quick Start

### 1. Install Poetry

[Poetry Installation](https://python-poetry.org/docs/#system-requirements)

### 2. Install pyenv (Recommended | Optional)

[pyenv Installation](https://github.com/pyenv/pyenv#installation)

#### Install python 3.11+

```bash
pyenv install 3.11.x # Replace x with the version you want to install
pyenv local 3.11.x # Replace x with the version that you installed
```

### 3. Install Dependencies

#### with pyenv

```bash
pyenv local 3.11.x # Replace x with the version that you installed
poetry env use 3.11.x # Replace x with the version that you installed
poetry install
```

### 3. Environment Setup

Create a `.env` file in the project root:

```bash
cp example.env .env
```

Edit the `.env` file with your own values.

```bash
ENV=dev
DEBUG=True

# Database
DATABASE_HOST=localhost
DATABASE_USER=postgres
DATABASE_PASSWORD=your-password
DATABASE_PORT=5432
DATABASE_NAME=conference_db

# Redis
REDIS_URL=redis://localhost:6379/0

# Firebase
FIREBASE_TEST_PHONE_NUMBER=your-test-phone

# AWS S3 (optional)
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_S3_REGION_NAME=your-region

# CORS
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000

# Sentry (optional)
SENTRY_URL=your-sentry-dsn
```

### 4. Database Setup

```bash
# Run migrations
poetry run python manage.py migrate

# Create superuser
poetry run python manage.py createsuperuser
```

### 5. Run the Application

```bash
# Development server
poetry run uvicorn portal:app --reload --host 0.0.0.0 --port 8000

# Or using Django development server
poetry run python manage.py runserver
```

## 🐳 Docker Deployment

### Build and Run with Docker

```bash
# Build the Docker image
docker build -t conf-portal-api .

# Run the container
docker run -p 8000:8000 conf-portal-api
```

## 📚 API Documentation

Once the application is running, you can access:

-   **Interactive API Docs**: http://localhost:8000/docs
-   **ReDoc Documentation**: http://localhost:8000/redoc

### API Endpoints

The API is organized into the following modules:

-   `/api/v1/account` - User account management
-   `/api/v1/conference` - Conference management
-   `/api/v1/event_info` - Event information and schedules
-   `/api/v1/faq` - FAQ management
-   `/api/v1/fcm_device` - Push notification device management
-   `/api/v1/feedback` - User feedback system
-   `/api/v1/testimony` - User testimonials
-   `/api/v1/workshop` - Workshop management
-   `/api/v1/ticket` - Ticket registration system
-   `/api/v1/instructor` - Instructor profiles
-   `/api/v1/location` - Location and venue management
-   `/api/v1/language` - Multi-language support

## 🧪 Testing

Run the test suite:

```bash
# Run all tests
poetry run pytest

# Run tests with coverage
poetry run pytest --cov=portal

# Run specific test file
poetry run pytest tests/handlers/test_account.py
```

## 📁 Project Structure

```
conf-portal-api/
├── portal/                    # Main application
│   ├── apps/                 # Django applications
│   │   ├── account/         # User account management
│   │   ├── conference/      # Conference management
│   │   ├── workshop/        # Workshop system
│   │   ├── ticket/          # Ticket management
│   │   ├── faq/            # FAQ system
│   │   └── ...             # Other modules
│   ├── routers/            # FastAPI routers
│   ├── serializers/        # API serializers
│   ├── handlers/           # Business logic handlers
│   ├── libs/              # Shared libraries
│   └── configs/           # Configuration files
├── tests/                  # Test suite
├── Dockerfile             # Docker configuration
├── entrypoint.sh          # Container entrypoint
└── pyproject.toml        # Poetry configuration
```

## 🔧 Configuration

### Environment Variables

Key environment variables that can be configured:

-   `DEBUG`: Enable/disable debug mode
-   `ENV`: Environment (dev/production)
-   `DATABASE_*`: Database connection settings
-   `REDIS_URL`: Redis connection URL
-   `FIREBASE_*`: Firebase configuration
-   `AWS_*`: AWS S3 configuration
-   `SENTRY_URL`: Sentry DSN for error tracking
-   `CORS_ALLOWED_ORIGINS`: CORS configuration

### Settings Files

-   `portal/configs/base.py`: Base configuration
-   `portal/configs/dev.py`: Development settings
-   `portal/configs/production.py`: Production settings

## 🚀 Deployment

### Production Deployment

1. Set environment variables for production
2. Configure database and Redis
3. Set up Firebase credentials
4. Configure AWS S3 for file storage
5. Set up Sentry for monitoring
6. Build the Docker image
7. Run the Docker container

### Environment-Specific Configurations

-   **Development**: Uses `portal.configs.dev`
-   **Production**: Uses `portal.configs.production`
