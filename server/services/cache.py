"""Cache wrapper: Redis if REDIS_URL is set, otherwise in-process dict.

This replaces the ad-hoc cache_data global in app.py for shared
multi-worker caching once we run under Waitress with multiple threads.
"""
from __future__ import annotations

import json
import time
from threading import RLock
from typing import Any, Optional

from config.settings import settings as config


class _MemoryCache:
    def __init__(self):
        self._data: dict[str, tuple[float, Any]] = {}
        self._lock = RLock()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            rec = self._data.get(key)
            if not rec:
                return None
            expires, value = rec
            if expires and time.time() > expires:
                self._data.pop(key, None)
                return None
            return value

    def set(self, key: str, value: Any, ttl: int = 0) -> None:
        with self._lock:
            self._data[key] = (time.time() + ttl if ttl else 0, value)

    def delete(self, key: str) -> None:
        with self._lock:
            self._data.pop(key, None)


class _RedisCache:
    def __init__(self, url: str):
        import redis  # imported lazily so the dep is optional
        self._r = redis.from_url(url)

    def get(self, key: str) -> Optional[Any]:
        raw = self._r.get(key)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except Exception:
            return None

    def set(self, key: str, value: Any, ttl: int = 0) -> None:
        payload = json.dumps(value, default=str)
        if ttl:
            self._r.setex(key, ttl, payload)
        else:
            self._r.set(key, payload)

    def delete(self, key: str) -> None:
        self._r.delete(key)


def _build():
    if config.REDIS_URL:
        try:
            return _RedisCache(config.REDIS_URL)
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning("Redis cache unavailable, falling back to memory: %s", e)
    return _MemoryCache()


cache = _build()
