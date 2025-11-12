# Conference Portal API

A modern RESTful API service for conference portal backend, built with FastAPI.

## 🛠️ Tech Stack

- **Backend Framework**: FastAPI
- **Database**: PostgreSQL (using SQLAlchemy + asyncpg)
- **Cache**: Redis
- **Authentication**: Firebase Admin SDK + JWT
- **Authorization**: RBAC (Role-Based Access Control)
- **File Storage**: AWS S3
- **Monitoring**: Sentry
- **Containerization**: Docker
- **Package Manager**: Poetry
- **Database Migration**: Alembic
- **Python Version**: 3.13+

## 📋 Prerequisites

- Python 3.13+
- PostgreSQL 12+
- Redis 6+
- Docker (optional)
- Firebase project with credentials
- AWS S3 bucket (for file storage)

## 🚀 Quick Start

### 1. Install Poetry

[Poetry Installation Guide](https://python-poetry.org/docs/#system-requirements)

### 2. Install pyenv (Recommended | Optional)

[pyenv Installation Guide](https://github.com/pyenv/pyenv#installation)

#### Install Python 3.13

```bash
pyenv install 3.13.x  # Replace x with the version you want to install
pyenv local 3.13.x   # Replace x with the version you installed
```

### 3. Install Dependencies

#### Using pyenv

```bash
pyenv local 3.13.x   # Replace x with the version you installed
poetry env use 3.13.x # Replace x with the version you installed
poetry install
```

#### Without pyenv

```bash
poetry install
```

### 4. Environment Setup

Create a `.env` file in the project root:

```bash
cp example.env .env
```

Edit the `.env` file with your configuration values:

```bash
ENV=dev

# AWS
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_S3_REGION_NAME=your-region

# Firebase
# FIREBASE_AUTH_EMULATOR_HOST="127.0.0.1:9099"  # Uncomment when using Firebase Emulator in development
FIREBASE_TEST_PHONE_NUMBER=your-test-phone

# Database
DATABASE_HOST=localhost
DATABASE_USER=postgres
DATABASE_PASSWORD=your-password
DATABASE_PORT=5432
DATABASE_NAME=conference_db

# Redis
REDIS_URL=redis://localhost:6379/0

# Rate Limiting (optional)
# RATE_LIMITERS_CONFIG_PATH=/path/to/rate_limiters.yaml

# Sentry (optional)
SENTRY_URL=your-sentry-dsn

# JWT (optional, for admin authentication)
JWT_SECRET_KEY=your-jwt-secret-key
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=7
REFRESH_TOKEN_HASH_SALT=your-salt
REFRESH_TOKEN_HASH_PEPPER=your-pepper
```

#### Firebase Credentials Setup

Firebase credentials are loaded in the following order:

1. Path specified by `GOOGLE_APPLICATION_CREDENTIALS` environment variable
2. `env/google_certificate.json`
3. `/etc/secrets/google_certificate.json`

Place your Firebase service account credentials JSON file in any of the above locations.

#### Rate Limiter Configuration (Optional)

Rate Limiter configuration is loaded in the following order:

1. Path specified by `RATE_LIMITERS_CONFIG_PATH` environment variable
2. `env/rate_limiters.yaml`
3. `/etc/secrets/rate_limiters.yaml`

If no configuration file is provided, default values will be used.

### 5. Database Setup

#### Run Database Migrations

```bash
# Create a new migration file
poetry run alembic revision --autogenerate -m "description"

# Run migrations
poetry run alembic upgrade head

# Rollback to previous version
poetry run alembic downgrade -1
```

#### Initialize RBAC Data

```bash
# Initialize RBAC system (verbs/resources/permissions/roles)
poetry run python -m portal.cli.main init-rbac
```

#### Create Superuser

```bash
# Create admin superuser
poetry run python -m portal.cli.main create-superuser
```

### 6. Firebase Emulators Setup (Optional)

This feature is used to test Firebase authentication functionality in a local environment.

Requirements:

- [Firebase CLI](https://firebase.google.com/docs/cli?authuser=0#mac-linux-auto-script) installed
- Firebase project with credentials
- Firebase project with Authentication enabled
- [Quickstart-js](https://github.com/firebase/quickstart-js) project cloned

```bash
# Install Firebase CLI
npm install -g firebase-tools

# Login to Firebase
firebase login

# Initialize Firebase emulators in your project
firebase init emulators

# Start Firebase emulators
firebase emulators:start --only auth
```

The Auth emulator runs on `http://localhost:9099` by default.

Set in the `.env` file:

```bash
FIREBASE_AUTH_EMULATOR_HOST="127.0.0.1:9099"
```

### 7. Run the Application

#### Development Environment

```bash
# Using uvicorn development server
poetry run uvicorn portal:app --reload --host 0.0.0.0 --port 8000
```

#### Production Environment

```bash
# Using gunicorn (via entrypoint.sh)
poetry run gunicorn -c gunicorn_conf.py "portal:app"
```

The application runs on `http://localhost:8000` by default.

## 🐳 Docker Deployment

### Build Docker Image

```bash
# Build Docker image
docker build -t conf-portal-api .

# Run container
docker run -p 8000:8000 --env-file .env conf-portal-api
```

## 📚 API Documentation

Once the application is running, you can access:

- **Interactive API Docs**: <http://localhost:8000/docs>
- **ReDoc Documentation**: <http://localhost:8000/redoc>
- **Health Check**: <http://localhost:8000/api/healthz>

### API Endpoints

The API is organized into the following modules:

#### Public Endpoints

- `/api/v1/account` - User account management
- `/api/v1/conference` - Conference management
- `/api/v1/event_info` - Event information and schedules
- `/api/v1/faq` - FAQ management
- `/api/v1/fcm_device` - Push notification device management
- `/api/v1/feedback` - User feedback system
- `/api/v1/testimony` - User testimonials
- `/api/v1/workshop` - Workshop management

#### Admin Endpoints

- `/api/v1/admin/auth` - Admin authentication
- `/api/v1/admin/user` - User management
- `/api/v1/admin/conference` - Conference management
- `/api/v1/admin/event_info` - Event information management
- `/api/v1/admin/faq` - FAQ management
- `/api/v1/admin/feedback` - Feedback management
- `/api/v1/admin/testimony` - Testimony management
- `/api/v1/admin/instructor` - Instructor management
- `/api/v1/admin/location` - Location management
- `/api/v1/admin/file` - File management
- `/api/v1/admin/notification` - Notification management
- `/api/v1/admin/log` - Log management
- `/api/v1/admin/permission` - Permission management
- `/api/v1/admin/resource` - Resource management
- `/api/v1/admin/role` - Role management
- `/api/v1/admin/verb` - Verb management

## 🧪 Testing

Run the test suite:

```bash
# Run all tests
poetry run pytest

# Run tests with coverage
poetry run pytest --cov=portal

# Run specific test file
poetry run pytest tests/handlers/test_account.py

# Run specific test function
poetry run pytest tests/handlers/test_account.py::test_function_name

# Run tests with verbose output
poetry run pytest -v

# Run tests and stop on first failure
poetry run pytest -x
```

### Test Structure

Test files should follow this structure:

```
tests/
├── conftest.py              # pytest configuration and shared fixtures
├── fixtures/               # Test fixtures
│   ├── container.py       # Container fixtures
│   ├── context.py         # Context fixtures
│   ├── handlers.py        # Handler fixtures
│   ├── providers.py       # Provider fixtures
│   └── test_data.py       # Test data
├── handlers/              # Handler tests
├── libs/                  # Shared library tests
└── providers/             # Provider tests
```

## 📁 Project Structure

```
conf-portal-api/
├── portal/                    # Main application
│   ├── __init__.py
│   ├── __main__.py
│   ├── main.py               # FastAPI application entry point
│   ├── config.py             # Configuration
│   ├── container.py          # Dependency injection container
│   ├── authorization/       # Authentication related
│   │   └── access_token.py  # Token authentication
│   ├── cli/                  # CLI tools
│   │   ├── main.py          # CLI entry point
│   │   ├── superuser.py     # Create superuser
│   │   └── rbac.py          # RBAC initialization
│   ├── exceptions/           # Exception handling
│   │   └── responses/       # Exception responses
│   ├── handlers/            # Business logic handlers
│   │   ├── admin/          # Admin handlers
│   │   └── ...             # Other handlers
│   ├── libs/                # Shared libraries
│   │   ├── authorization/  # Authorization related
│   │   ├── consts/         # Constants
│   │   ├── contexts/       # Context management
│   │   ├── database/       # Database related
│   │   ├── decorators/     # Decorators
│   │   ├── depends/        # FastAPI dependencies
│   │   ├── http_client/    # HTTP client
│   │   ├── logger/         # Logging
│   │   ├── shared/         # Shared utilities
│   │   └── utils/          # Utility functions
│   ├── middlewares/         # Middlewares
│   │   ├── auth_middleware.py      # Authentication middleware
│   │   └── core_request.py         # Core request middleware
│   ├── models/              # Database models
│   │   ├── mixins/         # Model mixins
│   │   └── ...             # Other models
│   ├── providers/           # Service providers
│   │   ├── firebase/       # Firebase provider
│   │   ├── jwt_provider.py # JWT provider
│   │   └── ...             # Other providers
│   ├── route_classes/       # Route classes
│   │   ├── auth_route.py   # Authentication route
│   │   └── log_route.py    # Log route
│   ├── routers/            # API routers
│   │   ├── api_root.py     # API root router
│   │   ├── auth_router.py  # Authentication router
│   │   └── apis/           # API routers
│   │       └── v1/        # v1 API
│   │           ├── admin/ # Admin endpoints
│   │           └── ...    # Other endpoints
│   ├── schemas/            # Shared schemas
│   └── serializers/       # Serializers (request/response models)
│       └── v1/            # v1 serializers
│           ├── admin/     # Admin serializers
│           └── ...        # Other serializers
├── alembic/                # Database migrations
│   ├── versions/          # Migration versions
│   └── env.py             # Alembic environment configuration
├── tests/                  # Test suite
├── docs/                   # Documentation
├── env/                    # Environment configuration files
│   ├── google_certificate.json  # Firebase credentials (should not be committed)
│   └── rate_limiters.yaml       # Rate Limiter configuration (optional)
├── Dockerfile             # Docker configuration
├── entrypoint.sh          # Container entry point
├── gunicorn_conf.py       # Gunicorn configuration
├── pyproject.toml         # Poetry configuration
├── alembic.ini            # Alembic configuration
└── README.md              # This file
```

## 🔧 Configuration

### Environment Variables

Key configurable environment variables:

#### Application Base Settings

- `ENV`: Environment (dev/stg/prod)
- `APP_FQDN`: Application fully qualified domain name
- `HOST`: Server host (default: 127.0.0.1)
- `PORT`: Server port (default: 8000)

#### Database Settings

- `DATABASE_HOST`: Database host
- `DATABASE_USER`: Database user
- `DATABASE_PASSWORD`: Database password
- `DATABASE_PORT`: Database port (default: 5432)
- `DATABASE_NAME`: Database name
- `DATABASE_SCHEMA`: Database schema (default: public)
- `DATABASE_CONNECTION_POOL_MAX_SIZE`: Connection pool max size (default: 10)
- `SQL_ECHO`: Whether to output SQL statements (default: False)

#### Redis Settings

- `REDIS_URL`: Redis connection URL
- `REDIS_DB`: Redis database number (default: 0)
- `TOKEN_BLACKLIST_REDIS_DB`: Token blacklist Redis database number (default: 1)

#### CORS Settings

- `CORS_ALLOWED_ORIGINS`: Allowed origins (space-separated)
- `CORS_ALLOW_ORIGINS_REGEX`: Allowed origins regex pattern

#### JWT Settings

- `JWT_SECRET_KEY`: JWT secret key
- `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`: Access token expiration time (minutes, default: 60)
- `REFRESH_TOKEN_EXPIRE_DAYS`: Refresh token expiration time (days, default: 7)
- `REFRESH_TOKEN_HASH_SALT`: Refresh token hash salt
- `REFRESH_TOKEN_HASH_PEPPER`: Refresh token hash pepper

#### AWS S3 Settings

- `AWS_ACCESS_KEY_ID`: AWS access key ID
- `AWS_SECRET_ACCESS_KEY`: AWS secret access key
- `AWS_S3_REGION_NAME`: AWS S3 region
- `AWS_STORAGE_BUCKET_NAME`: S3 bucket name (default: conf-portal-api)
- `MAX_UPLOAD_SIZE`: Maximum upload file size (bytes, default: 5MB)

#### Firebase Settings

- `FIREBASE_AUTH_EMULATOR_HOST`: Firebase Auth Emulator host (development)
- `FIREBASE_TEST_PHONE_NUMBER`: Test phone number
- `GOOGLE_APPLICATION_CREDENTIALS`: Google application credentials path

#### Other Settings

- `SENTRY_URL`: Sentry DSN (error tracking)
- `RATE_LIMITERS_CONFIG_PATH`: Rate Limiter configuration file path

### Gunicorn Configuration

The Gunicorn configuration file is located at `gunicorn_conf.py`, main settings include:

- `workers`: Number of worker processes (default: CPU core count)
- `worker_class`: Worker class (default: uvicorn.workers.UvicornWorker)
- `timeout`: Request timeout (seconds, default: 120)
- `graceful_timeout`: Graceful shutdown timeout (seconds, default: 150)
- `max_requests`: Maximum requests per worker (default: 100000)

You can override the number of workers via the `GUNICORN_WORKERS` environment variable.

## 🔐 Authentication & Authorization

### Authentication Mechanisms

The project supports two authentication methods:

1. **Firebase Token**: For general user authentication
2. **JWT Token**: For admin authentication

### Authorization Mechanism

Uses RBAC (Role-Based Access Control) system:

- **Verbs**: Actions (e.g., read, write, delete)
- **Resources**: Resources (e.g., user, conference, workshop)
- **Permissions**: Permissions (verb + resource, e.g., user:read)
- **Roles**: Roles (containing multiple permissions)
- **Users**: Users (can be assigned roles)

### Using AuthRouter

`AuthRouter` integrates authentication and authorization functionality, allowing you to specify authentication and permission requirements directly in route definitions:

```python
from portal.routers.auth_router import AuthRouter

router = AuthRouter(tags=["Admin - User"])

@router.get(
    path="/pages",
    permissions=["user:read"],  # Automatically performs authentication and permission checks
    status_code=status.HTTP_200_OK,
    response_model=UserPages
)
async def get_user_pages(...):
    ...
```

For detailed usage instructions, refer to `docs/auth_router_readme.md`.

## 🚀 Deployment

### Production Deployment

1. Set production environment variables
2. Configure database and Redis
3. Set up Firebase credentials
4. Configure AWS S3 for file storage
5. Set up Sentry for monitoring
6. Build Docker image
7. Run Docker container

### Environment-Specific Configuration

- **Development Environment**: `ENV=dev`
- **Staging Environment**: `ENV=stg`
- **Production Environment**: `ENV=prod`

## 📝 Development Guidelines

### Database Migrations

- Use Alembic for database migrations
- **Do not** manually modify files in the `alembic/` directory
- When creating constraints, you don't need to provide a name. The project's naming convention is already configured in `libs/database/orm`

### API Routers

- BaseModels definitions should be placed in the `serializers/` directory, aligned with the router version
- All API router prefixes should be set only at the `__init__.py` level

### Testing

- Use pytest for testing
- Use `pytest.mark.asyncio` decorator for async tests
- Test files should be placed in the `tests/` directory
- Test files should be named `test_<module_name>.py`
- Test functions should be named `test_<function_name>`
- Fixtures should be placed in the `tests/fixtures/` directory

### Tracing

- Use OpenTelemetry for tracing
- Every function in handlers and providers should use the `@distributed_trace` decorator
