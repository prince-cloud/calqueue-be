import json
import time

from .context import clear_request, set_request

SENSITIVE_KEYS = {"password", "token", "access", "refresh", "secret", "pin", "otp", "authorization"}
SKIP_PREFIXES = ("/static/", "/bknd-ctr/", "/favicon.ico")


def _mask(data):
    if isinstance(data, dict):
        return {
            k: "***" if any(s in k.lower() for s in SENSITIVE_KEYS) else _mask(v)
            for k, v in data.items()
        }
    if isinstance(data, list):
        return [_mask(item) for item in data]
    return data


def _parse_request_body(request):
    content_type = request.content_type or ""
    try:
        if "application/json" in content_type:
            raw = request.body
            if raw:
                return _mask(json.loads(raw))
        elif "application/x-www-form-urlencoded" in content_type:
            return _mask(dict(request.POST.items()))
    except Exception:
        pass
    return None


def _get_client_ip(request):
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


class APILogMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if any(request.path.startswith(p) for p in SKIP_PREFIXES):
            return self.get_response(request)

        # Store the request in thread-local so signal handlers can read the actor
        set_request(request)
        request._log_body = _parse_request_body(request)
        request._log_start = time.monotonic()

        try:
            response = self.get_response(request)
        finally:
            clear_request()

        try:
            self._save(request, response)
        except Exception:
            pass

        return response

    def _save(self, request, response):
        from django.contrib.auth import get_user_model

        from .models import APILog

        User = get_user_model()

        user = None
        req_user = getattr(request, "user", None)
        if req_user and not req_user.is_anonymous and isinstance(req_user, User):
            user = req_user

        response_body = None
        if "application/json" in response.get("Content-Type", ""):
            try:
                response_body = json.loads(response.content)
            except Exception:
                pass

        error_message = ""
        if isinstance(response_body, dict):
            error_message = str(
                response_body.get("errorMsg", "") or response_body.get("detail", "")
            )

        duration_ms = int((time.monotonic() - request._log_start) * 1000)

        APILog.objects.create(
            method=request.method,
            path=request.path,
            query_params=dict(request.GET),
            request_body=getattr(request, "_log_body", None),
            response_body=response_body,
            status_code=response.status_code,
            user=user,
            ip_address=_get_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", "")[:500],
            error_message=error_message[:1000],
            duration_ms=duration_ms,
        )
