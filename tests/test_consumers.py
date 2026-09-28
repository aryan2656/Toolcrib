import pytest
from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator
from django.test import override_settings

from crib.consumers import BoardConsumer
from crib.services import handle_scan

# Tests use the in-memory channel layer so the suite doesn't need a real
# Redis instance running; dev/prod point CHANNEL_LAYERS at Redis instead
# (see config/settings.py). Channels listens for Django's setting_changed
# signal, so override_settings correctly swaps the layer for each test.
TEST_CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}


@override_settings(CHANNEL_LAYERS=TEST_CHANNEL_LAYERS)
@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_connect_sends_current_board_state_immediately():
    communicator = WebsocketCommunicator(BoardConsumer.as_asgi(), "/ws/board/")
    connected, _ = await communicator.connect()
    assert connected

    message = await communicator.receive_json_from()
    assert message["type"] == "board_state"
    assert message["tools"] == []

    await communicator.disconnect()


@override_settings(CHANNEL_LAYERS=TEST_CHANNEL_LAYERS)
@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_checkout_pushes_a_fresh_board_state_to_connected_clients(employee, tool):
    communicator = WebsocketCommunicator(BoardConsumer.as_asgi(), "/ws/board/")
    connected, _ = await communicator.connect()
    assert connected
    await communicator.receive_json_from()  # initial (empty) board_state

    result = await database_sync_to_async(handle_scan)(employee.badge_id, tool.asset_tag)
    assert result["status"] == 200

    update = await communicator.receive_json_from(timeout=2)
    assert update["type"] == "board_state"
    assert len(update["tools"]) == 1
    assert update["tools"][0]["asset_tag"] == tool.asset_tag
    assert update["tools"][0]["holder_name"] == employee.name

    await communicator.disconnect()


@override_settings(CHANNEL_LAYERS=TEST_CHANNEL_LAYERS)
@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_ping_gets_a_pong():
    communicator = WebsocketCommunicator(BoardConsumer.as_asgi(), "/ws/board/")
    connected, _ = await communicator.connect()
    assert connected
    await communicator.receive_json_from()  # initial board_state

    await communicator.send_json_to({"type": "ping"})
    reply = await communicator.receive_json_from()
    assert reply == {"type": "pong"}

    await communicator.disconnect()
