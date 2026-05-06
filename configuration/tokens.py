from datetime import timedelta
from rest_framework_simplejwt.tokens import Token
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from configuration.models import Device


class DeviceAccessToken(Token):
    token_type = "device_access"
    lifetime = timedelta(hours=10)


class DeviceRefreshToken(Token):
    token_type = "device_refresh"
    lifetime = timedelta(hours=24)

    @classmethod
    def for_device(cls, device: "Device") -> "DeviceRefreshToken":
        token = cls()
        token["device_id"] = str(device.device_id)
        token["serial_number"] = device.serial_number
        token["branch_id"] = device.branch.id
        token["branch_code"] = device.branch.code
        token["branch_name"] = device.branch.name
        token["label"] = device.label
        return token

    @property
    def access_token(self) -> DeviceAccessToken:
        access = DeviceAccessToken()
        access.set_exp()
        for claim in ("device_id", "serial_number", "branch_id", "branch_code", "branch_name", "label"):
            if claim in self.payload:
                access[claim] = self.payload[claim]
        return access
