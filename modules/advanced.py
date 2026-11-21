"""Lightweight advanced telemetry and allow-listed service controls."""
from __future__ import annotations
import subprocess
from pathlib import Path
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from modules.router import snapshot, human_bytes, human_duration

# Only these fixed init scripts can be restarted from Telegram.
RESTARTABLE_SERVICES = {
    "dnsmasq": "DNS/DHCP (dnsmasq)",
    "firewall": "Firewall",
    "network": "Network (may interrupt bot connectivity)",
    "wireguard": "WireGuard",
    "openvpn": "OpenVPN",
}

def _run(argv: list[str], timeout: int = 5) -> str:
    try:
        return subprocess.check_output(argv, text=True, stderr=subprocess.STDOUT, timeout=timeout).strip()
    except (OSError, subprocess.SubprocessError):
        return ""

def vpn_status() -> list[str]:
    """Report tunnel presence only; never expose private keys or peer endpoints."""
    lines = []
    wg = _run(["wg", "show", "interfaces"])
    if wg:
        import time
        for interface in wg.split():
            state = _run(["wg", "show", interface, "latest-handshakes"])
            recent = False
            for row in state.splitlines():
                parts = row.split()
                if len(parts) >= 2 and parts[-1].isdigit() and int(parts[-1]) > 0:
                    recent = recent or time.time() - int(parts[-1]) <= 180
            lines.append(f"WireGuard {interface}: active; recent peer handshake: {'yes' if recent else 'not seen (last 3 min)'}")
    else:
        lines.append("WireGuard: no active interfaces detected")
    lines.append("OpenVPN: process running" if _run(["pgrep", "-x", "openvpn"]) else "OpenVPN: no running process detected")
    return lines

def dashboard_text() -> str:
    d = snapshot()
    mem, disk = d["memory"], d["storage"]
    temp = "n/a" if d["temperature_c"] is None else f"{d['temperature_c']:.1f} °C"
    return (f"📊 Cubie A5E live dashboard\nHost: {d['system']['hostname']}\n"
        f"WAN: {d['system']['wan'] or 'no default route'}\nUptime: {human_duration(d['uptime_seconds'])}\n"
        f"CPU load 1/5/15m: {' / '.join(f'{v:.2f}' for v in d['load_average'])}\n"
        f"RAM: {mem['percent']:.1f}% ({human_bytes(mem['used'])}/{human_bytes(mem['total'])})\n"
        f"Root disk: {disk['percent']:.1f}% ({human_bytes(disk['free'])} free)\n"
        f"Temperature: {temp}\nDHCP leases: {len(d['clients'])}")

def dashboard_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Refresh", callback_data="dash:refresh")],
        [InlineKeyboardButton("🔐 VPN status", callback_data="dash:vpn"),
         InlineKeyboardButton("🛠 Router controls", callback_data="dash:control")]])

def control_keyboard() -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(f"Restart {label}", callback_data=f"svc:{key}:ask")]
        for key, label in RESTARTABLE_SERVICES.items()]
    rows.append([InlineKeyboardButton("Cancel", callback_data="dash:refresh")])
    return InlineKeyboardMarkup(rows)

def confirmation_keyboard(service: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("✅ Confirm restart", callback_data=f"svc:{service}:confirm"),
        InlineKeyboardButton("Cancel", callback_data="dash:control")]])

def restart_service(service: str) -> tuple[bool, str]:
    if service not in RESTARTABLE_SERVICES:
        return False, "Service is not on the allow-list."
    init = Path("/etc/init.d") / service
    if not init.is_file():
        return False, f"{service}: init script not installed on this router."
    try:
        result = subprocess.run([str(init), "restart"], text=True, capture_output=True, timeout=25)
        if result.returncode == 0:
            return True, f"{RESTARTABLE_SERVICES[service]} restart command completed."
        detail = (result.stderr or result.stdout or "no details").strip()[-700:]
        return False, f"{service} restart failed (exit {result.returncode}): {detail}"
    except (OSError, subprocess.SubprocessError) as exc:
        return False, f"{service} restart failed: {exc}"
