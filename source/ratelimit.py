import time
from collections import deque

SWEEP_EVERY_CALLS = 1024


class SlidingWindowLimiter:
    """Exact sliding-window log: per key, at most `limit` events per `window_seconds`."""

    def __init__(self, limit: int, window_seconds: float) -> None:
        self._limit = limit
        self._window = window_seconds
        self._events: dict[str, deque[float]] = {}
        self._calls_until_sweep = SWEEP_EVERY_CALLS

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        cutoff = now - self._window
        events = self._events.setdefault(key, deque())
        while events and events[0] <= cutoff:
            events.popleft()
        self._sweep(cutoff)
        if len(events) >= self._limit:
            return False
        events.append(now)
        return True

    def _sweep(self, cutoff: float) -> None:
        """Drop idle keys periodically so key-rotating clients cannot grow memory forever."""
        self._calls_until_sweep -= 1
        if self._calls_until_sweep > 0:
            return
        self._calls_until_sweep = SWEEP_EVERY_CALLS
        self._events = {key: events for key, events in self._events.items() if events and events[-1] > cutoff}
