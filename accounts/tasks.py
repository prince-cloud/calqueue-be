from celery import shared_task
from django.conf import settings
import requests
from loguru import logger
from jinja2 import Environment, FileSystemLoader
import os
from typing import Dict


@shared_task
def generic_send_mail(
    recipient, title, template_type="email_otp_verification", payload: Dict = None
):
    """
    Send generic email using specified template type.

    Args:
        recipient: Email address of the recipient
        title: Email subject
        template_type: Template type to use (email_otp_verification, password_reset_otp, password_changed)
        payload: Dictionary containing template variables
    """
    if payload is None:
        payload = {}

    env = Environment(
        loader=FileSystemLoader(
            os.path.join(os.path.dirname(__file__), "templates", "emails")
        )
    )

    # Map template types to template files
    template_map = {
        "email_otp_verification": "email_otp_verification.html",
        "password_reset_otp": "password_reset_otp.html",
        "password_changed": "password_changed.html",
    }

    template_file = template_map.get(template_type, "email_otp_verification.html")
    template = env.get_template(template_file)

    # Add current year to payload
    from datetime import datetime

    payload["current_year"] = datetime.now().year

    html_message = template.render(payload)
    try:
        base_url = settings.AWS_EMAIL_URL
        body = {
            "recipient": recipient,
            "subject": title,
            "body": html_message,
        }
        email_send = requests.post(
            base_url, json=body, headers={"Content-Type": "application/json"}
        )
        logger.info("Email sent successfully: {}", email_send.text)
        return "Mail Sent"
    except Exception as e:
        logger.warning(f"An error occurred sending email {str(e)}")


@shared_task
def generic_send_sms(to, body):
    url = f"https://api.mnotify.com/api/sms/quick?key={settings.MNOTIFY_API_KEY}"
    payload = {
        "recipient": [to],
        "sender": settings.MNOTIFY_SENDER_ID,
        "message": body,
        "is_schedule": "False",
        "schedule_date": "",
    }
    try:
        response = requests.post(url, json=payload)
        logger.info(f"mnotify Response: {response.text}")
        response.raise_for_status()
        logger.info("Message sent successfully via mnotify!")
        return response.json()
    except requests.RequestException as e:
        logger.error(f"An error occurred sending SMS via mnotify: {e}")
        return {"status": "error", "message": str(e)}
