import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.core.serializers.json import DjangoJSONEncoder

from .services import BOARD_GROUP, board_state


class BoardConsumer(AsyncJsonWebsocketConsumer):
    """Pushes board_state() to every connected viewer on connect, and again
    whenever handle_scan() changes what's checked out (see services.py's
    notify_board_update()). board_state() itself is untouched by any of
    this — it still returns native datetimes for board_state()'s own tests;
    only the WebSocket transport needs Django's JSON encoder to handle them,
    since AsyncJsonWebsocketConsumer's default send_json() doesn't."""

    async def connect(self):
        await self.channel_layer.group_add(BOARD_GROUP, self.channel_name)
        await self.accept()
        await self.push_board_state()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(BOARD_GROUP, self.channel_name)

    async def receive_json(self, content, **kwargs):
        if content.get("type") == "ping":
            await self.send_json({"type": "pong"})

    async def board_update(self, event):
        # Group message type "board.update" is routed here by Channels
        # (dots in "type" map to underscored method names).
        await self.push_board_state()

    async def push_board_state(self):
        state = await database_sync_to_async(board_state)()
        payload = {"type": "board_state", **state}
        await self.send(text_data=json.dumps(payload, cls=DjangoJSONEncoder))
