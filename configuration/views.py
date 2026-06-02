from django.core.cache import cache
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.generics import CreateAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from rest_framework_simplejwt.exceptions import TokenError

from accounts.permissions import IsSystemUser, ModelPermissions
from helpers import exceptions
from .filters import BranchFilter, CounterFilter, DeviceFilter, MainServiceFilter, ServiceFilter
from .models import Branch, Device, MainService, Service, Counter, SystemVoiceConfig, BranchVoiceConfig, BranchTVConfig, TVAdvertisement, OtherBank, OtherBankBranch
from .permissions import IsDevice
from rest_framework.parsers import MultiPartParser, JSONParser, FormParser
from .serializers import (
    BranchSerializer,
    BranchTVConfigSerializer,
    OtherBankSerializer,
    OtherBankWriteSerializer,
    OtherBankBranchSerializer,
    OtherBankBranchWriteSerializer,
    BranchVoiceConfigSerializer,
    BranchWriteSerializer,
    CounterSerializer,
    CounterWriteSerializer,
    DeviceLoginSerializer,
    DeviceRefreshSerializer,
    DeviceSerializer,
    DeviceWriteSerializer,
    MainServiceSerializer,
    ServiceSerializer,
    ServiceWriteSerializer,
    SystemVoiceConfigSerializer,
    TVAdvertisementSerializer,
    TVAdvertisementWriteSerializer,
)
from .tokens import DeviceRefreshToken


class DeviceLoginView(CreateAPIView):
    permission_classes = (permissions.AllowAny,)
    serializer_class = DeviceLoginSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        device: Device = serializer.validated_data["device"]
        refresh = DeviceRefreshToken.for_device(device)
        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "device": DeviceSerializer(device).data,
            },
            status=status.HTTP_200_OK,
        )


class DeviceTokenRefreshView(CreateAPIView):
    permission_classes = (permissions.AllowAny,)
    serializer_class = DeviceRefreshSerializer

    def post(self, request):
        refresh_raw = request.data.get("refresh")
        if not refresh_raw:
            raise exceptions.GeneralException(detail="Refresh token is required.")
        try:
            refresh = DeviceRefreshToken(refresh_raw)
        except TokenError:
            raise exceptions.InvalidToken()

        jti = refresh.get("jti")
        if jti:
            exp = refresh.get("exp", 0)
            ttl = exp - int(timezone.now().timestamp())
            if ttl > 0:
                cache.set(f"device-token-blacklist/{jti}", True, ttl)

        return Response(
            {"access": str(refresh.access_token)}, status=status.HTTP_200_OK
        )


class DeviceLogoutView(APIView):
    permission_classes = (IsDevice,)

    def post(self, request):
        refresh_raw = request.data.get("refresh")
        if not refresh_raw:
            raise exceptions.GeneralException(detail="Refresh token is required.")
        try:
            refresh = DeviceRefreshToken(refresh_raw)
            jti = refresh.get("jti")
            exp = refresh.get("exp", 0)
            ttl = exp - int(timezone.now().timestamp())
            if jti and ttl > 0:
                cache.set(f"device-token-blacklist/{jti}", True, ttl)
        except TokenError:
            pass
        return Response({"message": "Device logged out."}, status=status.HTTP_200_OK)


class DeviceProfileView(APIView):
    permission_classes = (IsDevice,)

    def get(self, request):
        return Response(DeviceSerializer(request.user).data)


