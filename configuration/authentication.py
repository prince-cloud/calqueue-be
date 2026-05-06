from django.core.cache import cache
from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.exceptions import TokenError

from configuration.models import Device
from configuration.tokens import DeviceAccessToken


class DeviceJWTAuthentication(BaseAuthentication):
    """
    Authenticates requests carrying a device_access JWT.
    Coexists with JWTAuthentication — each backend checks token_type and
    returns None if it doesn't own the token, so neither interferes with the other.
    """

    def authenticate(self, request):
        header = get_authorization_header(request).split()
        if not header or header[0].lower() != b"bearer":
            return None
        if len(header) != 2:
            return None

        raw_token = header[1]

        # Decode without full verification to peek at token_type.
        # If this isn't a device token, let another backend handle it.
        try:
            from rest_framework_simplejwt.backends import TokenBackend
            from django.conf import settings

            backend = TokenBackend(
                algorithm=settings.SIMPLE_JWT["ALGORITHM"],
                signing_key=settings.SECRET_KEY,
            )
            unverified = backend.decode(raw_token, verify=False)
        except Exception:
            return None

        if unverified.get("token_type") != "device_access":
            return None

        # Now fully verify the token.
        try:
            token = DeviceAccessToken(raw_token)
        except TokenError as exc:
            raise AuthenticationFailed(str(exc))

        # Check Redis blacklist (populated on logout).
        jti = token.get("jti")
        if jti and cache.get(f"device-token-blacklist/{jti}"):
            raise AuthenticationFailed("Token has been revoked.")

        device_id = token.get("device_id")
        try:
            device = Device.objects.select_related("branch").get(
                device_id=device_id,
                is_active=True,
            )
        except Device.DoesNotExist:
            raise AuthenticationFailed("Device not found or inactive.")

        return (device, token)

    def authenticate_header(self, request):
        return "Bearer"
