# CalQueue Backend

REST API and real-time server for the CalQueue bank branch queue management system. Handles customer ticketing, teller workflows, branch configuration, and live queue events.

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | Django 5.1 + Django REST Framework |
| Auth | SimpleJWT (user) + custom Device JWT |
| Real-time | Django Channels + Redis channel layer |
| Task queue | Celery + Redis |
| Database | PostgreSQL (SQLite for local dev) |
| Admin | django-unfold |
| Package manager | uv |

## Getting Started

### Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/)
- Redis
- PostgreSQL (or set `USE_SQLITE=True` to skip)

### Local Development

```bash
# Install dependencies
uv sync

# Configure environment
cp .env.example .env
# Edit .env — set USE_SQLITE=True to skip Postgres locally

# Run database migrations
uv run manage.py migrate

# Create an admin user
uv run manage.py createsuperuser

# Start the dev server (port 8090 by default)
uv run manage.py runserver 0.0.0.0:8090
```

### Background Workers

Open separate terminals for each worker:

```bash
# Celery task worker
uv run celery -A config worker -l INFO

# Celery beat scheduler (periodic tasks)
uv run celery -A config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

### Docker (production-like)

```bash
docker compose up -d --build
docker compose exec main python manage.py migrate
docker compose exec main python manage.py createsuperuser
```

### Code Quality

Pre-commit hooks enforce formatting and linting on every commit:

```bash
pre-commit run --all-files   # black + flake8 (max-line-length=150) + migration checks
```

### Running Tests

```bash
# All tests
uv run manage.py test

# Single test
uv run manage.py test accounts.tests.TestClassName.test_method_name
```

## Environment Variables

| Variable | Description |
|---|---|
| `USE_SQLITE` | Set `True` to use SQLite instead of PostgreSQL |
| `POSTGRES_DB` / `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_HOST` / `POSTGRES_PORT` | PostgreSQL connection settings |
| `REDIS_HOST` / `REDIS_PORT` | Redis connection (required for Channels, Celery, cache) |
| `USE_S3` | Set `True` to store media files in S3 |
| `AWS_*` | AWS credentials and bucket config (when `USE_S3=True`) |
| `SECRET_KEY` | Django secret key |
| `DEBUG` | Enable Django debug mode |
| `ALLOWED_HOSTS` | Comma-separated list of allowed hostnames |

Redis uses four separate database indices:

| Index | Purpose |
|---|---|
| DB 0 | Django Channels layer |
| DB 1 | Django cache |
| DB 2 | Celery broker |
| DB 3 | Celery result backend |

## Project Structure

```
config/               # Settings, root URLs, Celery config, exception handler
accounts/             # Custom user model, OTP flows, JWT auth, profile/ID/address
configuration/        # Branch management, working hours, physical device auth
core/                 # Banking service catalogue (MainService → Service → SubService)
pages/                # Static/template views
helpers/              # Shared utilities: OTP, reference codes, exception classes
```

### Django Apps

| App | Purpose |
|---|---|
| `accounts` | `CustomUser` (extends `AbstractUser`), OTP, JWT auth via `dj-rest-auth`, profile/ID/address endpoints |
| `configuration` | `Branch`, `BranchWorkingHours`, `Device` model with device-specific JWT tokens |
| `core` | Service catalogue — `MainService`, `Service`, `SubService` with enforced hierarchy; ticket and queue management |
| `config` | Settings, Celery, URL root, custom exception handler |
| `helpers` | OTP generation, reference codes, domain exception classes |

## Authentication

Two parallel JWT authentication stacks run side-by-side:

**User JWT** — standard `Bearer` tokens for `CustomUser` via `rest_framework_simplejwt`. Access tokens expire in 5 minutes; refresh tokens last 1 day with rotation and blacklisting.

**Device JWT** — custom `DeviceAccessToken` / `DeviceRefreshToken` types for physical teller kiosk devices. `DeviceJWTAuthentication` checks the `token_type` claim before taking ownership; if it is not `device_access`, it defers to the standard `JWTAuthentication`. Device refresh blacklisting uses Redis rather than the database blacklist table. Use the `IsDevice` permission class to restrict endpoints to devices only.

## API Documentation

The API is self-documented via OpenAPI:

| URL | Interface |
|---|---|
| `/api/docs/` | Swagger UI |
| `/api/redoc/` | Redoc |
| `/api/schema/` | Raw OpenAPI schema |

### URL Prefix Conventions

| Prefix | App |
|---|---|
| `/auth/` | User authentication (`accounts.urls`) |
| `/configuration/` | Branch and device management (`configuration.urls`) |
| `/core/` | Queue, ticket, and service endpoints |
| `/bknd-ctr/` | Django admin |

## Error Handling

All API errors go through `config.exceptions.custom_exception_handler`. Every error response has the shape:

```json
{
  "status_code": 400,
  "errorCode": 101,
  "errorMsg": "Human-readable message"
}
```

Raise from `helpers.exceptions` for domain errors; subclass `config.exceptions.BaseException` for generic API errors.

## Audit Logging

`django-auditlog` tracks changes to `CustomUser`, `UserID`, `UserAddress`, `Branch`, `BranchWorkingHours`, and `Device`. Sensitive fields (`password`, `last_login`) are excluded.

## Admin

The admin panel is available at `/bknd-ctr/` and uses `django-unfold` for an improved UI.
