"""Persistent WAN byte accounting using Linux network-interface counters.

RX on the WAN interface is treated as download; TX is treated as upload.
This is router-measured traffic, not an ISP billing meter.
"""
from __future__ import annotations
import argparse
import os
import re
import sqlite3
import subprocess
import time
from dataclasses import asdict, dataclass
from datetime import date, datetime, time as datetime_time, timedelta
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

DEFAULT_DB = "/etc/cubie-a5e-telegram-bot/traffic.sqlite3"
DEFAULT_MAX_GAP_SECONDS = 300

@dataclass(frozen=True)
class TrafficReport:
    period: str
    start: str
    end: str
    interface: str
    download_bytes: int
    upload_bytes: int
    complete: bool
    warnings: tuple[str, ...]

    @property
    def total_bytes(self) -> int:
        return self.download_bytes + self.upload_bytes

    def to_dict(self) -> dict:
        result = asdict(self)
        result["total_bytes"] = self.total_bytes
        return result

def detect_default_wan() -> str:
    """Return the interface used by the IPv4 default route."""
    try:
        output = subprocess.check_output(["ip", "-4", "route", "show", "default"],
            text=True, stderr=subprocess.DEVNULL, timeout=5)
    except (OSError, subprocess.SubprocessError) as exc:
        raise RuntimeError("Unable to detect WAN interface; set WAN_INTERFACE explicitly") from exc
    for line in output.splitlines():
        match = re.search(r"(?:^|\\s)dev\\s+([^\\s]+)", line)
        if match:
            return match.group(1)
    raise RuntimeError("No IPv4 default-route interface found; set WAN_INTERFACE explicitly")

def read_interface_counters(interface: str, sys_class_net: str = "/sys/class/net") -> tuple[int, int]:
    """Return (RX/download bytes, TX/upload bytes) from Linux sysfs."""
    if not re.fullmatch(r"[A-Za-z0-9_.:-]{1,64}", interface):
        raise ValueError("Invalid network interface name")
    base = Path(sys_class_net) / interface / "statistics"
    try:
        rx = int((base / "rx_bytes").read_text().strip())
        tx = int((base / "tx_bytes").read_text().strip())
    except (OSError, ValueError) as exc:
        raise RuntimeError("Unable to read counters for interface %s" % interface) from exc
    if rx < 0 or tx < 0:
        raise RuntimeError("Interface counters must not be negative")
    return rx, tx

