"""Tests for API key authentication."""

import pytest
from src.auth import (
    generate_api_key,
    add_api_key,
    revoke_api_key,
    validate_key,
    is_auth_enabled,
    record_usage,
    get_key_stats,
    _valid_keys,
    _key_usage,
)


@pytest.fixture(autouse=True)
def clean_keys():
    """Reset key state between tests."""
    _valid_keys.clear()
    _key_usage.clear()
    yield
    _valid_keys.clear()
    _key_usage.clear()


class TestGenerateApiKey:
    def test_format(self):
        key = generate_api_key()
        assert key.startswith("ats_live_")
        assert len(key) > 20

    def test_custom_prefix(self):
        key = generate_api_key(prefix="test")
        assert key.startswith("test_live_")

    def test_unique(self):
        keys = {generate_api_key() for _ in range(100)}
        assert len(keys) == 100  # All unique


class TestKeyManagement:
    def test_add_and_validate(self):
        key = "test_key_123"
        add_api_key(key)
        assert validate_key(key) is True
        assert is_auth_enabled() is True

    def test_revoke(self):
        key1 = "test_key_456"
        key2 = "test_key_789"
        add_api_key(key1)
        add_api_key(key2)
        assert validate_key(key1) is True
        assert revoke_api_key(key1) is True
        # key1 is revoked but key2 still exists, so auth is still enabled
        assert validate_key(key1) is False
        assert validate_key(key2) is True

    def test_revoke_nonexistent(self):
        assert revoke_api_key("nonexistent") is False

    def test_open_mode_when_no_keys(self):
        """With no keys configured, any key should be valid (open mode)."""
        assert is_auth_enabled() is False
        assert validate_key("anything") is True


class TestUsageTracking:
    def test_record_usage(self):
        key = "usage_test_key"
        add_api_key(key)
        record_usage(key, "/api/analyze")
        record_usage(key, "/api/analyze")
        record_usage(key, "/api/generate")

        stats = get_key_stats()
        assert stats["keys_configured"] == 1
        assert stats["auth_enabled"] is True

    def test_stats_structure(self):
        stats = get_key_stats()
        assert "keys_configured" in stats
        assert "auth_enabled" in stats
        assert "usage" in stats
