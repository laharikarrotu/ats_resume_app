"""Tests for utility functions."""

from src.utils import normalize_keyword, deduplicate_preserve_order


class TestNormalizeKeyword:
    def test_basic(self):
        assert normalize_keyword("  Python  ") == "Python"

    def test_underscore(self):
        assert normalize_keyword("machine_learning") == "machine learning"

    def test_empty(self):
        assert normalize_keyword("") == ""
        assert normalize_keyword("   ") == ""


class TestDeduplicatePreserveOrder:
    def test_basic(self):
        result = deduplicate_preserve_order(["a", "b", "a", "c", "b"])
        assert result == ["a", "b", "c"]

    def test_empty_strings_filtered(self):
        result = deduplicate_preserve_order(["a", "", "b", "", "c"])
        assert result == ["a", "b", "c"]

    def test_preserves_order(self):
        result = deduplicate_preserve_order(["z", "a", "m", "z", "a"])
        assert result == ["z", "a", "m"]

    def test_empty_input(self):
        assert deduplicate_preserve_order([]) == []

    def test_all_same(self):
        assert deduplicate_preserve_order(["x", "x", "x"]) == ["x"]
