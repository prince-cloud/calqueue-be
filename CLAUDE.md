# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Local development (uv)
```bash
uv run manage.py migrate
uv run manage.py runserver
uv run manage.py createsuperuser
uv run manage.py makemigrations
```

### Run a single test
```bash
uv run manage.py test accounts.tests.TestClassName.test_method_name
```

### Celery (local)
```bash
# Worker
uv run celery -A config worker -l INFO

# Beat scheduler
uv run celery -A config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

### Docker (production-like)
```bash
docker compose up -d --build
docker compose exec main python manage.py migrate
docker compose exec main python manage.py createsuperuser
```

### Code quality (enforced by pre-commit)
```bash
pre-commit run --all-files   # black + flake8 (max-line-length=150) + migration checks
```

### Environment
Copy `.env` for local dev. Set `USE_SQLITE=True` to skip Postgres; otherwise configure `POSTGRES_*` vars. Redis is required — set `REDIS_HOST`, `REDIS_PORT`, etc.

## Architecture

This is a **Django 5.1 REST API** (DRF + SimpleJWT) built on the [Lithium](https://github.com/wsvincent/lithium) boilerplate, domain-adapted for a bank branch queue management system (CalQueue).

### Django apps

| App | Purpose |
|---|---|
| `accounts` | Custom user model (`CustomUser` extends `AbstractUser`), OTP flows, JWT auth via `dj-rest-auth`, profile/ID/address endpoints |
| `configuration` | Branch management (`Branch`, `BranchWorkingHours`), physical device auth (`Device` model with its own JWT token type) |
| `core` | Banking service catalogue — `MainService`, `Service`, `SubService` with a strict hierarchy enforced via `clean()` and lookup maps (`MAIN_SERVICE_MAP`, `SERVICE_SUBSERVICE_MAP`) |
| `pages` | Static/template views |
| `config` | Settings, Celery config, URL root, custom exception handler |
| `helpers` | Shared utilities: OTP generation, reference codes, exception classes |

### Authentication — two parallel JWT stacks

1. **User JWT** (`rest_framework_simplejwt`) — standard `Bearer` tokens for `CustomUser`. Short-lived access (5 min), 1-day refresh with rotation + blacklist via `rest_framework_simplejwt.token_blacklist`.

2. **Device JWT** (`configuration.tokens`) — custom `DeviceAccessToken` / `DeviceRefreshToken` token types for physical teller devices. `DeviceJWTAuthentication` inspects the `token_type` claim before taking ownership; if it's not `device_access`, it returns `None` and lets `JWTAuthentication` handle it. Device refresh blacklisting uses Redis (not the DB blacklist table). Use `IsDevice` permission class for device-only endpoints.

### Redis usage (separate DB indices)
- DB 0: Django Channels layer
- DB 1: Django cache
- DB 2: Celery broker
- DB 3: Celery result backend

### Admin
`django-unfold` replaces the default admin theme. Admin is mounted at `/bknd-ctr/`.

### API docs
- Swagger UI: `/api/docs/`
- Redoc: `/api/redoc/`
- Schema: `/api/schema/`

### Exception handling
All API errors flow through `config.exceptions.custom_exception_handler`. The response shape is `{status_code, errorCode, errorMsg}`. Raise from `helpers.exceptions` for domain errors; raise `config.exceptions.BaseException` subclasses for generic API errors.

### Audit logging
`django-auditlog` is registered on `CustomUser`, `UserID`, `UserAddress`, `Branch`, `BranchWorkingHours`, and `Device`. Sensitive fields (`password`, `last_login`) are excluded.

### File storage
Local by default. Set `USE_S3=True` + AWS env vars to switch media storage to S3 (`storages.backends.s3boto3.S3Boto3Storage`); static files stay on Whitenoise.

### URL prefix conventions
- `/auth/` — user authentication endpoints (`accounts.urls`)
- `/configuration/` — branch and device endpoints (`configuration.urls`)
- `/bknd-ctr/` — Django admin
- `/accounts/` — django-allauth (session-based auth, used internally)
