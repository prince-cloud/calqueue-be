from django.core.cache import cache
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.generics import CreateAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError

from helpers import exceptions
from .models import Device
from .permissions import IsDevice
from .serializers import DeviceLoginSerializer, DeviceRefreshSerializer, DeviceSerializer
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

        # Blacklist the used refresh token (rotation)
        jti = refresh.get("jti")
        if jti:
            exp = refresh.get("exp", 0)
            ttl = exp - int(timezone.now().timestamp())
            if ttl > 0:
                cache.set(f"device-token-blacklist/{jti}", True, ttl)

        return Response(
            {"access": str(refresh.access_token)},
            status=status.HTTP_200_OK,
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
            pass  # Already invalid — treat as logged out

        return Response({"message": "Device logged out."}, status=status.HTTP_200_OK)


class DeviceProfileView(APIView):
    permission_classes = (IsDevice,)

    def get(self, request):
        return Response(DeviceSerializer(request.user).data)
