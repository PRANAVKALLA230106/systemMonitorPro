"""
display.py
----------
Terminal rendering engine with two modes:
  • Rich mode  — uses the `rich` library for a polished dashboard (preferred).
  • ANSI mode  — pure stdlib fallback using ANSI escape codes (no dependencies).

The correct mode is selected automatically at import time based on
whether `rich` is installed.
"""

import os
import platform
import sys
import time
from typing import Optional

from system_stats import CPUStats, MemoryStats
from process_stats import ProcessInfo
from alerts import Alert

# ── Detect rich availability ──────────────────────────────────────────────────

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.columns import Columns
    from rich.text import Text
    from rich.rule import Rule
    from rich import box
    _RICH_AVAILABLE = True
    console = Console()
except ImportError:
    _RICH_AVAILABLE = False
    console = None  # type: ignore[assignment]


# ═════════════════════════════════════════════════════════════════════════════
# Shared helpers
# ═════════════════════════════════════════════════════════════════════════════

def _get_term_width() -> int:
    try:
        return os.get_terminal_size().columns
    except OSError:
        return 100


# ═════════════════════════════════════════════════════════════════════════════
# ANSI fallback renderer (stdlib only)
# ═════════════════════════════════════════════════════════════════════════════

class _A:
    """Minimal ANSI colour / cursor helpers."""
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    DIM     = "\033[2m"
    RED     = "\033[91m"
    YELLOW  = "\033[93m"
    GREEN   = "\033[92m"
    CYAN    = "\033[96m"
    MAGENTA = "\033[95m"
    WHITE   = "\033[97m"
    GREY    = "\033[90m"

    @staticmethod
    def pct_color(pct: float) -> str:
        if pct >= 85:
            return _A.RED + _A.BOLD
        if pct >= 60:
            return _A.YELLOW + _A.BOLD
        return _A.GREEN + _A.BOLD

    @staticmethod
    def bar(pct: float, width: int = 20) -> str:
        filled = int(pct / 100 * width)
        col = _A.pct_color(pct)
        return col + "█" * filled + _A.DIM + "░" * (width - filled) + _A.RESET