class TrafficAccounting:
    """Store counter snapshots and interval deltas in a local SQLite database."""
    def __init__(self, database: str = DEFAULT_DB, timezone: str = "Asia/Dhaka",
                 max_gap_seconds: int = DEFAULT_MAX_GAP_SECONDS) -> None:
        if max_gap_seconds < 1:
            raise ValueError("max_gap_seconds must be positive")
        self.database = database
        self.tz = ZoneInfo(timezone)
        self.max_gap_seconds = max_gap_seconds
        Path(database).parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.database, timeout=15)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=15000")
        return conn

    def _initialize(self) -> None:
        with self._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL, interface TEXT NOT NULL,
                    rx_bytes INTEGER NOT NULL, tx_bytes INTEGER NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_snapshots_time ON snapshots(timestamp);
                CREATE TABLE IF NOT EXISTS intervals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    start_ts REAL NOT NULL, end_ts REAL NOT NULL,
                    interface TEXT NOT NULL, rx_delta INTEGER, tx_delta INTEGER,
                    valid INTEGER NOT NULL, reason TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_intervals_time ON intervals(start_ts, end_ts);
            """)

    def record_sample(self, interface: str, rx_bytes: int, tx_bytes: int,
                      timestamp: Optional[float] = None) -> dict:
        """Persist one sample; discontinuities are stored as invalid intervals."""
        if not re.fullmatch(r"[A-Za-z0-9_.:-]{1,64}", interface):
            raise ValueError("Invalid network interface name")
        if rx_bytes < 0 or tx_bytes < 0:
            raise ValueError("Counters must not be negative")
        now = float(time.time() if timestamp is None else timestamp)
        if now <= 0:
            raise ValueError("timestamp must be positive")
        with self._connect() as conn:
            previous = conn.execute(
                "SELECT timestamp,interface,rx_bytes,tx_bytes FROM snapshots ORDER BY timestamp DESC,id DESC LIMIT 1"
            ).fetchone()
            outcome = {"baseline": previous is None, "valid": False, "reason": None}
            if previous is not None:
                start = float(previous["timestamp"])
                elapsed = now - start
                reason = None
                if now <= start:
                    reason = "non_monotonic_time"
                elif previous["interface"] != interface:
                    reason = "interface_changed"
                elif elapsed > self.max_gap_seconds:
                    reason = "sampling_gap"
                elif rx_bytes < int(previous["rx_bytes"]) or tx_bytes < int(previous["tx_bytes"]):
                    reason = "counter_reset_or_wrap"
                if reason is None:
                    rx_delta = rx_bytes - int(previous["rx_bytes"])
                    tx_delta = tx_bytes - int(previous["tx_bytes"])
                    conn.execute(
                        "INSERT INTO intervals(start_ts,end_ts,interface,rx_delta,tx_delta,valid,reason) VALUES(?,?,?,?,?,1,NULL)",
                        (start, now, interface, rx_delta, tx_delta))
                    outcome.update(valid=True, download_bytes=rx_delta, upload_bytes=tx_delta)
                else:
                    conn.execute(
                        "INSERT INTO intervals(start_ts,end_ts,interface,rx_delta,tx_delta,valid,reason) VALUES(?,?,?,NULL,NULL,0,?)",
                        (start, now, interface, reason))
                    outcome["reason"] = reason
            conn.execute("INSERT INTO snapshots(timestamp,interface,rx_bytes,tx_bytes) VALUES(?,?,?,?)",
                         (now, interface, rx_bytes, tx_bytes))
        return outcome

    def sample_interface(self, interface: Optional[str] = None,
                         sys_class_net: str = "/sys/class/net") -> dict:
        selected = interface or detect_default_wan()
        rx, tx = read_interface_counters(selected, sys_class_net)
        return self.record_sample(selected, rx, tx)

    def reset_baseline(self) -> None:
        """Deliberately clear local snapshots and interval history."""
        with self._connect() as conn:
            conn.execute("DELETE FROM intervals")
            conn.execute("DELETE FROM snapshots")

    def report(self, start: datetime, end: datetime, label: str) -> TrafficReport:
        """Aggregate deltas overlapping [start,end), prorating interval boundaries."""
        if start.tzinfo is None or end.tzinfo is None or end <= start:
            raise ValueError("start and end must be timezone-aware and end must follow start")
        start_ts, end_ts = start.timestamp(), end.timestamp()
        warnings = []
        download = upload = 0
        interfaces = set()
        covered = []
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT start_ts,end_ts,interface,rx_delta,tx_delta,valid,reason
                   FROM intervals WHERE end_ts > ? AND start_ts < ? ORDER BY start_ts""",
                (start_ts, end_ts)).fetchall()
        for row in rows:
            left = max(start_ts, float(row["start_ts"]))
            right = min(end_ts, float(row["end_ts"]))
            if right <= left:
                continue
            if not row["valid"]:
                warnings.append(str(row["reason"] or "invalid_interval"))
                continue
            duration = float(row["end_ts"]) - float(row["start_ts"])
            if duration <= 0:
                warnings.append("invalid_interval_duration")
                continue
            fraction = (right - left) / duration
            download += int(round(int(row["rx_delta"]) * fraction))
            upload += int(round(int(row["tx_delta"]) * fraction))
            interfaces.add(str(row["interface"]))
            covered.append((left, right))
        cursor = start_ts
        for left, right in sorted(covered):
            if left > cursor + 1:
                warnings.append("missing_history_or_sampling_gap")
            cursor = max(cursor, right)
        if cursor < end_ts - 1:
            warnings.append("missing_history_or_sampling_gap")
        if len(interfaces) > 1:
            warnings.append("multiple_interfaces")
        unique_warnings = tuple(sorted(set(warnings)))
        return TrafficReport(label, start.isoformat(), end.isoformat(),
            ", ".join(sorted(interfaces)) if interfaces else "unknown",
            download, upload, not unique_warnings, unique_warnings)

    def daily_report(self, day: Optional[date] = None) -> TrafficReport:
        target = day or (datetime.now(self.tz).date() - timedelta(days=1))
        start = datetime.combine(target, datetime_time.min, self.tz)
        return self.report(start, start + timedelta(days=1), "Daily usage — %s" % target.isoformat())

    def monthly_report(self, year: Optional[int] = None, month: Optional[int] = None) -> TrafficReport:
        now = datetime.now(self.tz)
        if year is None or month is None:
            previous = now.replace(day=1) - timedelta(days=1)
            year, month = previous.year, previous.month
        start = datetime(year, month, 1, tzinfo=self.tz)
        end = datetime(year + (month == 12), 1 if month == 12 else month + 1, 1, tzinfo=self.tz)
        return self.report(start, end, "Monthly usage — %04d-%02d" % (year, month))

    def month_to_date_report(self, now: Optional[datetime] = None) -> TrafficReport:
        current = now or datetime.now(self.tz)
        if current.tzinfo is None:
            raise ValueError("now must be timezone-aware")
        current = current.astimezone(self.tz)
        start = current.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        return self.report(start, current, "Month to date — %04d-%02d" % (start.year, start.month))

