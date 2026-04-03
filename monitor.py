"""
monitor.py
----------
CLI entry point for sysmon — a real-time system monitoring tool.

Usage:
    python monitor.py [OPTIONS]

Options:
    --interval      Refresh rate in seconds (default: 1)
    --top           Number of top processes to display (default: 5)
    --sort          Sort processes by 'cpu' or 'memory' (default: cpu)
    --log           Path to write JSON-lines log file
    --alert-cpu     CPU usage % threshold for alerts
    --alert-memory  Memory usage % threshold for alerts

Example:
    python monitor.py --interval 2 --top 10 --sort memory --alert-cpu 80 --log /tmp/sysmon.log
"""

import argparse
import sys
import time
from typing import Optional

# Local modules
from system_stats import get_cpu_stats, get_memory_stats
from process_stats import get_top_processes, get_process_count
from alerts import AlertManager
from logger import StatsLogger
from display import render_frame, console


# ── Argument parsing ──────────────────────────────────────────────────────────

def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sysmon",
        description="Real-time system monitor — a lightweight htop in Python.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=1.0,
        metavar="SECONDS",
        help="Refresh rate in seconds (default: 1)",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=5,
        metavar="N",
        help="Number of top processes to display (default: 5)",
    )
    parser.add_argument(
        "--sort",
        choices=["cpu", "memory"],
        default="cpu",
        help="Sort processes by 'cpu' or 'memory' (default: cpu)",
    )
    parser.add_argument(
        "--log",
        type=str,
        default=None,
        metavar="FILE",
        help="Path to write JSON-lines log file",
    )
    parser.add_argument(
        "--alert-cpu",
        type=float,
        default=None,
        metavar="PCT",
        dest="alert_cpu",
        help="Alert when CPU usage exceeds this %% (e.g. 80)",
    )
    parser.add_argument(
        "--alert-memory",
        type=float,
        default=None,
        metavar="PCT",
        dest="alert_memory",
        help="Alert when memory usage exceeds this %% (e.g. 75)",
    )
    return parser


def validate_args(args: argparse.Namespace) -> None:
    """Validate CLI arguments and exit with a helpful message on failure."""
    if args.interval <= 0:
        sys.exit("Error: --interval must be a positive number.")
    if args.top < 1:
        sys.exit("Error: --top must be at least 1.")
    if args.alert_cpu is not None and not (0 < args.alert_cpu <= 100):
        sys.exit("Error: --alert-cpu must be between 1 and 100.")
    if args.alert_memory is not None and not (0 < args.alert_memory <= 100):
        sys.exit("Error: --alert-memory must be between 1 and 100.")


# ── Main monitoring loop ──────────────────────────────────────────────────────

def run(args: argparse.Namespace) -> None:
    """
    Main event loop.

    1. Collect CPU, memory, and process data via psutil.
    2. Evaluate alert thresholds.
    3. Optionally write a log entry.
    4. Render the terminal dashboard.
    5. Sleep until next interval.
    """
    alert_manager = AlertManager(
        cpu_threshold=args.alert_cpu,
        memory_threshold=args.alert_memory,
        cooldown_seconds=max(args.interval, 30.0),
    )

    logger: Optional[StatsLogger] = None
    if args.log:
        try:
            logger = StatsLogger(args.log)
            console.print(f"[green]Logging to:[/] {args.log}")
            time.sleep(0.5)
        except RuntimeError as e:
            sys.exit(str(e))

    # Warm-up: psutil needs one cycle to initialise CPU counters accurately
    get_cpu_stats(interval=0.2)

    try:
        while True:
            loop_start = time.monotonic()

            # ── Collect ────────────────────────────────────────────────────
            cpu = get_cpu_stats(interval=0.1)
            memory = get_memory_stats()
            processes = get_top_processes(top_n=args.top, sort_by=args.sort)
            proc_count = get_process_count()

            # ── Alerts ─────────────────────────────────────────────────────
            alerts = alert_manager.check(cpu.percent, memory.percent)

            # ── Log ────────────────────────────────────────────────────────
            if logger:
                logger.write(cpu, memory, processes, alerts)

            # ── Render ─────────────────────────────────────────────────────
            render_frame(
                cpu=cpu,
                memory=memory,
                processes=processes,
                alerts=alerts,
                interval=args.interval,
                top_n=args.top,
                sort_by=args.sort,
                proc_count=proc_count,
                log_path=args.log,
            )

            # ── Sleep (account for collection time) ────────────────────────
            elapsed = time.monotonic() - loop_start
            sleep_for = max(0.0, args.interval - elapsed)
            time.sleep(sleep_for)

    except KeyboardInterrupt:
        # Graceful Ctrl+C exit — no traceback spam
        console.print("\n[bold yellow]sysmon exited.[/]  Goodbye 👋\n")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[bold red]Fatal error:[/] {e}")
        sys.exit(1)


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()
    validate_args(args)
    run(args)


if __name__ == "__main__":
    main()
