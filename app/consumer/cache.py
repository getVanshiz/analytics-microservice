import time
import threading
from typing import Any, Optional, Dict, Set


class TTLDict:
    """
    Simple TTL dictionary: key -> (value, expires_at).
    Thread-safe for simple single-worker usage.
    """
    def __init__(self, ttl_seconds: int = 3600, max_size: int = 100_000):
        self.ttl = ttl_seconds
        self.max_size = max_size
        self._store: Dict[Any, Any] = {}
        self._exp: Dict[Any, float] = {}
        self._lock = threading.Lock()

    def set(self, key: Any, value: Any, ttl: Optional[int] = None) -> None:
        with self._lock:
            now = time.time()
            exp = now + (ttl if ttl is not None else self.ttl)
            if len(self._store) >= self.max_size:
                self._prune(n=1000)
            self._store[key] = value
            self._exp[key] = exp

    def get(self, key: Any) -> Optional[Any]:
        with self._lock:
            now = time.time()
            exp = self._exp.get(key)
            if exp is None:
                return None
            if exp < now:
                self._delete_no_lock(key)
                return None
            return self._store.get(key)

    def pop(self, key: Any) -> Optional[Any]:
        with self._lock:
            return self._delete_no_lock(key)

    def has(self, key: Any) -> bool:
        with self._lock:
            now = time.time()
            exp = self._exp.get(key)
            if exp is None:
                return False
            if exp < now:
                self._delete_no_lock(key)
                return False
            return True

    def size(self) -> int:
        with self._lock:
            self._prune()
            return len(self._store)

    def _delete_no_lock(self, key: Any) -> Optional[Any]:
        val = self._store.pop(key, None)
        self._exp.pop(key, None)
        return val

    def _prune(self, n: int = 1000) -> None:
        now = time.time()
        # Remove expired first
        expired = [k for k, exp in self._exp.items() if exp < now]
        for k in expired[:n]:
            self._delete_no_lock(k)
        # If still too big, remove oldest by expiry
        if len(self._store) > self.max_size:
            items = sorted(self._exp.items(), key=lambda kv: kv[1])
            for k, _ in items[:n]:
                self._delete_no_lock(k)


class TTLSet:
    """
    TTLSet stores unique items with expiration. Backed by dict.
    Supports approx-unique counting for short windows.
    """
    def __init__(self, ttl_seconds: int = 3600, max_size: int = 200_000):
        self.ttl = ttl_seconds
        self.max_size = max_size
        self._exp: Dict[Any, float] = {}
        self._lock = threading.Lock()

    def add(self, item: Any, ttl: Optional[int] = None) -> None:
        with self._lock:
            now = time.time()
            exp = now + (ttl if ttl is not None else self.ttl)
            if len(self._exp) >= self.max_size:
                self._prune(n=2000)
            self._exp[item] = exp

    def contains(self, item: Any) -> bool:
        with self._lock:
            now = time.time()
            exp = self._exp.get(item)
            if exp is None:
                return False
            if exp < now:
                self._exp.pop(item, None)
                return False
            return True

    def size(self) -> int:
        with self._lock:
            self._prune()
            return len(self._exp)

    def _prune(self, n: int = 2000) -> None:
        now = time.time()
        expired = [k for k, exp in self._exp.items() if exp < now]
        for k in expired[:n]:
            self._exp.pop(k, None)
        if len(self._exp) > self.max_size:
            items = sorted(self._exp.items(), key=lambda kv: kv[1])
            for k, _ in items[:n]:
                self._exp.pop(k, None)