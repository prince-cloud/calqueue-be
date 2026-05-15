from celery import shared_task


@shared_task(bind=True, max_retries=2, default_retry_delay=10)
def announce_ticket_audio(self, ticket_uuid: str, counter_uuid: str, base_url: str = ""):
    """
    Generate TTS audio for a ticket then broadcast ticket.called to all TV screens
    for that branch. Dispatched in the background so the HTTP response is not delayed.
    """
    from .models import Ticket
    from .tts import generate_announcement_audio
    from .serializers import TicketSerializer
    from .views import _broadcast_queue
    from configuration.models import Counter

    try:
        ticket = Ticket.objects.select_related(
            "branch", "device", "counter", "servced_by"
        ).get(uuid=ticket_uuid)
        counter = Counter.objects.get(uuid=counter_uuid)
    except (Ticket.DoesNotExist, Counter.DoesNotExist):
        return

    # Generate only when audio is absent or the counter has changed
    if not ticket.ticket_audio or ticket.counter_id != counter.pk:
        try:
            generate_announcement_audio(ticket, counter)
            ticket.refresh_from_db()
        except Exception as exc:
            raise self.retry(exc=exc)

    data = dict(TicketSerializer(ticket).data)
    # Patch audio_url to an absolute URL — serializer has no request in Celery context
    if ticket.ticket_audio:
        relative = ticket.ticket_audio.url
        data["audio_url"] = f"{base_url.rstrip('/')}{relative}" if base_url else relative

    _broadcast_queue(str(ticket.branch.uuid), "ticket.called", data)
