# CalQueue Security Overview

## Authentication
- Dual JWT stacks: user tokens (5-min access / 1-day refresh) and device tokens (10-hr access / 24-hr refresh)
- Device tokens use a custom `token_type` claim; `DeviceJWTAuthentication` falls back to user JWT if claim doesn't match
- OTP flows for phone (5 min), email (4 min), and password reset (5 min) — 6-digit numeric codes

## Authorization
- `IsAuthenticated`, `AllowAny` (DRF standard)
- `IsDevice` permission class for device-only endpoints
- Soft account deactivation via `deactivated_account` field on `CustomUser`

## Rate Limiting & Brute-Force Protection
- DRF throttling: 60 req/min (anon), 200 req/min (user) — env-configurable
- Login attempt cap: 5 attempts in 5 min for both user and device logins, tracked in Redis

## Token Blacklisting
- User logout explicitly blacklists the refresh token; automatic blacklist on rotation
- Device tokens blacklisted in Redis by JTI with TTL matching token expiry
- Blacklist checked on every authenticated device request

## Password Security
- Django validators: similarity check, min 8 chars, common password list, no all-numeric
- Registration validates via allauth's `clean_password()`

## Input Validation
- Phone: `PhoneNumberField` with uniqueness enforcement
- Email: allauth `clean_email()` + duplicate check
- ID and address updates: 90-day cooldown via `can_update()`
- OTP: length + cache-match validation before accepting

## CORS / CSRF
- CORS origins, allowed headers, and methods are restricted and env-configurable
- CSRF fully wired: middleware, `CSRF_TRUSTED_ORIGINS`, `JWT_AUTH_COOKIE_USE_CSRF`

## Security Headers (production only)
- HTTPS redirect, HSTS (1 year, subdomains, preload)
- `X-Content-Type-Options: nosniff`, `X-XSS-Protection`, `X-Frame-Options: DENY`
- Secure flags on session and CSRF cookies

## Audit Logging
- `django-auditlog` on: `CustomUser`, `UserID`, `UserAddress`, `Branch`, `BranchWorkingHours`, `Device`, `MainService`, `Service`
- Sensitive fields excluded: `password`, `last_login`
- `loguru` file logging: daily rotation, 7-day retention

## Secrets Management
- All credentials via environment variables: `SECRET_KEY`, DB, Redis, AWS, payment APIs
- Redis TLS supported via `rediss://` and `REDIS_USE_TLS` env var

## Celery Security
- Serialization locked to JSON — prevents pickle deserialization attacks

## File Storage
- S3: `AWS_DEFAULT_ACL = None`, no file overwrite, SigV4 signatures
- Static files via WhiteNoise

## Admin
- Custom admin at `/bknd-ctr/` with `django-unfold`
- Sensitive fields readonly; password changes only via `AdminPasswordChangeForm`

## Exception Handling
- All errors normalized to `{status_code, errorCode, errorMsg}` — no stack traces exposed
- 40+ typed domain exceptions to avoid information leakage

---

## Known Gaps

| # | Issue | Location | Risk |
|---|---|---|---|
| 1 | Device password stored and compared as plaintext | `configuration/models.py:103` | High |
| 2 | OTP uses `random` instead of `secrets` | `helpers/functions.py:6-11` | Medium |
| 3 | `JWT_AUTH_HTTPONLY: False` — JWT exposed to JS | `config/settings.py:315` | Medium |
| 4 | `DEBUG=True` as default env value | `config/settings.py:27` | Low-Medium |
