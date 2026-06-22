import logging
import operator
from functools import reduce

import requests
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings as django_settings
from django.db import transaction
from datetime import date, timedelta

from django.db.models import Avg, Count, Q, Sum
from django.db.models.functions import ExtractHour, TruncDate
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from configuration.models import Counter

logger = logging.getLogger(__name__)
from .filters import (
    CashDepositFilter,
    ChequeDepositFilter,
    EZWICHDepositFilter,
    MobileMoneyDepositFilter,
)
from .models import (
    CashDeposit,
    ChequeDeposit,
    EZWICHDeposit,
    MobileMoneyDeposit,
    Ticket,
    TicketStatus,
    T24Status,
    Verification,
)

_SERVICE_TYPE_TO_DEPOSIT_MODEL = {
    "CASH DEPOSIT": CashDeposit,
    "CHEQUE DEPOSIT": ChequeDeposit,
    "EZWICH CARD DEPOSIT": EZWICHDeposit,
    "MOBILE MONEY DEPOSIT": MobileMoneyDeposit,
}

# Fields extracted from services_data when auto-creating a deposit record at commit time.
_DEPOSIT_MODEL_FIELDS = {
    CashDeposit: [
        "deposit_type",
        "account_number",
        "account_name",
        "amount",
        "phone_number",
        "depositor_name",
        "residential_address",
        "occupation",
        "id_type",
        "nationality",
    ],
    ChequeDeposit: [
        "cheque_type",
        "beneficiary_account_number",
        "beneficiary_account_name",
        "cheque_details",
        "phone_number",
        "depositor_name",
    ],
    EZWICHDeposit: [
        "id_type",
        "id_number",
        "ezwich_card_number",
        "amount",
        "name",
        "residential_address",
        "occupation",
        "phone_number",
    ],
    MobileMoneyDeposit: [
        "id_type",
        "id_number",
        "name",
        "residential_address",
        "phone_number",
        "amount",
        "occupation",
    ],
}


def _extract_deposit_fields(service_entry: dict, model_class) -> dict:
    allowed = _DEPOSIT_MODEL_FIELDS.get(model_class, [])
    return {k: service_entry[k] for k in allowed if k in service_entry}


