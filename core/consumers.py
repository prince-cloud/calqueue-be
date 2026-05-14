import json
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer


class QueueConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        qs = parse_qs(self.scope.get("query_string", b"").decode())
        token = (qs.get("token") or [""])[0]

        if not await self._authenticate(token):
            await self.close(code=4001)
            return

        self.branch_uuid = self.scope["url_route"]["kwargs"]["branch_uuid"]
        self.group_name = f"queue_{self.branch_uuid}"

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        pass  # server-push only; no client messages handled

    async def queue_update(self, event):
        """Relays a queue event from the channel layer to the WebSocket client."""
        await self.send(text_data=json.dumps(event["data"]))

    @database_sync_to_async
    def _authenticate(self, token: str) -> bool:
        if not token:
            return False
        try:
            from rest_framework_simplejwt.tokens import AccessToken
            from accounts.models import CustomUser

            validated = AccessToken(token)
            return CustomUser.objects.filter(
                id=validated["user_id"], is_active=True
            ).exists()
        except Exception:
            return False
