import time
from collections import deque

SWEEP_EVERY_CALLS = 1024


class SlidingWindowLimiter:
    """Exact sliding-window log: per key, at most `limit` events per `window_seconds`."""

    def __init__(self, limit: int, window_seconds: float) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._events: dict[str, deque[float]] = {}
        self._calls_until_sweep = SWEEP_EVERY_CALLS

    def acquire(self, key: str) -> float | None:
        """None if the request is allowed; otherwise seconds until a slot frees."""
        now = time.monotonic()
        cutoff = now - self.window_seconds
        events = self._events.setdefault(key, deque())
        while events and events[0] <= cutoff:
            events.popleft()
        self._sweep(cutoff)
        if len(events) >= self.limit:
            return events[0] - cutoff
        events.append(now)
        return None

    def _sweep(self, cutoff: float) -> None:
        """Drop idle keys periodically so key-rotating clients cannot grow memory forever."""
        self._calls_until_sweep -= 1
        if self._calls_until_sweep > 0:
            return
        self._calls_until_sweep = SWEEP_EVERY_CALLS
        self._events = {key: events for key, events in self._events.items() if events and events[-1] > cutoff}