def _ansi_render(
    cpu: CPUStats,
    memory: MemoryStats,
    processes: list[ProcessInfo],
    alerts: list[Alert],
    interval: float,
    top_n: int,
    sort_by: str,
    proc_count: int,
    log_path: Optional[str],
) -> None:
    """Full-screen ANSI render — no external dependencies."""
    W = _get_term_width()
    out: list[str] = []

    def rule(char: str = "─") -> None:
        out.append(_A.GREY + char * W + _A.RESET)

    def section(title: str) -> None:
        out.append(_A.BOLD + _A.CYAN + f" {title}" + _A.RESET)
        rule()

    # ── Header ────────────────────────────────────────────────────────────────
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    log_str = f"  logging→{log_path}" if log_path else ""
    out.append(
        _A.BOLD + _A.WHITE + f" {platform.node()}" + _A.RESET
        + _A.GREY + f"  {platform.system()} {platform.release()}  " + _A.RESET
        + _A.CYAN + ts + _A.RESET
        + _A.GREY + f"  interval={interval}s  top={top_n}  procs={proc_count}{log_str}" + _A.RESET
    )
    rule("═")

    # ── CPU ───────────────────────────────────────────────────────────────────
    section("⚙  CPU")
    col = _A.pct_color(cpu.percent)
    out.append(f"  {'Overall':<8} {_A.bar(cpu.percent)}  {col}{cpu.percent:5.1f}%{_A.RESET}")
    if cpu.per_core:
        for i, c in enumerate(cpu.per_core):
            out.append(f"  {'Core '+str(i):<8} {_A.bar(c, 16)}  {_A.pct_color(c)}{c:5.1f}%{_A.RESET}")
    freq = f"{cpu.frequency_mhz:.0f} MHz" if cpu.frequency_mhz else "N/A"
    out.append(_A.GREY + f"  Cores: {cpu.core_count}   Frequency: {freq}" + _A.RESET)
    out.append("")

    # ── Memory ────────────────────────────────────────────────────────────────
    section("🧠 Memory")
    out.append(
        f"  {'RAM':<8} {_A.bar(memory.percent)}  "
        f"{_A.pct_color(memory.percent)}{memory.percent:5.1f}%{_A.RESET}  "
        f"{_A.GREY}{memory.used_gb:.1f} / {memory.total_gb:.1f} GB{_A.RESET}"
    )
    if memory.swap_total_gb > 0:
        out.append(
            f"  {'Swap':<8} {_A.bar(memory.swap_percent)}  "
            f"{_A.pct_color(memory.swap_percent)}{memory.swap_percent:5.1f}%{_A.RESET}  "
            f"{_A.GREY}{memory.swap_used_gb:.1f} / {memory.swap_total_gb:.1f} GB{_A.RESET}"
        )
    out.append(_A.GREY + f"  Available: {memory.available_gb:.2f} GB" + _A.RESET)
    out.append("")

    # ── Alerts ────────────────────────────────────────────────────────────────
    if alerts:
        rule()
        out.append(_A.RED + _A.BOLD + " 🚨 ALERTS" + _A.RESET)
        rule()
        for a in alerts:
            out.append(_A.RED + _A.BOLD + f"  ⚠  [{a.timestamp_str}]  {a.message}" + _A.RESET)
        out.append("")

    # ── Processes ─────────────────────────────────────────────────────────────
    sort_label = "CPU%" if sort_by == "cpu" else "MEM%"
    section(f"📋 Top {top_n} Processes  (sorted by {sort_label})")
    out.append(
        _A.BOLD + _A.WHITE
        + f"  {'PID':>7}  {'NAME':<22}  {'STATUS':<10}  {'USER':<12}  {'CPU%':>7}  {'MEM%':>7}"
        + _A.RESET
    )
    rule()

    for proc in processes:
        status_col = {"running": _A.GREEN, "sleeping": _A.GREY,
                      "zombie": _A.RED, "stopped": _A.YELLOW}.get(proc.status.lower(), _A.WHITE)
        out.append(
            f"  {proc.pid:>7}  {proc.name[:22]:<22}  "
            f"{status_col}{proc.status:<10}{_A.RESET}  "
            f"{_A.GREY}{proc.username[:12]:<12}{_A.RESET}  "
            f"{_A.pct_color(proc.cpu_percent)}{proc.cpu_percent:>7.2f}{_A.RESET}  "
            f"{_A.pct_color(proc.memory_percent * 5)}{proc.memory_percent:>7.3f}{_A.RESET}"
        )

    out.append("")
    out.append(_A.GREY + "  Press Ctrl+C to exit" + _A.RESET)

    # Flush entire frame atomically to reduce flicker
    sys.stdout.write("\033c")          # clear terminal
    sys.stdout.write("\n".join(out) + "\n")
    sys.stdout.flush()


# ═════════════════════════════════════════════════════════════════════════════
# Rich renderer (preferred when `rich` is installed)
# ═════════════════════════════════════════════════════════════════════════════

def _rich_pct_color(pct: float) -> str:
    if pct >= 85:
        return "bold red"
    if pct >= 60:
        return "bold yellow"
    return "bold green"


def _rich_bar(pct: float, width: int = 20) -> "Text":  # type: ignore[name-defined]
    filled = int(pct / 100 * width)
    t = Text("█" * filled + "░" * (width - filled), style=_rich_pct_color(pct))
    return t


