import pytest
import asyncio
from src.core.safety import SafetySupervisor
from src.core.event_bus import EventBus

def test_action_budget_limit():
    supervisor = SafetySupervisor()
    assert supervisor.check_action_budget(current_step=1, max_budget=10) is True
    assert supervisor.check_action_budget(current_step=10, max_budget=10) is True
    assert supervisor.check_action_budget(current_step=11, max_budget=10) is False
    assert supervisor.is_cancelled() is True

def test_panic_trigger_and_cancel():
    supervisor = SafetySupervisor()
    assert supervisor.is_cancelled() is False
    supervisor.trigger_panic("user emergency stop")
    assert supervisor.is_cancelled() is True
    supervisor.reset()
    assert supervisor.is_cancelled() is False

def test_triple_esc_detection():
    supervisor = SafetySupervisor()
    # Press 1
    assert supervisor.record_esc_press(100.0) is False
    # Press 2 within 0.3s
    assert supervisor.record_esc_press(100.3) is False
    # Press 3 within 0.7s total (< 1.0s window)
    assert supervisor.record_esc_press(100.7) is True
    assert supervisor.is_cancelled() is True

def test_esc_detection_outside_window():
    supervisor = SafetySupervisor(window_seconds=1.0, required_presses=3)
    assert supervisor.record_esc_press(100.0) is False
    assert supervisor.record_esc_press(100.5) is False
    # Next press is 1.6s after first press, so first press expires:
    assert supervisor.record_esc_press(101.6) is False
    assert supervisor.is_cancelled() is False
    # Next press at 101.8: 101.8 - 100.5 = 1.3 > 1.0, so 100.5 expires; [101.6, 101.8] remains (2 presses)
    assert supervisor.record_esc_press(101.8) is False
    assert supervisor.is_cancelled() is False
    # Third within window of 101.6: 102.0 - 101.6 = 0.4 <= 1.0; [101.6, 101.8, 102.0] -> 3 presses
    assert supervisor.record_esc_press(102.0) is True
    assert supervisor.is_cancelled() is True

@pytest.mark.asyncio
async def test_panic_event_publishing():
    bus = EventBus()
    events = []

    async def on_panic(data):
        events.append(data)

    bus.subscribe("safety:panic", on_panic)
    supervisor = SafetySupervisor(event_bus=bus)
    supervisor.trigger_panic("test panic")

    # Give event loop a cycle to run the task
    await asyncio.sleep(0.01)
    assert len(events) == 1
    assert events[0] == {"reason": "test panic"}