class BranchViewSet(ModelViewSet):
    queryset = Branch.objects.prefetch_related("working_hours").order_by("name")
    filterset_class = BranchFilter
    search_fields = ("name", "code", "location")
    ordering_fields = ("name", "created_at")
    lookup_field = "uuid"

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [(IsSystemUser | IsDevice)()]
        return [ModelPermissions()]

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return BranchWriteSerializer
        return BranchSerializer

    def create(self, request, *args, **kwargs):
        write_serializer = self.get_serializer(data=request.data)
        write_serializer.is_valid(raise_exception=True)
        instance = write_serializer.save()
        return Response(BranchSerializer(instance).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        write_serializer = self.get_serializer(instance, data=request.data, partial=partial)
        write_serializer.is_valid(raise_exception=True)
        instance = write_serializer.save()
        return Response(BranchSerializer(instance).data)


class DeviceViewSet(ModelViewSet):
    queryset = Device.objects.select_related("branch").order_by("branch", "label")
    filterset_class = DeviceFilter
    search_fields = ("username", "serial_number", "label")
    ordering_fields = ("label", "created_at")
    lookup_field = "uuid"

    def get_permissions(self):
        return [ModelPermissions()]

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return DeviceWriteSerializer
        return DeviceSerializer

    def create(self, request, *args, **kwargs):
        write_serializer = self.get_serializer(data=request.data)
        write_serializer.is_valid(raise_exception=True)
        instance = write_serializer.save()
        return Response(DeviceSerializer(instance).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        write_serializer = self.get_serializer(instance, data=request.data, partial=partial)
        write_serializer.is_valid(raise_exception=True)
        instance = write_serializer.save()
        return Response(DeviceSerializer(instance).data)


class MainServiceViewSet(ModelViewSet):
    serializer_class = MainServiceSerializer
    filterset_class = MainServiceFilter
    search_fields = ("name",)
    ordering_fields = ("name", "created_at")
    lookup_field = "uuid"

    def get_queryset(self):
        qs = MainService.objects.prefetch_related("services").order_by("created_at")
        if isinstance(self.request.user, Device):
            qs = qs.filter(is_active=True)
        return qs

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [(IsSystemUser | IsDevice)()]
        return [ModelPermissions()]


class ServiceViewSet(ModelViewSet):
    filterset_class = ServiceFilter
    search_fields = ("name",)
    ordering_fields = ("name", "created_at")
    lookup_field = "uuid"

    def get_queryset(self):
        qs = Service.objects.select_related("main_service").order_by("name")
        if isinstance(self.request.user, Device):
            qs = qs.filter(is_active=True)
        return qs

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [(IsSystemUser | IsDevice)()]
        return [ModelPermissions()]

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return ServiceWriteSerializer
        return ServiceSerializer

    def create(self, request, *args, **kwargs):
        write_serializer = self.get_serializer(data=request.data)
        write_serializer.is_valid(raise_exception=True)
        instance = write_serializer.save()
        return Response(ServiceSerializer(instance).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        write_serializer = self.get_serializer(instance, data=request.data, partial=partial)
        write_serializer.is_valid(raise_exception=True)
        instance = write_serializer.save()
        return Response(ServiceSerializer(instance).data)


class CounterViewSet(ModelViewSet):
    queryset = (
        Counter.objects.select_related("branch")
        .prefetch_related("operations")
        .order_by("branch", "counter_name")
    )
    filterset_class = CounterFilter
    search_fields = ("counter_code", "counter_name")
    ordering_fields = ("counter_name", "created_at")
    lookup_field = "uuid"

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [(IsSystemUser | IsDevice)()]
        return [ModelPermissions()]

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return CounterWriteSerializer
        return CounterSerializer

    def create(self, request, *args, **kwargs):
        from accounts.models import CustomUser
        write_serializer = self.get_serializer(data=request.data)
        write_serializer.is_valid(raise_exception=True)
        created_by = request.user if isinstance(request.user, CustomUser) else None
        instance = write_serializer.save(created_by=created_by)
        return Response(CounterSerializer(instance).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        write_serializer = self.get_serializer(instance, data=request.data, partial=partial)
        write_serializer.is_valid(raise_exception=True)
        instance = write_serializer.save()
        return Response(CounterSerializer(instance).data)


class SystemVoiceConfigView(APIView):
    permission_classes = [IsSystemUser]

    def get(self, request):
        config = SystemVoiceConfig.get_solo()
        return Response(SystemVoiceConfigSerializer(config).data)

    def put(self, request):
        config = SystemVoiceConfig.get_solo()
        s = SystemVoiceConfigSerializer(config, data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        s.save()
        config.refresh_from_db()
        return Response(SystemVoiceConfigSerializer(config).data)


class BranchVoiceConfigView(APIView):
    permission_classes = [IsSystemUser]
    parser_classes = [JSONParser, FormParser]

    def _get_branch(self, branch_uuid):
        try:
            return Branch.objects.get(uuid=branch_uuid)
        except Branch.DoesNotExist:
            return None

    def get(self, request, branch_uuid):
        branch = self._get_branch(branch_uuid)
        if not branch:
            return Response({"detail": "Branch not found."}, status=status.HTTP_404_NOT_FOUND)
        config, _ = BranchVoiceConfig.objects.get_or_create(branch=branch)
        return Response(BranchVoiceConfigSerializer(config, context={"request": request}).data)

    def put(self, request, branch_uuid):
        branch = self._get_branch(branch_uuid)
        if not branch:
            return Response({"detail": "Branch not found."}, status=status.HTTP_404_NOT_FOUND)
        config, _ = BranchVoiceConfig.objects.get_or_create(branch=branch)
        s = BranchVoiceConfigSerializer(config, data=request.data, partial=True, context={"request": request})
        s.is_valid(raise_exception=True)
        s.save()
        config.refresh_from_db()
        return Response(BranchVoiceConfigSerializer(config, context={"request": request}).data)


class VoicePreviewView(APIView):
    """
    POST /configuration/voice-config/preview/
    Generate a short TTS clip with the supplied settings so the user can
    hear the voice and speed before saving.  Returns raw MP3 bytes.
    """
    permission_classes = [IsSystemUser]
    _SAMPLE = "Ticket A 0 0 1, please proceed to Counter One. Thank you."

    def post(self, request):
        from django.http import HttpResponse
        from core.tts import _generate_edge_tts, _generate_gtts
        from .models import TTSEngine

        engine = request.data.get("engine", TTSEngine.EDGE_TTS)
        template = (request.data.get("announcement_template") or "").strip()
        text = (
            template.format(
                ticket_number="A 0 0 1",
                counter_name="Counter One",
                branch_name="Main Branch",
            )
            if template
            else self._SAMPLE
        )

        try:
            if engine == TTSEngine.EDGE_TTS:
                voice = request.data.get("voice") or "en-US-GuyNeural"
                rate = request.data.get("rate") or "+0%"
                audio = _generate_edge_tts(text, voice, rate)
            else:
                language = request.data.get("language") or "en"
                tld = request.data.get("tld") or "com"
                slow = bool(request.data.get("slow", False))
                audio = _generate_gtts(text, language, tld, slow)
        except Exception as exc:
            return Response(
                {"detail": f"TTS generation failed: {exc}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return HttpResponse(audio, content_type="audio/mpeg")


class BranchTVConfigView(APIView):
    permission_classes = [IsSystemUser]
    parser_classes = [MultiPartParser, JSONParser, FormParser]

    def _get_branch(self, branch_uuid):
        try:
            return Branch.objects.get(uuid=branch_uuid)
        except Branch.DoesNotExist:
            return None

    def get(self, request, branch_uuid):
        branch = self._get_branch(branch_uuid)
        if not branch:
            return Response({"detail": "Branch not found."}, status=status.HTTP_404_NOT_FOUND)
        config, _ = BranchTVConfig.objects.get_or_create(branch=branch)
        return Response(BranchTVConfigSerializer(config, context={"request": request}).data)

    def put(self, request, branch_uuid):
        branch = self._get_branch(branch_uuid)
        if not branch:
            return Response({"detail": "Branch not found."}, status=status.HTTP_404_NOT_FOUND)
        config, _ = BranchTVConfig.objects.get_or_create(branch=branch)
        s = BranchTVConfigSerializer(config, data=request.data, partial=True, context={"request": request})
        s.is_valid(raise_exception=True)
        s.save()
        config.refresh_from_db()
        return Response(BranchTVConfigSerializer(config, context={"request": request}).data)


class BranchTVAdsView(APIView):
    """
    POST   /configuration/branches/{uuid}/tv-config/ads/   — upload a new ad (image or video)
    DELETE /configuration/branches/{uuid}/tv-config/ads/{ad_id}/ — remove an ad
    PATCH  /configuration/branches/{uuid}/tv-config/ads/{ad_id}/ — update order
    """
    permission_classes = [IsSystemUser]
    parser_classes = [MultiPartParser, FormParser]

    def _get_config(self, branch_uuid):
        try:
            branch = Branch.objects.get(uuid=branch_uuid)
        except Branch.DoesNotExist:
            return None, None
        config, _ = BranchTVConfig.objects.get_or_create(branch=branch)
        return branch, config

    def post(self, request, branch_uuid):
        _, config = self._get_config(branch_uuid)
        if config is None:
            return Response({"detail": "Branch not found."}, status=status.HTTP_404_NOT_FOUND)
        s = TVAdvertisementWriteSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        ad = s.save(tv_config=config)
        return Response(TVAdvertisementSerializer(ad, context={"request": request}).data, status=status.HTTP_201_CREATED)

    def delete(self, request, branch_uuid, ad_id):
        _, config = self._get_config(branch_uuid)
        if config is None:
            return Response({"detail": "Branch not found."}, status=status.HTTP_404_NOT_FOUND)
        try:
            ad = TVAdvertisement.objects.get(pk=ad_id, tv_config=config)
        except TVAdvertisement.DoesNotExist:
            return Response({"detail": "Ad not found."}, status=status.HTTP_404_NOT_FOUND)
        ad.file.delete(save=False)
        ad.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def patch(self, request, branch_uuid, ad_id):
        _, config = self._get_config(branch_uuid)
        if config is None:
            return Response({"detail": "Branch not found."}, status=status.HTTP_404_NOT_FOUND)
        try:
            ad = TVAdvertisement.objects.get(pk=ad_id, tv_config=config)
        except TVAdvertisement.DoesNotExist:
            return Response({"detail": "Ad not found."}, status=status.HTTP_404_NOT_FOUND)
        order = request.data.get("order")
        if order is not None:
            ad.order = int(order)
            ad.save(update_fields=["order"])
        return Response(TVAdvertisementSerializer(ad, context={"request": request}).data)


class OtherBankViewSet(ModelViewSet):
    queryset = OtherBank.objects.prefetch_related("branches").order_by("name")
    lookup_field = "uuid"

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [(IsSystemUser | IsDevice)()]
        return [ModelPermissions()]

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return OtherBankWriteSerializer
        return OtherBankSerializer

    def create(self, request, *args, **kwargs):
        write_serializer = self.get_serializer(data=request.data)
        write_serializer.is_valid(raise_exception=True)
        instance = write_serializer.save()
        return Response(OtherBankSerializer(instance).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        write_serializer = self.get_serializer(instance, data=request.data, partial=partial)
        write_serializer.is_valid(raise_exception=True)
        instance = write_serializer.save()
        return Response(OtherBankSerializer(instance).data)


class OtherBankBranchViewSet(ModelViewSet):
    lookup_field = "uuid"

    def get_queryset(self):
        qs = OtherBankBranch.objects.select_related("bank").order_by("bank__name", "name")
        bank_uuid = self.request.query_params.get("bank")
        if bank_uuid:
            qs = qs.filter(bank__uuid=bank_uuid)
        return qs

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [(IsSystemUser | IsDevice)()]
        return [ModelPermissions()]

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return OtherBankBranchWriteSerializer
        return OtherBankBranchSerializer

    def create(self, request, *args, **kwargs):
        write_serializer = self.get_serializer(data=request.data)
        write_serializer.is_valid(raise_exception=True)
        instance = write_serializer.save()
        return Response(OtherBankBranchSerializer(instance).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        write_serializer = self.get_serializer(instance, data=request.data, partial=partial)
        write_serializer.is_valid(raise_exception=True)
        instance = write_serializer.save()
        return Response(OtherBankBranchSerializer(instance).data)
