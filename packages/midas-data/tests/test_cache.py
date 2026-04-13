"""Tier 1 unit tests for the data cache layer."""

from datetime import date, datetime, timedelta

import pytest

from midas_data.fabric.cache import DataCache


class TestDataCacheLogic:
    """Test cache TTL and stampede logic (no Redis connection needed)."""

    def setup_method(self):
        self.cache = DataCache("redis://dummy:6379/0")

    @pytest.mark.unit
    def test_jitter_ttl_reduces_value(self):
        """Stampede protection should reduce TTL by 0-10%."""
        ttl = 3600
        jittered = self.cache._jitter_ttl(ttl)
        assert jittered <= ttl
        assert jittered >= ttl * 0.9

    @pytest.mark.unit
    def test_jitter_ttl_zero_returns_zero(self):
        assert self.cache._jitter_ttl(0) == 0

    @pytest.mark.unit
    def test_jitter_ttl_small_value(self):
        jittered = self.cache._jitter_ttl(5)
        assert jittered >= 1
        assert jittered <= 5

    @pytest.mark.unit
    def test_news_ttl_fresh_content(self):
        """Fresh news (< 24h old) should get 1 hour TTL."""
        items = [{"published_at": datetime.utcnow().isoformat()}]
        ttl = self.cache._compute_news_ttl(items)
        assert ttl == 3600

    @pytest.mark.unit
    def test_news_ttl_aging_content(self):
        """Aging news (24-72h old) should get 6 hour TTL."""
        items = [{"published_at": (datetime.utcnow() - timedelta(hours=48)).isoformat()}]
        ttl = self.cache._compute_news_ttl(items)
        assert ttl == 21600

    @pytest.mark.unit
    def test_news_ttl_old_content(self):
        """Old news (> 72h) should get 24 hour TTL."""
        items = [{"published_at": (datetime.utcnow() - timedelta(hours=96)).isoformat()}]
        ttl = self.cache._compute_news_ttl(items)
        assert ttl == 86400

    @pytest.mark.unit
    def test_news_ttl_empty_list(self):
        ttl = self.cache._compute_news_ttl([])
        assert ttl == 3600

    @pytest.mark.unit
    def test_news_ttl_no_published_at(self):
        items = [{"title": "test"}]
        ttl = self.cache._compute_news_ttl(items)
        assert ttl == 3600
