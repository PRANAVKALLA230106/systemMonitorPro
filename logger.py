"""
logger.py
---------
Handles optional file-based logging of system metrics.
Writes structured JSON-lines (one JSON object per line) for easy parsing.
"""

import json
import os
import time
from pathlib import Path
from typing import Optional

from system_stats import CPUStats, MemoryStats
from process_stats import ProcessInfo
from alerts import Alert


class StatsLogger:
    """
    Appends time-stamped metric snapshots to a JSON-lines log file.

    Each line is a self-contained JSON record covering system stats,
    top processes, and any active alerts — making it trivial to parse
    with jq, pandas, or a log aggregator.
    """

    def __init__(self, log_path: str):
        self.log_path = Path(log_path)
        self._ensure_file()

    def _ensure_file(self) -> None:
        """Create the log file (and parent dirs) if they don't exist."""
        try:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            if not self.log_path.exists():
                self.log_path.touch()
        except OSError as e:
            raise RuntimeError(
                f"Cannot create log file at '{self.log_path}': {e}"
            ) from e

    def write(
        self,
        cpu: CPUStats,
        memory: MemoryStats,
        processes: list[ProcessInfo],
        alerts: list[Alert],
    ) -> None:
        """
        Append a single JSON record to the log file.

        Args:
            cpu:       Current CPU statistics.
            memory:    Current memory statistics.
            processes: Top-N process list at this snapshot.
            alerts:    Any alerts triggered this cycle.
        """
        record = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "cpu": {
                "percent": cpu.percent,
                "per_core": cpu.per_core,
                "frequency_mhz": cpu.frequency_mhz,
                "core_count": cpu.core_count,
            },
            "memory": {
                "total_gb": memory.total_gb,
                "used_gb": memory.used_gb,
                "available_gb": memory.available_gb,
                "percent": memory.percent,
                "swap_total_gb": memory.swap_total_gb,
                "swap_used_gb": memory.swap_used_gb,
                "swap_percent": memory.swap_percent,
            },
            "top_processes": [
                {
                    "pid": p.pid,
                    "name": p.name,
                    "cpu_percent": p.cpu_percent,
                    "memory_percent": p.memory_percent,
                    "status": p.status,
                    "username": p.username,
                }
                for p in processes
            ],
            "alerts": [
                {
                    "kind": a.kind,
                    "current_value": a.current_value,
                    "threshold": a.threshold,
                    "message": a.message,
                }
                for a in alerts
            ],
        }

        try:
            with self.log_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(record) + "\n")
        except OSError as e:
            # Log write failure shouldn't crash the monitor; just warn stderr
            import sys
            print(f"[logger] WARNING: Could not write to log: {e}", file=sys.stderr)