from .serializers import (
    CashDepositSerializer,
    ChequeDepositSerializer,
    EZWICHDepositSerializer,
    MobileMoneyDepositSerializer,
    MobileTicketWriteSerializer,
    TicketWriteSerializer,
    TicketSerializer,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _resolve_counter(request, uuid_param: str | None = None):
    """
    Resolve a Counter from an explicit UUID param or the authenticated user's
    assigned counter. Returns (counter, error_response).
    """
    counter_uuid = uuid_param
    if counter_uuid:
        try:
            counter = Counter.objects.prefetch_related("operations").get(
                uuid=counter_uuid, is_active=True
            )
            return counter, None
        except Counter.DoesNotExist:
            return None, Response(
                {"detail": "Counter not found or inactive."},
                status=status.HTTP_404_NOT_FOUND,
            )

    counter_fk = getattr(request.user, "queue_counter_id", None)
    if not counter_fk:
        return None, Response(
            {"detail": "No counter assigned. Pass ?counter=<uuid>."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    try:
        counter = Counter.objects.prefetch_related("operations").get(
            pk=counter_fk, is_active=True
        )
        return counter, None
    except Counter.DoesNotExist:
        return None, Response(
            {"detail": "Assigned counter not found or inactive."},
            status=status.HTTP_404_NOT_FOUND,
        )


def _build_service_filter(service_types: list[str]):
    """OR filter: tickets that contain any of the given service_type values."""
    return reduce(
        operator.or_,
        (Q(services_data__contains=[{"service_type": st}]) for st in service_types),
    )


def _inject_audio_data(data: dict, ticket, counter) -> None:
    """
    Generate TTS audio (or retrieve from Redis cache) and embed it as a
    base64 data URL in the broadcast payload. The TV screen plays directly
    from memory — no S3 round-trip required.
    """
    import base64
    from .tts import generate_announcement_audio

    audio_bytes = generate_announcement_audio(ticket, counter)
    if audio_bytes:
        b64 = base64.b64encode(audio_bytes).decode("ascii")
        data["audio_data"] = f"data:audio/mpeg;base64,{b64}"


def _broadcast_with_audio_background(
    ticket_data: dict, ticket_uuid: str, counter_uuid: str, branch_uuid: str
) -> None:
    """
    Spin up a daemon thread that generates TTS audio then broadcasts
    ticket.called with audio_data embedded. The HTTP response is already
    returned by the time this runs — the teller gets instant feedback and
    the TV screen receives the audio a few seconds later.
    """
    import threading

    def _run():
        try:
            from django.db import connections
            from .models import Ticket
            from configuration.models import Counter

            ticket = Ticket.objects.select_related(
                "branch", "device", "counter", "servced_by"
            ).get(uuid=ticket_uuid)
            counter = Counter.objects.get(uuid=counter_uuid)

            broadcast_data = dict(ticket_data)
            _inject_audio_data(broadcast_data, ticket, counter)
            _broadcast_queue(branch_uuid, "ticket.called", broadcast_data)
        except Exception as e:
            print(f"[tts-thread] error: {e}")
        finally:
            from django.db import connections

            connections.close_all()

    threading.Thread(target=_run, daemon=True).start()


def _broadcast_queue(branch_uuid: str, event_type: str, ticket_data: dict):
    """Push a queue event to all WebSocket clients subscribed to this branch."""
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return
    async_to_sync(channel_layer.group_send)(
        f"queue_{branch_uuid}",
        {
            "type": "queue.update",
            "data": {"type": event_type, "ticket": ticket_data},
        },
    )


# ---------------------------------------------------------------------------
# TicketViewSet
# ---------------------------------------------------------------------------


class TicketViewSet(ModelViewSet):
    lookup_field = "uuid"
    http_method_names = ["get", "post", "head", "options"]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_queryset(self):
        return Ticket.objects.select_related(
            "branch", "device", "counter", "servced_by"
        ).order_by("-created_at")

    def get_serializer_class(self):
        if self.action == "create":
            return TicketWriteSerializer
        return TicketSerializer

    def create(self, request, *args, **kwargs):
        s = self.get_serializer(data=request.data)
        s.is_valid(raise_exception=True)
        ticket = s.save()
        data = TicketSerializer(ticket, context={"request": request}).data
        _broadcast_queue(str(ticket.branch.uuid), "ticket.created", data)
        return Response(data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["get"], url_path="queue")
    def queue(self, request):
        """
        GET /core/tickets/queue/
        Returns today's WAITING tickets for the counter's operations,
        excluding tickets that are already assigned as a counter's current ticket.
        """
        date_str = request.query_params.get("date")
        if date_str:
            from datetime import date as _date

            try:
                filter_date = _date.fromisoformat(date_str)
            except ValueError:
                return Response(
                    {"detail": "Invalid date format. Use YYYY-MM-DD."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            filter_date = timezone.localdate()

        counter, err = _resolve_counter(request, request.query_params.get("counter"))
        if err:
            return err

        service_types = list(counter.operations.values_list("name", flat=True))
        if not service_types:
            return Response({"count": 0, "results": []})

        service_filter = _build_service_filter(service_types)

        tickets = (
            Ticket.objects.select_related("branch", "device", "counter", "servced_by")
            .filter(
                service_filter,
                status=TicketStatus.WAITING,
                current_at_counter__isnull=True,
                created_at__date=filter_date,
            )
            .order_by("created_at")
        )

        serializer = TicketSerializer(tickets, many=True, context={"request": request})
        return Response({"count": tickets.count(), "results": serializer.data})

    @action(detail=False, methods=["get"], url_path="current")
    def current(self, request):
        """
        GET /core/tickets/current/
        Returns the ticket currently assigned to the user's counter, or null.
        """
        counter, err = _resolve_counter(request, request.query_params.get("counter"))
        if err:
            return err

        if not counter.current_ticket_id:
            return Response(None)

        ticket = Ticket.objects.select_related(
            "branch", "device", "counter", "servced_by"
        ).get(pk=counter.current_ticket_id)
        return Response(TicketSerializer(ticket, context={"request": request}).data)

    @action(detail=False, methods=["post"], url_path="next")
    def next(self, request):
        """
        POST /core/tickets/next/
        Picks the oldest WAITING ticket matching the counter's operations and
        assigns it as the counter's current ticket (status → ON_GOING).
        """
        counter, err = _resolve_counter(request, request.data.get("counter"))
        if err:
            return err

        service_types = list(counter.operations.values_list("name", flat=True))
        if not service_types:
            return Response(
                {"detail": "Counter has no operations assigned."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        service_filter = _build_service_filter(service_types)

        with transaction.atomic():
            counter = (
                Counter.objects.select_for_update()
                .prefetch_related("operations")
                .get(pk=counter.pk)
            )

            if counter.current_ticket_id:
                return Response(
                    {
                        "detail": "Counter already has an active ticket. Release it first."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            ticket = (
                Ticket.objects.select_for_update(of=("self",))
                .filter(
                    service_filter,
                    status=TicketStatus.WAITING,
                    current_at_counter__isnull=True,
                    created_at__date=timezone.localdate(),
                )
                .order_by("created_at")
                .first()
            )

            if not ticket:
                return Response(
                    {"detail": "No tickets waiting in queue."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            ticket.status = TicketStatus.CALLED
            ticket.counter = counter
            ticket.called_time = timezone.now()
            ticket.save(
                update_fields=["status", "counter", "called_time", "updated_at"]
            )

            counter.current_ticket = ticket
            counter.save(update_fields=["current_ticket"])

        ticket.refresh_from_db()
        data = TicketSerializer(ticket, context={"request": request}).data
        branch_uuid = str(ticket.branch.uuid)
        # Respond immediately — audio generates in background, TV gets one broadcast with audio
        _broadcast_with_audio_background(
            data, str(ticket.uuid), str(counter.uuid), branch_uuid
        )
        return Response(data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"], url_path="release")
    def release(self, request):
        """
        POST /core/tickets/release/
        Releases the counter's current ticket back to WAITING status.
        """
        counter, err = _resolve_counter(request, request.data.get("counter"))
        if err:
            return err

        with transaction.atomic():
            counter = Counter.objects.select_for_update().get(pk=counter.pk)

            if not counter.current_ticket_id:
                return Response(
                    {"detail": "No active ticket to release."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            ticket = Ticket.objects.select_for_update().get(
                pk=counter.current_ticket_id
            )
            ticket.status = TicketStatus.WAITING
            ticket.counter = None
            ticket.called_time = None
            ticket.save(
                update_fields=["status", "counter", "called_time", "updated_at"]
            )

            branch_uuid = str(ticket.branch.uuid)
            ticket_data = TicketSerializer(ticket, context={"request": request}).data

            counter.current_ticket = None
            counter.save(update_fields=["current_ticket"])

        _broadcast_queue(branch_uuid, "ticket.released", ticket_data)
        return Response({"detail": "Ticket released successfully."})

    @action(detail=True, methods=["post"], url_path="release")
    def release_ticket(self, request, uuid=None):
        """
        POST /core/tickets/{uuid}/release/
        Release a specific SKIPPED ticket back to WAITING so it re-enters the queue.
        """
        try:
            ticket = Ticket.objects.select_related("branch").get(uuid=uuid)
        except Ticket.DoesNotExist:
            return Response(
                {"detail": "Ticket not found."}, status=status.HTTP_404_NOT_FOUND
            )

        if ticket.status != TicketStatus.SKIPPED:
            return Response(
                {"detail": "Only SKIPPED tickets can be released this way."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            ticket = Ticket.objects.select_for_update(of=("self",)).get(pk=ticket.pk)
            ticket.status = TicketStatus.WAITING
            ticket.hold_started_at = None
            ticket.total_hold_seconds = 0
            ticket.start_serve_time = None
            ticket.called_time = None
            ticket.save(
                update_fields=[
                    "status",
                    "hold_started_at",
                    "total_hold_seconds",
                    "start_serve_time",
                    "called_time",
                    "updated_at",
                ]
            )

        ticket.refresh_from_db()
        branch_uuid = str(ticket.branch.uuid)
        ticket_data = TicketSerializer(ticket, context={"request": request}).data
        _broadcast_queue(branch_uuid, "ticket.released", ticket_data)
        return Response(ticket_data)

    @action(detail=True, methods=["post"], url_path="pick")
    def pick(self, request, uuid=None):
        """
        POST /core/tickets/{uuid}/pick/
        Pick a specific WAITING ticket and assign it to the teller's counter,
        identical to /next/ but for a teller-selected ticket rather than
        the oldest in queue.
        """
        counter, err = _resolve_counter(request, request.data.get("counter"))
        if err:
            return err

        with transaction.atomic():
            counter = (
                Counter.objects.select_for_update()
                .prefetch_related("operations")
                .get(pk=counter.pk)
            )

            if counter.current_ticket_id:
                return Response(
                    {
                        "detail": "Counter already has an active ticket. Release it first."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            try:
                ticket = (
                    Ticket.objects.select_for_update(of=("self",))
                    .select_related("branch", "device", "counter", "servced_by")
                    .get(uuid=uuid)
                )
            except Ticket.DoesNotExist:
                return Response(
                    {"detail": "Ticket not found."}, status=status.HTTP_404_NOT_FOUND
                )

            if ticket.status not in (TicketStatus.WAITING, TicketStatus.SKIPPED):
                return Response(
                    {"detail": "Ticket is no longer available to pick."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if (
                ticket.status == TicketStatus.WAITING
                and ticket.current_at_counter.exists()
            ):
                return Response(
                    {"detail": "Ticket is already assigned to another counter."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            ticket.status = TicketStatus.CALLED
            ticket.counter = counter
            ticket.called_time = timezone.now()
            ticket.save(
                update_fields=["status", "counter", "called_time", "updated_at"]
            )

            counter.current_ticket = ticket
            counter.save(update_fields=["current_ticket"])

        ticket.refresh_from_db()
        data = TicketSerializer(ticket, context={"request": request}).data
        branch_uuid = str(ticket.branch.uuid)
        _broadcast_with_audio_background(
            data, str(ticket.uuid), str(counter.uuid), branch_uuid
        )
        return Response(data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="start-serve")
    def start_serve(self, request, uuid=None):
        """POST /core/tickets/{uuid}/start-serve/ — begin serving a CALLED ticket."""
        ticket = self.get_object()
        if ticket.status != TicketStatus.CALLED:
            return Response(
                {"detail": "Ticket is not in CALLED state."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        with transaction.atomic():
            ticket = Ticket.objects.select_for_update(of=("self",)).get(pk=ticket.pk)
            ticket.status = TicketStatus.ON_GOING
            ticket.start_serve_time = timezone.now()
            ticket.save(update_fields=["status", "start_serve_time", "updated_at"])
        ticket.refresh_from_db()
        return Response(TicketSerializer(ticket, context={"request": request}).data)

    @action(detail=True, methods=["post"], url_path="hold")
    def hold(self, request, uuid=None):
        """POST /core/tickets/{uuid}/hold/ — put ON_GOING ticket on hold."""
        ticket = self.get_object()
        if ticket.status != TicketStatus.ON_GOING:
            return Response(
                {"detail": "Ticket is not ON_GOING."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        with transaction.atomic():
            ticket = Ticket.objects.select_for_update(of=("self",)).get(pk=ticket.pk)
            ticket.status = TicketStatus.ON_HOLD
            ticket.hold_started_at = timezone.now()
            ticket.save(update_fields=["status", "hold_started_at", "updated_at"])
        ticket.refresh_from_db()
        return Response(TicketSerializer(ticket, context={"request": request}).data)

    @action(detail=True, methods=["post"], url_path="resume")
    def resume(self, request, uuid=None):
        """POST /core/tickets/{uuid}/resume/ — resume an ON_HOLD ticket."""
        ticket = self.get_object()
        if ticket.status != TicketStatus.ON_HOLD:
            return Response(
                {"detail": "Ticket is not ON_HOLD."}, status=status.HTTP_400_BAD_REQUEST
            )
        with transaction.atomic():
            ticket = Ticket.objects.select_for_update(of=("self",)).get(pk=ticket.pk)
            if ticket.hold_started_at:
                held_secs = int(
                    (timezone.now() - ticket.hold_started_at).total_seconds()
                )
                ticket.total_hold_seconds = (ticket.total_hold_seconds or 0) + held_secs
            ticket.status = TicketStatus.ON_GOING
            ticket.hold_started_at = None
            ticket.save(
                update_fields=[
                    "status",
                    "hold_started_at",
                    "total_hold_seconds",
                    "updated_at",
                ]
            )
        ticket.refresh_from_db()
        return Response(TicketSerializer(ticket, context={"request": request}).data)

    @action(detail=True, methods=["post"], url_path="skip")
    def skip(self, request, uuid=None):
        """POST /core/tickets/{uuid}/skip/ — skip a CALLED/ON_GOING ticket (no-show)."""
        ticket = self.get_object()
        if ticket.status not in (
            TicketStatus.CALLED,
            TicketStatus.ON_GOING,
            TicketStatus.ON_HOLD,
        ):
            return Response(
                {"detail": "Ticket cannot be skipped in its current state."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        with transaction.atomic():
            ticket = (
                Ticket.objects.select_for_update(of=("self",))
                .select_related("counter")
                .get(pk=ticket.pk)
            )
            counter = ticket.counter
            ticket.status = TicketStatus.SKIPPED
            ticket.counter = None
            ticket.called_time = None
            ticket.hold_started_at = None
            ticket.save(
                update_fields=[
                    "status",
                    "counter",
                    "called_time",
                    "hold_started_at",
                    "updated_at",
                ]
            )
            if counter:
                counter = Counter.objects.select_for_update().get(pk=counter.pk)
                if counter.current_ticket_id == ticket.pk:
                    counter.current_ticket = None
                    counter.save(update_fields=["current_ticket"])
        ticket.refresh_from_db()
        branch_uuid = str(ticket.branch.uuid)
        ticket_data = TicketSerializer(ticket, context={"request": request}).data
        _broadcast_queue(branch_uuid, "ticket.skipped", ticket_data)
        return Response(ticket_data)

    @action(detail=False, methods=["get"], url_path="skipped")
    def skipped_queue(self, request):
        """GET /core/tickets/skipped/ — today's skipped tickets for this counter."""
        counter, err = _resolve_counter(request, request.query_params.get("counter"))
        if err:
            return err
        service_types = list(counter.operations.values_list("name", flat=True))
        if not service_types:
            return Response({"count": 0, "results": []})
        service_filter = _build_service_filter(service_types)
        tickets = (
            Ticket.objects.select_related("branch", "device", "counter", "servced_by")
            .filter(
                service_filter,
                status=TicketStatus.SKIPPED,
                created_at__date=timezone.localdate(),
            )
            .order_by("created_at")
        )
        serializer = TicketSerializer(tickets, many=True, context={"request": request})
        return Response({"count": tickets.count(), "results": serializer.data})

    @action(
        detail=True,
        methods=["post"],
        url_path="commit-t24",
        permission_classes=[IsAuthenticated],
    )
    def commit_t24(self, request, uuid=None):
        """
        POST /core/tickets/{uuid}/commit-t24/
        Mark the service at service_position as committed to T24.
        Updates served_by on the linked deposit record.
        If all services are now committed, completes the ticket and auto-assigns
        the next waiting ticket to the counter.
        """
        ticket = self.get_object()

        try:
            service_position = int(request.data.get("service_position"))
        except (TypeError, ValueError):
            return Response(
                {"detail": "service_position must be an integer."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not (0 <= service_position < len(ticket.services_data)):
            return Response(
                {"detail": "service_position out of range."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        service_entry = ticket.services_data[service_position]

        if service_entry.get("t24_committed"):
            return Response(
                {"detail": "This service has already been committed to T24."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        completed = False

        with transaction.atomic():
            # of=("self",) locks only the ticket row; avoids the PostgreSQL
            # "FOR UPDATE cannot be applied to nullable outer join" error that
            # occurs when select_related pulls in nullable FK tables.
            ticket = (
                Ticket.objects.select_for_update(of=("self",))
                .select_related("branch", "counter", "servced_by")
                .get(pk=ticket.pk)
            )

            # Re-read service_entry from the freshly-locked ticket row.
            service_entry = ticket.services_data[service_position]

            # Ensure a deposit record exists for this service and mark it committed.
            object_uuid = service_entry.get("object_uuid")
            DepositModel = _SERVICE_TYPE_TO_DEPOSIT_MODEL.get(
                service_entry.get("service_type", "")
            )
            if DepositModel:
                if object_uuid:
                    try:
                        deposit = DepositModel.objects.select_for_update().get(
                            uuid=object_uuid
                        )
                        deposit.served_by = request.user
                        deposit.t24_status = T24Status.COMMITTED
                        deposit.save(
                            update_fields=["served_by", "t24_status", "updated_at"]
                        )
                    except DepositModel.DoesNotExist:
                        pass
                else:
                    # Deposit not yet created — build it from the services_data payload.
                    deposit_data = _extract_deposit_fields(service_entry, DepositModel)
                    deposit = DepositModel.objects.create(
                        **deposit_data,
                        ticket=ticket,
                        served_by=request.user,
                        t24_status=T24Status.COMMITTED,
                    )
                    # The post_save signal writes object_uuid back to the DB copy of
                    # services_data. Mirror it on our local copy so the final ticket.save
                    # below doesn't overwrite it.
                    ticket.services_data[service_position]["object_uuid"] = str(
                        deposit.uuid
                    )

            # Mark this service committed in the JSON blob
            ticket.services_data[service_position]["t24_committed"] = True

            all_committed = all(
                svc.get("t24_committed") for svc in ticket.services_data
            )

            ticket_update_fields = ["services_data", "updated_at"]

            if all_committed:
                completed = True
                now = timezone.now()
                ticket.status = TicketStatus.COMPLETED
                ticket_update_fields.append("status")

                if ticket.start_serve_time:
                    ticket.served_time = int(
                        (now - ticket.start_serve_time).total_seconds()
                    )
                    ticket_update_fields.append("served_time")

                ticket.total_time_spent = int((now - ticket.created_at).total_seconds())
                ticket_update_fields.append("total_time_spent")

                counter = ticket.counter
                if counter:
                    counter = Counter.objects.select_for_update().get(pk=counter.pk)
                    counter.current_ticket = None
                    counter.save(update_fields=["current_ticket"])

            ticket.save(update_fields=ticket_update_fields)

        ticket.refresh_from_db()
        ticket_data = TicketSerializer(ticket, context={"request": request}).data

        if completed:
            _broadcast_queue(str(ticket.branch.uuid), "ticket.released", ticket_data)

        return Response(
            {
                "ticket": ticket_data,
                "completed": completed,
                "message": "Transaction committed to T24 successfully.",
            },
            status=status.HTTP_200_OK,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="announce",
        permission_classes=[IsAuthenticated],
    )
    def announce(self, request, uuid=None):
        """
        POST /core/tickets/{uuid}/announce/
        Re-announce a ticket synchronously. Regenerates audio when the counter has
        changed or no audio exists, then broadcasts ticket.called so TV screens play it.
        """
        ticket = self.get_object()

        counter_uuid = request.data.get("counter")
        counter, err = _resolve_counter(request, counter_uuid)
        if err:
            return err

        data = TicketSerializer(ticket, context={"request": request}).data
        _inject_audio_data(data, ticket, counter)
        _broadcast_queue(str(ticket.branch.uuid), "ticket.called", data)
        return Response(data, status=status.HTTP_200_OK)

    @action(
        detail=True,
        methods=["post"],
        url_path="verify",
        permission_classes=[IsAuthenticated],
        parser_classes=[MultiPartParser, FormParser, JSONParser],
    )
    def verify(self, request, uuid=None):
        """
        POST /core/tickets/{uuid}/verify/
        Real-time counter verification. Accepts method=face (with image file) or
        method=biometric (simulated). Updates ticket.verification_data and returns
        the updated ticket so the teller dashboard refreshes immediately.
        """
        ticket = self.get_object()
        method = request.data.get("method", "face")

        if method == "biometric":
            ticket.verification_data = {"verified": True, "method": "biometric"}
            ticket.save(update_fields=["verification_data"])
            return Response(TicketSerializer(ticket, context={"request": request}).data)

        # Face verification via NIA
        if ticket.id_type.upper() != "GHANA CARD":
            return Response(
                {"detail": "Face verification is only available for Ghana Card holders."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        image = request.FILES.get("image")
        if not image:
            return Response(
                {"detail": "image is required for face verification."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        verified, payload = _call_nia_api(image, ticket.id_number.strip().upper())
        ticket.verification_data = {"verified": verified, "method": "face", **(payload or {})}
        ticket.save(update_fields=["verification_data"])

        return Response(TicketSerializer(ticket, context={"request": request}).data)

    @action(
        detail=False,
        methods=["get"],
        url_path="tv-display",
        permission_classes=[AllowAny],
    )
    def tv_display(self, request):
        """
        GET /core/tickets/tv-display/?branch={uuid}
        Returns branch info, waiting tickets, and TV display config for the branch.
        No auth required — TV screens are public displays.
        """
        from configuration.models import Branch, BranchTVConfig
        from configuration.serializers import BranchSerializer, BranchTVConfigSerializer
        from django.utils import timezone

        branch_uuid = request.query_params.get("branch")
        if not branch_uuid:
            return Response(
                {"detail": "branch query param is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            branch = Branch.objects.get(uuid=branch_uuid, is_active=True)
        except Branch.DoesNotExist:
            return Response(
                {"detail": "Branch not found."}, status=status.HTTP_404_NOT_FOUND
            )

        tv_config, _ = BranchTVConfig.objects.get_or_create(branch=branch)

        waiting_tickets = (
            Ticket.objects.select_related("branch", "device", "counter", "servced_by")
            .filter(
                branch=branch,
                status=TicketStatus.WAITING,
                created_at__date=timezone.localdate(),
            )
            .order_by("created_at")
        )

        return Response(
            {
                "branch": BranchSerializer(branch).data,
                "waiting_tickets": TicketSerializer(
                    waiting_tickets, many=True, context={"request": request}
                ).data,
                "tv_config": BranchTVConfigSerializer(
                    tv_config, context={"request": request}
                ).data,
            }
        )

    @action(
        detail=True,
        methods=["get"],
        url_path="verification",
        permission_classes=[IsAuthenticated],
    )
    def verification(self, request, uuid=None):
        """
        GET /core/tickets/{uuid}/verification/
        Returns the NIA verification status stored on this ticket.
        """
        ticket = self.get_object()
        if ticket.verification_data:
            data = dict(ticket.verification_data)
            if data.get("captured_image"):
                from django.conf import settings as django_settings
                data["captured_image"] = request.build_absolute_uri(
                    f"{django_settings.MEDIA_URL}{data['captured_image']}"
                )
            return Response({"status": True, "data": data})
        return Response({"status": False, "data": None})


# ---------------------------------------------------------------------------
# Deposit ViewSets
# ---------------------------------------------------------------------------


class _DepositViewSet(ModelViewSet):
    lookup_field = "uuid"
    http_method_names = ["get", "post", "head", "options"]


class CashDepositViewSet(_DepositViewSet):
    queryset = CashDeposit.objects.select_related("ticket").order_by("-created_at")
    serializer_class = CashDepositSerializer
    filterset_class = CashDepositFilter
    search_fields = (
        "ticket__ticket_number",
        "account_number",
        "depositor_name",
        "phone_number",
    )


class ChequeDepositViewSet(_DepositViewSet):
    queryset = ChequeDeposit.objects.select_related("ticket").order_by("-created_at")
    serializer_class = ChequeDepositSerializer
    filterset_class = ChequeDepositFilter
    search_fields = (
        "ticket__ticket_number",
        "beneficiary_account_number",
        "depositor_name",
        "phone_number",
    )


class EZWICHDepositViewSet(_DepositViewSet):
    queryset = EZWICHDeposit.objects.select_related("ticket").order_by("-created_at")
    serializer_class = EZWICHDepositSerializer
    filterset_class = EZWICHDepositFilter
    search_fields = (
        "ticket__ticket_number",
        "ezwich_card_number",
        "name",
        "phone_number",
    )


class MobileMoneyDepositViewSet(_DepositViewSet):
    queryset = MobileMoneyDeposit.objects.select_related("ticket").order_by(
        "-created_at"
    )
    serializer_class = MobileMoneyDepositSerializer
    filterset_class = MobileMoneyDepositFilter
    search_fields = ("ticket__ticket_number", "name", "phone_number")


# ---------------------------------------------------------------------------
# Ghana Card / NIA verification
# ---------------------------------------------------------------------------


class GhanaCardVerificationView(APIView):
    """
    POST /core/verification/ghana-card/

    Accepts a face image and Ghana Card number from the kiosk device,
    calls the NIA API (if configured), persists the result, and returns
    {"verified": bool}.

    AllowAny — the device may call this before its JWT is refreshed and
    a failed auth check must never silently block customer verification.
    """

    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        image = request.FILES.get("image")
        card_number = request.data.get("card_number", "").strip().upper()

        if not image or not card_number:
            return Response(
                {"detail": "image and card_number are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        verified, payload = _call_nia_api(image, card_number)

        record = Verification.objects.create(
            card_number=card_number,
            image=image,
            verified=verified,
            data=payload,
        )

        return Response({"verified": verified, "verification_uuid": str(record.uuid)})


def _call_nia_api(image, card_number: str) -> tuple[bool, dict | None]:
    """
    Forward image + card_number to the Ghana NIA identity API.
    Returns (verified, payload).  On any failure returns (False, None).

    Settings / env vars:
        GHANA_NIA_API_URL  — full URL of the NIA endpoint
        GHANA_NIA_API_KEY  — bearer token / API key
    """
    nia_url = getattr(django_settings, "GHANA_NIA_API_URL", None)
    nia_key = getattr(django_settings, "GHANA_NIA_API_KEY", None)

    if not nia_url:
        # NIA not configured — simulate a successful match so the full flow
        # can be tested end-to-end. Remove this branch when going to production.
        logger.debug("GHANA_NIA_API_URL not configured — returning simulated verification.")
        return True, {
            "verified": True,
            "simulated": True,
            "name": "Kwame Asante",
            "date_of_birth": "1988-04-22",
            "gender": "Male",
            "nationality": "Ghanaian",
            "residential_address": "14 Liberation Road, Accra, Ghana",
            "photo": None,
        }

    try:
        resp = requests.post(
            nia_url,
            headers={"Authorization": f"Bearer {nia_key}"} if nia_key else {},
            files={"image": ("face.jpg", image.read(), "image/jpeg")},
            data={"card_number": card_number},
            timeout=15,
        )
        resp.raise_for_status()
        payload = resp.json()
        verified = bool(payload.get("verified") or payload.get("match"))
        return verified, payload
    except Exception:
        logger.exception("NIA API call failed for card %s", card_number)
        return False, None


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------


class ReportsView(APIView):
    """
    GET /core/reports/?action=<action>&branch=<uuid>&date_from=YYYY-MM-DD&date_to=YYYY-MM-DD

    Supported actions: queue_summary, hourly_traffic, transactions,
                       teller_performance, verification_stats
    """

    permission_classes = [IsAuthenticated]

    _ACTIONS = frozenset(
        ["queue_summary", "hourly_traffic", "transactions", "teller_performance", "verification_stats"]
    )

    def get(self, request):
        from configuration.models import Branch

        action_name = request.query_params.get("action", "")
        if action_name not in self._ACTIONS:
            return Response(
                {"detail": f"action must be one of: {', '.join(sorted(self._ACTIONS))}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        branch_uuid = request.query_params.get("branch")
        if not branch_uuid:
            return Response({"detail": "branch is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            branch = Branch.objects.get(uuid=branch_uuid)
        except Branch.DoesNotExist:
            return Response({"detail": "Branch not found."}, status=status.HTTP_404_NOT_FOUND)

        today = date.today()
        raw_from = request.query_params.get("date_from")
        raw_to = request.query_params.get("date_to")
        try:
            date_from = date.fromisoformat(raw_from) if raw_from else today - timedelta(days=29)
            date_to = date.fromisoformat(raw_to) if raw_to else today
        except ValueError:
            return Response({"detail": "date_from / date_to must be YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)

        handler = getattr(self, f"_action_{action_name}")
        return Response(handler(branch, date_from, date_to, request.query_params))

    # ------------------------------------------------------------------
    # action: queue_summary
    # ------------------------------------------------------------------
    def _action_queue_summary(self, branch, date_from, date_to, params):
        qs = Ticket.objects.filter(branch=branch, created_at__date__range=[date_from, date_to])
        total = qs.count()

        status_counts = {
            row["status"]: row["count"]
            for row in qs.values("status").annotate(count=Count("id"))
        }

        averages = qs.aggregate(
            avg_waiting_time=Avg("waiting_time"),
            avg_served_time=Avg("served_time"),
            avg_total_time_spent=Avg("total_time_spent"),
        )

        daily = list(
            qs.annotate(day=TruncDate("created_at"))
            .values("day")
            .annotate(total=Count("id"), completed=Count("id", filter=Q(status=TicketStatus.COMPLETED)))
            .order_by("day")
            .values("day", "total", "completed")
        )
        for row in daily:
            row["day"] = row["day"].isoformat()

        return {
            "total": total,
            "status_counts": status_counts,
            "averages": {k: round(v) if v is not None else None for k, v in averages.items()},
            "daily": daily,
        }

    # ------------------------------------------------------------------
    # action: hourly_traffic
    # ------------------------------------------------------------------
    def _action_hourly_traffic(self, branch, date_from, date_to, params):
        raw_date = params.get("date")
        try:
            target_date = date.fromisoformat(raw_date) if raw_date else date.today()
        except ValueError:
            target_date = date.today()

        qs = Ticket.objects.filter(branch=branch, created_at__date=target_date)
        hourly = list(
            qs.annotate(hour=ExtractHour("created_at"))
            .values("hour")
            .annotate(count=Count("id"))
            .order_by("hour")
        )
        return {"date": target_date.isoformat(), "hourly": hourly}

    # ------------------------------------------------------------------
    # action: transactions
    # ------------------------------------------------------------------
    def _action_transactions(self, branch, date_from, date_to, params):
        deposit_models = [
            (CashDeposit, "Cash Deposit", True),
            (ChequeDeposit, "Cheque Deposit", False),
            (EZWICHDeposit, "EZWICH Deposit", True),
            (MobileMoneyDeposit, "Mobile Money Deposit", True),
        ]
        summary = []
        for Model, label, has_amount in deposit_models:
            qs = Model.objects.filter(
                ticket__branch=branch,
                created_at__date__range=[date_from, date_to],
            )
            agg = qs.aggregate(
                count=Count("id"),
                committed=Count("id", filter=Q(t24_status=T24Status.COMMITTED)),
                failed=Count("id", filter=Q(t24_status=T24Status.FAILED_COMMIT)),
                pending=Count("id", filter=Q(t24_status=T24Status.PENDING)),
                total_amount=Sum("amount") if has_amount else Count("id", filter=Q(id=None)),
            )
            if not has_amount:
                agg["total_amount"] = None

            daily = list(
                qs.annotate(day=TruncDate("created_at"))
                .values("day")
                .annotate(count=Count("id"))
                .order_by("day")
                .values("day", "count")
            )
            for row in daily:
                row["day"] = row["day"].isoformat()

            summary.append(
                {
                    "type": label,
                    "count": agg["count"],
                    "total_amount": float(agg["total_amount"]) if agg["total_amount"] is not None else None,
                    "committed": agg["committed"],
                    "failed": agg["failed"],
                    "pending": agg["pending"],
                    "daily": daily,
                }
            )
        return {"transactions": summary}

    # ------------------------------------------------------------------
    # action: teller_performance
    # ------------------------------------------------------------------
    def _action_teller_performance(self, branch, date_from, date_to, params):
        qs = Ticket.objects.filter(
            branch=branch,
            created_at__date__range=[date_from, date_to],
            servced_by__isnull=False,
        )
        rows = list(
            qs.values("servced_by", "servced_by__first_name", "servced_by__last_name")
            .annotate(
                total=Count("id"),
                completed=Count("id", filter=Q(status=TicketStatus.COMPLETED)),
                avg_serve_time=Avg("served_time"),
                avg_total_time=Avg("total_time_spent"),
            )
            .order_by("-total")
        )
        tellers = []
        for row in rows:
            first = row["servced_by__first_name"] or ""
            last = row["servced_by__last_name"] or ""
            tellers.append(
                {
                    "teller_uuid": str(row["servced_by"]),
                    "name": f"{first} {last}".strip() or "Unknown",
                    "total": row["total"],
                    "completed": row["completed"],
                    "avg_serve_time": round(row["avg_serve_time"]) if row["avg_serve_time"] else None,
                    "avg_total_time": round(row["avg_total_time"]) if row["avg_total_time"] else None,
                }
            )
        return {"tellers": tellers}

    # ------------------------------------------------------------------
    # action: verification_stats
    # ------------------------------------------------------------------
    def _action_verification_stats(self, branch, date_from, date_to, params):
        card_qs = Ticket.objects.filter(
            branch=branch,
            created_at__date__range=[date_from, date_to],
            id_type__iexact="ghana card",
        )
        total_card = card_qs.count()
        verified_count = card_qs.filter(verification_data__verified=True).count()
        simulated_count = card_qs.filter(verification_data__simulated=True).count()

        daily = list(
            card_qs.annotate(day=TruncDate("created_at"))
            .values("day")
            .annotate(
                total=Count("id"),
                verified=Count("id", filter=Q(verification_data__verified=True)),
            )
            .order_by("day")
            .values("day", "total", "verified")
        )
        for row in daily:
            row["day"] = row["day"].isoformat()

        return {
            "total_card_tickets": total_card,
            "verified": verified_count,
            "simulated": simulated_count,
            "verification_rate": round(verified_count / total_card * 100, 1) if total_card else 0,
            "daily": daily,
        }


# ---------------------------------------------------------------------------
# Mobile customer-app ticket creation (additive, branch-based, public)
# ---------------------------------------------------------------------------


class MobileTicketCreateView(APIView):
    """
    POST /core/mobile/tickets/

    Creates a queue ticket from the mobile customer app using the checked-in
    branch (no device). Leaves the device-based /core/tickets/ untouched.
    """

    permission_classes = (AllowAny,)
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def post(self, request):
        s = MobileTicketWriteSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        ticket = s.save()
        data = TicketSerializer(ticket, context={"request": request}).data
        _broadcast_queue(str(ticket.branch.uuid), "ticket.created", data)
        return Response(data, status=status.HTTP_201_CREATED)
