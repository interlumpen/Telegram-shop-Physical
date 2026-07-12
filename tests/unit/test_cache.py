"""
Tests for the caching layer — in particular the JSON-only (de)serialization that
replaced the previous pickle path (pickle.loads on cached data was an RCE risk).
"""
import json
import pickle

import pytest
from unittest.mock import AsyncMock

from bot.caching.cache import CacheManager


@pytest.mark.unit
@pytest.mark.caching
class TestCacheJsonOnly:
    """The cache must never unpickle data read from Redis."""

    async def test_pickle_payload_is_not_deserialized(self):
        """A pickled payload in Redis must NOT be unpickled — returns a miss."""
        redis = AsyncMock()
        redis.get.return_value = pickle.dumps({"evil": "object"})

        cache = CacheManager(redis)
        result = await cache.get("some_key")

        # JSON decode fails on pickle bytes -> treated as a cache miss, never unpickled.
        assert result is None

    async def test_json_roundtrip(self):
        """A normally cached (JSON-serializable) value round-trips correctly."""
        store = {}

        async def _setex(key, ttl, value):
            store[key] = value

        async def _get(key):
            return store.get(key)

        redis = AsyncMock()
        redis.setex.side_effect = _setex
        redis.get.side_effect = _get

        cache = CacheManager(redis)
        await cache.set("k", {"a": 1, "b": [1, 2, 3]})

        # Stored as JSON bytes, not pickle.
        assert json.loads(store["k"].decode("utf-8")) == {"a": 1, "b": [1, 2, 3]}
        assert await cache.get("k") == {"a": 1, "b": [1, 2, 3]}

    async def test_corrupt_value_returns_none(self):
        """Non-JSON, non-decodable bytes are a miss, not an error."""
        redis = AsyncMock()
        redis.get.return_value = b"\x80\x04not-json"

        cache = CacheManager(redis)
        assert await cache.get("k") is None
