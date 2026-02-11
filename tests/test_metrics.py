"""Tests for Prometheus-compatible metrics."""

import pytest
from src.metrics import MetricsCollector


@pytest.fixture()
def collector():
    """Fresh metrics collector for each test."""
    return MetricsCollector()


class TestCounters:
    def test_increment(self, collector):
        collector.inc("test_counter")
        collector.inc("test_counter")
        collector.inc("test_counter", 3)
        assert collector._counters["test_counter"] == 5

    def test_labeled_counter(self, collector):
        collector.inc("requests", labels={"method": "GET", "status": "200"})
        collector.inc("requests", labels={"method": "GET", "status": "200"})
        collector.inc("requests", labels={"method": "POST", "status": "201"})
        assert len(collector._counter_labels["requests"]) == 2


class TestGauges:
    def test_set(self, collector):
        collector.set_gauge("active_connections", 42)
        assert collector._gauges["active_connections"] == 42

    def test_inc_dec(self, collector):
        collector.set_gauge("queue_size", 10)
        collector.inc_gauge("queue_size", 5)
        assert collector._gauges["queue_size"] == 15
        collector.dec_gauge("queue_size", 3)
        assert collector._gauges["queue_size"] == 12


class TestHistograms:
    def test_observe(self, collector):
        for v in [0.1, 0.2, 0.3, 0.5, 1.0]:
            collector.observe("response_time", v)
        assert len(collector._histograms["response_time"]) == 5

    def test_rolling_window(self, collector):
        collector._histogram_max_samples = 10
        for i in range(20):
            collector.observe("test_hist", float(i))
        assert len(collector._histograms["test_hist"]) == 10


class TestTimer:
    def test_timer(self, collector):
        import time
        with collector.timer("test_timer"):
            time.sleep(0.01)
        assert len(collector._histograms["test_timer"]) == 1
        assert collector._histograms["test_timer"][0] >= 0.01


class TestExport:
    def test_prometheus_format(self, collector):
        collector.inc("http_requests_total", 5)
        collector.set_gauge("active_sessions", 3)
        collector.observe("latency_seconds", 0.5)

        output = collector.to_prometheus()
        assert "http_requests_total 5" in output
        assert "active_sessions 3" in output
        assert "latency_seconds_count 1" in output

    def test_dict_export(self, collector):
        collector.inc("counter_a", 10)
        collector.set_gauge("gauge_b", 20)
        collector.observe("hist_c", 0.5)

        data = collector.to_dict()
        assert data["counters"]["counter_a"] == 10
        assert data["gauges"]["gauge_b"] == 20
        assert data["histograms"]["hist_c"]["count"] == 1

    def test_empty_export(self, collector):
        output = collector.to_prometheus()
        assert output.strip() == ""


class TestReset:
    def test_reset(self, collector):
        collector.inc("x", 5)
        collector.set_gauge("y", 10)
        collector.observe("z", 1.0)
        collector.reset()
        assert len(collector._counters) == 0
        assert len(collector._gauges) == 0
        assert len(collector._histograms) == 0
