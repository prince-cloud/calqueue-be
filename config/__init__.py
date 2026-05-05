from .celery import app as celery_app
from .logging_config import configure_stdlib_logging, setup_loguru

# Configure loguru on app startup
setup_loguru()
configure_stdlib_logging()

__all__ = ("celery_app",)
