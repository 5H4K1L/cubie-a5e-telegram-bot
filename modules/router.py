"""Read-only router telemetry for OpenWrt and ImmortalWrt."""
from __future__ import annotations
import os
import re
import shutil
import subprocess
import time
from pathlib import Path

def _read(path: str, default: str = "") -> str:
    try:
        return Path(path).read_text(errors="replace").strip()
    except OSError:
        return default

def _run(argv: list[str], timeout: int = 4) -> str:
    try:
        return subprocess.check_output(argv, text=True, stderr=subprocess.DEVNULL, timeout=timeout).strip()
    except (OSError, subprocess.SubprocessError):
        return ""

def temperature_c() -> float | None:
    values = []
    for path in Path("/sys/class/thermal").glob("thermal_zone*/temp"):
        try:
            raw = int(path.read_text().strip())
            value = raw / 1000 if raw > 1000 else float(raw)
            if -20 < value < 150:
                values.append(value)
        except (OSError, ValueError):
            continue
    return max(values) if values else None

def memory() -> dict:
    info = {}
    for line in _read("/proc/meminfo").splitlines():
        match = re.match(r"(\w+):\s+(\d+)", line)
        if match:
            info[match.group(1)] = int(match.group(2)) * 1024
    total = info.get("MemTotal", 0)
    available = info.get("MemAvailable", info.get("MemFree", 0) + info.get("Buffers", 0) + info.get("Cached", 0))
    used = max(0, total - available)
    return {"total": total, "used": used, "available": available,
            "percent": (used / total * 100) if total else 0.0}

def storage() -> dict:
    usage = shutil.disk_usage("/")
    return {"total": usage.total, "used": usage.used, "free": usage.free,
            "percent": usage.used / usage.total * 100 if usage.total else 0.0}

def uptime_seconds() -> float:
    try:
        return float(_read("/proc/uptime").split()[0])
    except (ValueError, IndexError):
        return 0.0

def default_wan() -> str | None:
    route = _run(["ip", "-4", "route", "show", "default"])
    match = re.search(r"(?:^|\s)dev\s+([^\s]+)", route)
    return match.group(1) if match else None

def interface_counters(interface: str) -> dict | None:
    if not re.fullmatch(r"[A-Za-z0-9_.:-]{1,64}", interface):
        return None
    base = Path("/sys/class/net") / interface / "statistics"
    try:
        return {"rx_bytes": int((base / "rx_bytes").read_text()),
                "tx_bytes": int((base / "tx_bytes").read_text())}
    except (OSError, ValueError):
        return None

def interfaces() -> list[dict]:
    result = []
    for path in Path("/sys/class/net").iterdir():
        name = path.name
        counters = interface_counters(name) or {}
        try:
            state = (path / "operstate").read_text().strip()
        except OSError:
            state = "unknown"
        result.append({"name": name, "state": state, **counters})
    return result

def connected_clients() -> list[dict]:
    """Return DHCP lease entries only; this is not a complete Wi-Fi client inventory."""
    clients = []
    for line in _read("/tmp/dhcp.leases").splitlines():
        parts = line.split()
        if len(parts) >= 4:
            expiry, mac, ip, hostname = parts[:4]
            clients.append({"ip": ip, "mac": mac, "hostname": hostname if hostname != "*" else "unknown"})
    return clients

def system_info() -> dict:
    release = _read("/etc/openwrt_release") or _read("/etc/os-release")
    board = _run(["ubus", "call", "system", "board"])
    return {
        "hostname": _read("/proc/sys/kernel/hostname", "router"),
        "kernel": _run(["uname", "-r"]),
        "architecture": _run(["uname", "-m"]),
        "release": release[:1600],
        "board": board[:1600],
        "wan": default_wan(),
    }

def snapshot() -> dict:
    return {
        "system": system_info(),
        "uptime_seconds": uptime_seconds(),
        "load_average": os.getloadavg() if hasattr(os, "getloadavg") else (0, 0, 0),
        "memory": memory(),
        "storage": storage(),
        "temperature_c": temperature_c(),
        "interfaces": interfaces(),
        "clients": connected_clients(),
        "captured_at": time.time(),
    }

def human_bytes(value: int) -> str:
    amount = float(value)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if amount < 1024 or unit == "TiB":
            return f"{amount:.2f} {unit}"
        amount /= 1024
    return f"{amount:.2f} TiB"

def human_duration(seconds: float) -> str:
    seconds = max(0, int(seconds))
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, _ = divmod(rem, 60)
    return f"{days}d {hours}h {minutes}m"
