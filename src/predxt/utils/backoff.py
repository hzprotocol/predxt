import random


class ExponentialBackoff:
    def __init__(self, base_seconds: float = 1.0, max_seconds: float = 60.0):
        self.base = base_seconds
        self.max = max_seconds
        self._attempt = 0

    def next_delay(self) -> float:
        delay = min(self.base * (2**self._attempt), self.max)
        jitter = random.uniform(0, delay * 0.1)
        self._attempt += 1
        return delay + jitter

    def reset(self) -> None:
        self._attempt = 0
