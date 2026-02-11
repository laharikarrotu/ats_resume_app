"""
Prometheus-compatible metrics — lightweight, zero-dependency implementation.

Provides request counters, latency histograms, and business metrics
without requiring the prometheus_client library.

Metrics are exposed at GET /metrics in Prometheus text format.

Usage:
    from src.metrics import metrics
    metrics.inc("resume_uploads_total")
    metrics.observe("llm_latency_seconds", 1.23)
"""

import time
import threading
from collections import defaultdict
from typing import Dict, List, Optional


class MetricsCollector:
    """Thread-safe in-memory metrics collector with Prometheus text export."""

    def __init__(self):
        self._lock = threading.Lock()
        self._counters: Dict[str, float] = defaultdict(float)
        self._counter_labels: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, List[float]] = defaultdict(list)
        self._histogram_max_samples = 1000  # Rolling window

    # ── Counters ──────────────────────────────────────

    def inc(self, name: str, value: float = 1, labels: Optional[Dict[str, str]] = None) -> None:
        """Increment a counter."""
        with self._lock:
            if labels:
                label_key = ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))
                self._counter_labels[name][label_key] += value
            else:
                self._counters[name] += value

    # ── Gauges ────────────────────────────────────────

    def set_gauge(self, name: str, value: float) -> None:
        """Set a gauge to a specific value."""
        with self._lock:
            self._gauges[name] = value

    def inc_gauge(self, name: str, value: float = 1) -> None:
        """Increment a gauge."""
        with self._lock:
            self._gauges[name] = self._gauges.get(name, 0) + value

    def dec_gauge(self, name: str, value: float = 1) -> None:
        """Decrement a gauge."""
        with self._lock:
            self._gauges[name] = self._gauges.get(name, 0) - value

    # ── Histograms ────────────────────────────────────

    def observe(self, name: str, value: float) -> None:
        """Record an observation for a histogram."""
        with self._lock:
            samples = self._histograms[name]
            samples.append(value)
            # Rolling window — keep last N samples
            if len(samples) > self._histogram_max_samples:
                self._histograms[name] = samples[-self._histogram_max_samples:]

    # ── Timer Context Manager ─────────────────────────

    class _Timer:
        """Context manager for timing code blocks."""
        def __init__(self, collector: "MetricsCollector", name: str):
            self._collector = collector
            self._name = name
            self._start = 0.0

        def __enter__(self):
            self._start = time.perf_counter()
            return self

        def __exit__(self, *args):
            duration = time.perf_counter() - self._start
            self._collector.observe(self._name, duration)

    def timer(self, name: str) -> _Timer:
        """Return a context manager that times a block and records it as a histogram."""
        return self._Timer(self, name)

    # ── Export ────────────────────────────────────────

    def to_prometheus(self) -> str:
        """Export all metrics in Prometheus text exposition format."""
        lines: List[str] = []

        with self._lock:
            # Counters (simple)
            for name, value in sorted(self._counters.items()):
                lines.append(f"# TYPE {name} counter")
                lines.append(f"{name} {value}")

            # Counters (with labels)
            for name, label_values in sorted(self._counter_labels.items()):
                lines.append(f"# TYPE {name} counter")
                for label_key, value in sorted(label_values.items()):
                    lines.append(f"{name}{{{label_key}}} {value}")

            # Gauges
            for name, value in sorted(self._gauges.items()):
                lines.append(f"# TYPE {name} gauge")
                lines.append(f"{name} {value}")

            # Histograms (summary-style: count, sum, avg, p50, p95, p99)
            for name, samples in sorted(self._histograms.items()):
                if not samples:
                    continue
                sorted_samples = sorted(samples)
                count = len(sorted_samples)
                total = sum(sorted_samples)
                avg = total / count
                p50 = sorted_samples[int(count * 0.5)]
                p95 = sorted_samples[min(int(count * 0.95), count - 1)]
                p99 = sorted_samples[min(int(count * 0.99), count - 1)]

                lines.append(f"# TYPE {name} summary")
                lines.append(f'{name}_count {count}')
                lines.append(f'{name}_sum {total:.6f}')
                lines.append(f'{name}{{quantile="0.5"}} {p50:.6f}')
                lines.append(f'{name}{{quantile="0.95"}} {p95:.6f}')
                lines.append(f'{name}{{quantile="0.99"}} {p99:.6f}')

        lines.append("")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        """Export metrics as a Python dict (for JSON endpoints)."""
        with self._lock:
            result = {
                "counters": dict(self._counters),
                "gauges": dict(self._gauges),
                "histograms": {},
            }

            for name, samples in self._histograms.items():
                if not samples:
                    continue
                sorted_samples = sorted(samples)
                count = len(sorted_samples)
                total = sum(sorted_samples)
                result["histograms"][name] = {
                    "count": count,
                    "sum": round(total, 4),
                    "avg": round(total / count, 4),
                    "p50": round(sorted_samples[int(count * 0.5)], 4),
                    "p95": round(sorted_samples[min(int(count * 0.95), count - 1)], 4),
                    "p99": round(sorted_samples[min(int(count * 0.99), count - 1)], 4),
                }

            # Add labeled counters
            for name, label_values in self._counter_labels.items():
                result["counters"][name] = dict(label_values)

            return result

    def reset(self) -> None:
        """Reset all metrics (for testing)."""
        with self._lock:
            self._counters.clear()
            self._counter_labels.clear()
            self._gauges.clear()
            self._histograms.clear()


# ── Module-level singleton ──

metrics = MetricsCollector()
