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
from .models import Branch, Device, MainService, Service, Counter
from .permissions import IsDevice
from .serializers import (
    BranchSerializer,
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
    queryset = (
        MainService.objects.filter(is_active=True)
        .prefetch_related("services")
        .order_by("created_at")
    )
    serializer_class = MainServiceSerializer
    filterset_class = MainServiceFilter
    search_fields = ("name",)
    ordering_fields = ("name", "created_at")
    lookup_field = "uuid"

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [(IsSystemUser | IsDevice)()]
        return [ModelPermissions()]


class ServiceViewSet(ModelViewSet):
    queryset = (
        Service.objects.filter(is_active=True)
        .select_related("main_service")
        .order_by("name")
    )
    filterset_class = ServiceFilter
    search_fields = ("name",)
    ordering_fields = ("name", "created_at")
    lookup_field = "uuid"

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
