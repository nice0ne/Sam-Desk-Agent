import pytest
import asyncio
from src.core.event_bus import EventBus

@pytest.mark.asyncio
async def test_event_bus_publish_and_subscribe():
    bus = EventBus()
    received = []

    async def sample_handler(data):
        received.append(data)

    bus.subscribe("test_event", sample_handler)
    await bus.publish("test_event", {"message": "hello"})
    assert received == [{"message": "hello"}]

@pytest.mark.asyncio
async def test_event_bus_unsubscribe():
    bus = EventBus()
    received = []

    async def sample_handler(data):
        received.append(data)

    bus.subscribe("test_event", sample_handler)
    bus.unsubscribe("test_event", sample_handler)
    await bus.publish("test_event", {"message": "hello"})
    assert received == []
