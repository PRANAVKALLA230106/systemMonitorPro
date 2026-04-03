"""
system_stats.py
---------------
Collects CPU and memory statistics using psutil.
Provides structured dataclasses for clean data passing across modules.
"""

import psutil
import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class CPUStats:
    percent: float                  # Overall CPU usage %
    per_core: list[float]           # Per-core usage percentages
    frequency_mhz: Optional[float]  # Current CPU frequency
    core_count: int                 # Logical CPU count


@dataclass
class MemoryStats:
    total_gb: float        # Total RAM in GB
    used_gb: float         # Used RAM in GB
    available_gb: float    # Available RAM in GB
    percent: float         # Usage percentage
    swap_total_gb: float   # Swap total in GB
    swap_used_gb: float    # Swap used in GB
    swap_percent: float    # Swap usage percentage


def get_cpu_stats(interval: float = 0.1) -> CPUStats:
    """
    Retrieve current CPU usage stats.

    Args:
        interval: Sampling interval for per-CPU measurement (seconds).

    Returns:
        CPUStats dataclass populated with current readings.
    """
    try:
        percent = psutil.cpu_percent(interval=interval)
        per_core = psutil.cpu_percent(percpu=True)
        freq = psutil.cpu_freq()
        frequency_mhz = freq.current if freq else None
        core_count = psutil.cpu_count(logical=True)
    except Exception as e:
        # Fallback to safe defaults if psutil call fails
        percent = 0.0
        per_core = []
        frequency_mhz = None
        core_count = 1

    return CPUStats(
        percent=percent,
        per_core=per_core,
        frequency_mhz=frequency_mhz,
        core_count=core_count,
    )


def get_memory_stats() -> MemoryStats:
    """
    Retrieve current virtual memory and swap stats.

    Returns:
        MemoryStats dataclass with GB-converted values.
    """
    def to_gb(bytes_val: int) -> float:
        return round(bytes_val / (1024 ** 3), 2)

    try:
        vm = psutil.virtual_memory()
        sw = psutil.swap_memory()
    except Exception:
        # Should rarely fail; return zeroed struct on error
        return MemoryStats(0, 0, 0, 0.0, 0, 0, 0.0)

    return MemoryStats(
        total_gb=to_gb(vm.total),
        used_gb=to_gb(vm.used),
        available_gb=to_gb(vm.available),
        percent=vm.percent,
        swap_total_gb=to_gb(sw.total),
        swap_used_gb=to_gb(sw.used),
        swap_percent=sw.percent,
    )