def _rich_render(
    cpu: CPUStats,
    memory: MemoryStats,
    processes: list[ProcessInfo],
    alerts: list[Alert],
    interval: float,
    top_n: int,
    sort_by: str,
    proc_count: int,
    log_path: Optional[str],
) -> None:
    console.clear()

    # Header
    log_str = f"  [dim]● logging → {log_path}[/]" if log_path else ""
    console.print(Text.from_markup(
        f"[bold white]{platform.node()}[/]  "
        f"[dim]{platform.system()} {platform.release()}[/]   "
        f"[cyan]{time.strftime('%Y-%m-%d  %H:%M:%S')}[/]   "
        f"[dim]interval={interval}s  top={top_n}  procs={proc_count}[/]{log_str}"
    ))
    console.print(Rule(style="grey23"))

    # CPU panel
    ct = Text()
    ct.append("  Overall  ", style="dim")
    ct.append(_rich_bar(cpu.percent))
    ct.append(f"  {cpu.percent:5.1f}%\n", style=_rich_pct_color(cpu.percent))
    for i, c in enumerate(cpu.per_core or []):
        ct.append(f"  Core {i:<3} ", style="dim")
        ct.append(_rich_bar(c, 16))
        ct.append(f"  {c:5.1f}%\n", style=_rich_pct_color(c))
    freq = f"{cpu.frequency_mhz:.0f} MHz" if cpu.frequency_mhz else "N/A"
    ct.append(f"\n  Cores: {cpu.core_count}   Freq: {freq}", style="dim")
    cpu_panel = Panel(ct, title="[bold cyan]⚙  CPU[/]", border_style="cyan", padding=(0, 1))

    # Memory panel
    mt = Text()
    mt.append("  RAM      ", style="dim")
    mt.append(_rich_bar(memory.percent))
    mt.append(f"  {memory.percent:5.1f}%   {memory.used_gb:.1f} / {memory.total_gb:.1f} GB\n",
               style=_rich_pct_color(memory.percent))
    if memory.swap_total_gb > 0:
        mt.append("  Swap     ", style="dim")
        mt.append(_rich_bar(memory.swap_percent))
        mt.append(f"  {memory.swap_percent:5.1f}%   {memory.swap_used_gb:.1f} / {memory.swap_total_gb:.1f} GB\n",
                   style=_rich_pct_color(memory.swap_percent))
    mt.append(f"\n  Available: {memory.available_gb:.2f} GB", style="dim")
    mem_panel = Panel(mt, title="[bold magenta]🧠 Memory[/]", border_style="magenta", padding=(0, 1))

    console.print(Columns([cpu_panel, mem_panel], equal=True, expand=True))

    # Alerts
    if alerts:
        at = Text()
        for a in alerts:
            at.append(f"  ⚠  [{a.timestamp_str}]  {a.message}\n", style="bold red")
        console.print(Panel(at, title="[bold red]🚨 ALERTS[/]", border_style="red", padding=(0, 1)))

    # Process table
    sort_label = "CPU %" if sort_by == "cpu" else "MEM %"
    tbl = Table(box=box.SIMPLE_HEAD, show_header=True, header_style="bold white on grey23",
                row_styles=["", "dim"], expand=True)
    tbl.add_column("PID", style="cyan", width=8, justify="right")
    tbl.add_column("Name", style="white", min_width=20, max_width=32, no_wrap=True)
    tbl.add_column("Status", width=10)
    tbl.add_column("User", style="dim", width=12, no_wrap=True)
    tbl.add_column(f"CPU %{'▼' if sort_by=='cpu' else '':>2}", justify="right", width=10)
    tbl.add_column(f"MEM %{'▼' if sort_by=='memory' else '':>2}", justify="right", width=10)

    for proc in processes:
        sc = {"running": "green", "sleeping": "dim", "zombie": "red", "stopped": "yellow"}
        tbl.add_row(
            str(proc.pid), proc.name,
            Text(proc.status, style=sc.get(proc.status.lower(), "white")),
            proc.username[:12],
            Text(f"{proc.cpu_percent:6.2f}", style=_rich_pct_color(proc.cpu_percent)),
            Text(f"{proc.memory_percent:6.3f}", style=_rich_pct_color(proc.memory_percent * 5)),
        )

    console.print(Panel(tbl, title=f"[bold yellow]📋 Processes[/] [dim](sorted by {sort_label})[/]",
                        border_style="yellow", padding=(0, 1)))
    console.print("[dim]  Press Ctrl+C to exit[/]", justify="right")


# ═════════════════════════════════════════════════════════════════════════════
# Public API — called from monitor.py
# ═════════════════════════════════════════════════════════════════════════════

def render_frame(
    cpu: CPUStats,
    memory: MemoryStats,
    processes: list[ProcessInfo],
    alerts: list[Alert],
    interval: float,
    top_n: int,
    sort_by: str,
    proc_count: int,
    log_path: Optional[str] = None,
) -> None:
    """
    Clear the terminal and render a complete dashboard frame.
    Automatically chooses rich or ANSI rendering based on availability.
    """
    if _RICH_AVAILABLE:
        _rich_render(cpu, memory, processes, alerts, interval, top_n, sort_by, proc_count, log_path)
    else:
        _ansi_render(cpu, memory, processes, alerts, interval, top_n, sort_by, proc_count, log_path)
