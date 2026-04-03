"""
alerts.py
---------
Threshold-based alerting for CPU and memory usage.
Alerts are emitted as structured objects so callers can display or log them.
"""

import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Alert:
    timestamp: float           # Unix timestamp when alert was raised
    kind: str                  # 'cpu' | 'memory'
    current_value: float       # Measured value that triggered alert
    threshold: float           # Configured threshold
    message: str               # Human-readable description

    @property
    def timestamp_str(self) -> str:
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.timestamp))


class AlertManager:
    """
    Evaluates current metrics against configured thresholds and
    produces Alert objects when thresholds are exceeded.

    Implements a simple cooldown so the same alert isn't fired every
    refresh cycle (default: 30-second cooldown per alert type).
    """

    def __init__(
        self,
        cpu_threshold: Optional[float] = None,
        memory_threshold: Optional[float] = None,
        cooldown_seconds: float = 30.0,
    ):
        self.cpu_threshold = cpu_threshold
        self.memory_threshold = memory_threshold
        self.cooldown = cooldown_seconds

        # Track when each alert kind was last fired
        self._last_fired: dict[str, float] = {}

    def _should_fire(self, kind: str) -> bool:
        """Return True if cooldown has elapsed since the last alert of this kind."""
        last = self._last_fired.get(kind, 0.0)
        return (time.time() - last) >= self.cooldown

    def _record_fire(self, kind: str) -> None:
        self._last_fired[kind] = time.time()

    def check(self, cpu_percent: float, memory_percent: float) -> list[Alert]:
        """
        Evaluate current readings against thresholds.

        Args:
            cpu_percent:    Current CPU usage (0–100).
            memory_percent: Current memory usage (0–100).

        Returns:
            List of Alert objects (may be empty).
        """
        alerts: list[Alert] = []
        now = time.time()

        if (
            self.cpu_threshold is not None
            and cpu_percent >= self.cpu_threshold
            and self._should_fire("cpu")
        ):
            alerts.append(Alert(
                timestamp=now,
                kind="cpu",
                current_value=cpu_percent,
                threshold=self.cpu_threshold,
                message=(
                    f"CPU usage {cpu_percent:.1f}% exceeds threshold "
                    f"{self.cpu_threshold:.1f}%"
                ),
            ))
            self._record_fire("cpu")

        if (
            self.memory_threshold is not None
            and memory_percent >= self.memory_threshold
            and self._should_fire("memory")
        ):
            alerts.append(Alert(
                timestamp=now,
                kind="memory",
                current_value=memory_percent,
                threshold=self.memory_threshold,
                message=(
                    f"Memory usage {memory_percent:.1f}% exceeds threshold "
                    f"{self.memory_threshold:.1f}%"
                ),
            ))
            self._record_fire("memory")

        return alerts
