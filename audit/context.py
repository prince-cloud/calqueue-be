import threading

_local = threading.local()


def set_request(request):
    _local.request = request


def get_actor():
    request = getattr(_local, "request", None)
    if request is None:
        return None
    user = getattr(request, "user", None)
    if user is None or user.is_anonymous:
        return None
    try:
        from django.contrib.auth import get_user_model
        if isinstance(user, get_user_model()):
            return user
    except Exception:
        pass
    return None


def clear_request():
    if hasattr(_local, "request"):
        del _local.request
