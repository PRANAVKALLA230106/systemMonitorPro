"""
process_stats.py
----------------
Collects and ranks running process information using psutil.
Handles permission errors gracefully for protected system processes.
"""

import psutil
from dataclasses import dataclass
from typing import Literal, Optional


# Attributes fetched in one shot to minimise race conditions (process may die)
_PROC_ATTRS = ["pid", "name", "cpu_percent", "memory_percent", "status", "username"]

SortKey = Literal["cpu", "memory"]


@dataclass
class ProcessInfo:
    pid: int
    name: str
    cpu_percent: float
    memory_percent: float
    status: str
    username: str


def _safe_proc_info(proc: psutil.Process) -> Optional[ProcessInfo]:
    """
    Attempt to extract ProcessInfo from a psutil.Process object.
    Returns None if the process has terminated or access is denied.
    """
    try:
        info = proc.as_dict(attrs=_PROC_ATTRS)
        return ProcessInfo(
            pid=info["pid"],
            name=info["name"] or "<unknown>",
            cpu_percent=info.get("cpu_percent") or 0.0,
            memory_percent=round(info.get("memory_percent") or 0.0, 3),
            status=info.get("status") or "?",
            username=info.get("username") or "?",
        )
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        # These are expected; skip silently
        return None
    except Exception:
        return None


def get_top_processes(top_n: int = 10, sort_by: SortKey = "cpu") -> list[ProcessInfo]:
    """
    Return the top N processes ranked by CPU or memory usage.

    Args:
        top_n:   Number of processes to return.
        sort_by: Ranking key — 'cpu' or 'memory'.

    Returns:
        Sorted list of ProcessInfo objects (descending order).
    """
    # First pass: call cpu_percent with interval=None to initialise counters.
    # psutil requires processes to be seen twice for accurate CPU %.
    processes: list[ProcessInfo] = []

    for proc in psutil.process_iter(_PROC_ATTRS):
        info = _safe_proc_info(proc)
        if info is not None:
            processes.append(info)

    sort_attr = "cpu_percent" if sort_by == "cpu" else "memory_percent"
    processes.sort(key=lambda p: getattr(p, sort_attr), reverse=True)

    return processes[:top_n]


def get_process_count() -> int:
    """Return total number of running processes."""
    try:
        return len(list(psutil.process_iter()))
    except Exception:
        return 0
