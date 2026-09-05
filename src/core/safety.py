import asyncio
import time
from typing import List, Optional
from src.core.event_bus import EventBus

class SafetySupervisor:
    def __init__(
        self,
        event_bus: Optional[EventBus] = None,
        window_seconds: float = 1.0,
        required_presses: int = 3,
    ):
        self.event_bus = event_bus
        self.window_seconds = window_seconds
        self.required_presses = required_presses
        self._esc_timestamps: List[float] = []
        self._is_cancelled: bool = False

    def is_cancelled(self) -> bool:
        return self._is_cancelled

    def trigger_panic(self, reason: str = "panic switch activated") -> None:
        self._is_cancelled = True
        if self.event_bus:
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self.event_bus.publish("safety:panic", {"reason": reason}))
            except RuntimeError:
                pass

    def reset(self) -> None:
        self._is_cancelled = False
        self._esc_timestamps.clear()

    def record_esc_press(self, timestamp: Optional[float] = None) -> bool:
        if timestamp is None:
            timestamp = time.time()
        self._esc_timestamps.append(timestamp)
        # Prune presses outside window_seconds
        self._esc_timestamps = [t for t in self._esc_timestamps if timestamp - t <= self.window_seconds]
        if len(self._esc_timestamps) >= self.required_presses:
            self.trigger_panic("Triple-Esc panic trigger detected")
            return True
        return False

    def check_action_budget(self, current_step: int, max_budget: int = 10) -> bool:
        if current_step > max_budget:
            self.trigger_panic(f"Action budget exceeded ({current_step} > {max_budget})")
            return False
        return True
