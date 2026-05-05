import os
from celery import Celery
import logging

from celery.schedules import crontab


logger = logging.getLogger(__name__)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("aimy-ai")
app.config_from_object("django.conf:settings", namespace="CELERY")

app.conf.beat_schedule = {
    # "process_due_reminders": {
    #     "task": "app.tasks.process_due_reminders",
    #     "schedule": crontab(minute="*"),  # Run every minute
    # },
}


app.autodiscover_tasks()
