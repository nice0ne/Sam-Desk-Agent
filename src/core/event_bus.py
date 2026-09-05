import asyncio
from typing import Callable, Any, Dict, List
import inspect

class EventBus:
    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}

    def subscribe(self, event_type: str, handler: Callable) -> None:
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        if handler not in self._subscribers[event_type]:
            self._subscribers[event_type].append(handler)

    def unsubscribe(self, event_type: str, handler: Callable) -> None:
        if event_type in self._subscribers and handler in self._subscribers[event_type]:
            self._subscribers[event_type].remove(handler)

    async def publish(self, event_type: str, data: Any = None) -> None:
        if event_type not in self._subscribers:
            return
        tasks = []
        for handler in self._subscribers[event_type]:
            if inspect.iscoroutinefunction(handler):
                tasks.append(asyncio.create_task(handler(data)))
            else:
                handler(data)
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
