from functools import reduce
import operator

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from configuration.models import Counter
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


def _broadcast_with_audio_background(ticket_data: dict, ticket_uuid: str, counter_uuid: str, branch_uuid: str) -> None:
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

            ticket.status = TicketStatus.ON_GOING
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
        _broadcast_with_audio_background(data, str(ticket.uuid), str(counter.uuid), branch_uuid)
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
