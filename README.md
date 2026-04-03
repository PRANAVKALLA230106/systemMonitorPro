# sysmon 🖥️

A production-quality, real-time system monitoring tool built in Python — think `htop`, but lightweight and fully Pythonic.

---

## Features

- **Real-time CPU usage** — overall + per-core, with frequency
- **Real-time memory usage** — RAM and swap (used / available / %)
- **Top-N process table** — PID, name, status, user, CPU%, MEM%
- **Colour-coded output** — green → yellow → red traffic-light system
- **Configurable alerts** — threshold-based warnings for CPU and memory
- **JSON-lines logging** — structured, timestamped log file
- **Auto-detects `rich`** — polished panels when installed, clean ANSI fallback otherwise
- **Graceful Ctrl+C exit** — no traceback spam
- **Cross-platform** — Linux, macOS, Windows (Windows colours require a modern terminal)

---

## Project Structure

```
sysmon/
├── monitor.py        # CLI entry point — argument parsing & main loop
├── system_stats.py   # CPU and memory data collection (psutil)
├── process_stats.py  # Process enumeration and ranking
├── alerts.py         # Threshold alerting with cooldown logic
├── logger.py         # JSON-lines file logging
├── display.py        # Terminal rendering (rich + ANSI fallback)
├── requirements.txt  # Python dependencies
└── README.md
```

---

## Installation

### 1. Clone / download

```bash
git clone https://github.com/you/sysmon.git
cd sysmon
```

### 2. Create a virtual environment (recommended)

```bash
python3 -m venv .venv
source .venv/bin/activate        # Linux / macOS
.venv\Scripts\activate           # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

`psutil` is required. `rich` is **optional** — if not installed, the tool
falls back to clean ANSI colour output with no loss of functionality.

---

## Usage

```bash
python monitor.py [OPTIONS]
```

| Flag              | Default | Description                                      |
|-------------------|---------|--------------------------------------------------|
| `--interval N`    | `1`     | Refresh rate in seconds                          |
| `--top N`         | `5`     | Number of top processes to show                  |
| `--sort KEY`      | `cpu`   | Sort processes by `cpu` or `memory`              |
| `--log FILE`      | _(none)_| Write JSON-lines log to this path                |
| `--alert-cpu N`   | _(none)_| Alert when CPU usage exceeds N%                  |
| `--alert-memory N`| _(none)_| Alert when memory usage exceeds N%               |

### Examples

```bash
# Basic monitor, refresh every second, show top 5 by CPU
python monitor.py

# Show top 10 processes sorted by memory, refresh every 2 seconds
python monitor.py --interval 2 --top 10 --sort memory

# Full setup: alerts + logging
python monitor.py --interval 1 --top 10 --sort cpu \
  --alert-cpu 80 --alert-memory 75 \
  --log /var/log/sysmon.jsonl
```

---

## Log Format

Each line in the log file is a self-contained JSON record:

```json
{
  "timestamp": "2025-04-03T14:22:01",
  "cpu": {
    "percent": 43.2,
    "per_core": [51.0, 35.4],
    "frequency_mhz": 2400.0,
    "core_count": 2
  },
  "memory": {
    "total_gb": 16.0,
    "used_gb": 8.3,
    "available_gb": 7.7,
    "percent": 51.8,
    "swap_total_gb": 2.0,
    "swap_used_gb": 0.1,
    "swap_percent": 5.0
  },
  "top_processes": [
    {"pid": 1234, "name": "python3", "cpu_percent": 38.2,
     "memory_percent": 2.1, "status": "running", "username": "alice"}
  ],
  "alerts": [
    {"kind": "cpu", "current_value": 43.2, "threshold": 40.0,
     "message": "CPU usage 43.2% exceeds threshold 40.0%"}
  ]
}
```

Parse logs with `jq`:

```bash
# Last 10 CPU readings
tail -10 sysmon.jsonl | jq '.cpu.percent'

# All alerts
grep -v '"alerts": \[\]' sysmon.jsonl | jq '.alerts[]'
```

---

## Alert Cooldown

Alerts fire at most once every **30 seconds** per metric type (or once per
`--interval` if that's longer) to avoid flooding the terminal or log.

---

## Requirements

```
psutil>=5.9.0   # required
rich>=13.0.0    # optional (ANSI fallback used if absent)
```

---

## Extending

| Task                          | File to edit       |
|-------------------------------|--------------------|
| Add disk I/O stats            | `system_stats.py`  |
| Add network throughput        | `system_stats.py`  |
| Add per-process thread count  | `process_stats.py` |
| Change alert cooldown         | `alerts.py`        |
| Change log format to CSV      | `logger.py`        |
| Customise display layout      | `display.py`       |