def format_bytes(value: int) -> str:
    amount = float(value)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if amount < 1024 or unit == "TiB":
            return "%.2f %s" % (amount, unit)
        amount /= 1024
    return "%.2f TiB" % amount

def format_report(report: TrafficReport) -> str:
    status = "Complete for observed intervals" if report.complete else "INCOMPLETE / ESTIMATED"
    lines = [
        "🌐 %s" % report.period,
        "WAN interface: %s" % report.interface,
        "Download: %s" % format_bytes(report.download_bytes),
        "Upload: %s" % format_bytes(report.upload_bytes),
        "Combined: %s" % format_bytes(report.total_bytes),
        "Data quality: %s" % status,
    ]
    if report.warnings:
        lines.append("Notes: %s" % ", ".join(report.warnings))
    lines.append("Router interface counters; may differ from ISP billing totals.")
    return "\\n".join(lines)

def main() -> None:
    parser = argparse.ArgumentParser(description="Local WAN traffic accounting")
    parser.add_argument("--db", default=os.environ.get("TRAFFIC_DB", DEFAULT_DB))
    parser.add_argument("--timezone", default=os.environ.get("TIMEZONE", "Asia/Dhaka"))
    parser.add_argument("--interface", default=os.environ.get("WAN_INTERFACE"))
    parser.add_argument("--sample", action="store_true")
    parser.add_argument("--daily", action="store_true")
    parser.add_argument("--monthly", action="store_true")
    parser.add_argument("--mtd", action="store_true")
    parser.add_argument("--reset-baseline", action="store_true")
    args = parser.parse_args()
    accounting = TrafficAccounting(args.db, args.timezone)
    if args.reset_baseline:
        accounting.reset_baseline()
        print("Traffic history cleared; next sample establishes a new baseline.")
    if args.sample:
        print(accounting.sample_interface(args.interface))
    if args.daily:
        print(format_report(accounting.daily_report()))
    if args.monthly:
        print(format_report(accounting.monthly_report()))
    if args.mtd:
        print(format_report(accounting.month_to_date_report()))
    if not any((args.sample, args.daily, args.monthly, args.mtd, args.reset_baseline)):
        parser.print_help()

if __name__ == "__main__":
    main()
