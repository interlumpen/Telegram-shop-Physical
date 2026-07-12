"""
Tests for the rate limiter — pruning of idle users (memory-leak fix) and the
read-only get_wait_time that must not materialize empty tracking entries.
"""
import time

import pytest

from bot.middleware.rate_limit import RateLimiter, RateLimitConfig


@pytest.mark.unit
class TestRateLimiterPruning:
    def test_prune_removes_idle_users_and_expired_bans(self):
        config = RateLimitConfig()
        limiter = RateLimiter(config)
        limiter._prune_interval = 0  # force prune to run

        # Requests older than the window -> should be dropped entirely.
        limiter.user_requests[111] = [time.time() - 10_000]
        limiter.user_actions['buy_item'][111] = [time.time() - 10_000]
        # A ban older than ban_duration -> should be cleared.
        limiter.banned_users[222] = time.time() - (config.ban_duration + 10)
        # A fresh request -> should be kept.
        limiter.user_requests[333] = [time.time()]

        limiter.prune()

        assert 111 not in limiter.user_requests
        assert 'buy_item' not in limiter.user_actions
        assert 222 not in limiter.banned_users
        assert 333 in limiter.user_requests

    def test_get_wait_time_does_not_create_entries(self):
        """Querying wait time for an unknown user must not grow the dicts."""
        limiter = RateLimiter(RateLimitConfig())

        wait = limiter.get_wait_time(999, 'buy_item')

        assert wait == 0
        assert 999 not in limiter.user_requests
        assert 999 not in limiter.user_actions.get('buy_item', {})
