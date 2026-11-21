"""Threshold-based notifications; all checks are read-only."""
from __future__ import annotations
from modules.router import snapshot

class AlertMonitor:
    def __init__(self, temperature_c: float, memory_percent: float, disk_percent: float):
        self.thresholds = {"temperature_c": temperature_c, "memory_percent": memory_percent,
                           "disk_percent": disk_percent}
        self.last_alert: dict[str, float] = {}

    def check(self, cooldown_seconds: int = 1800) -> list[str]:
        data = snapshot()
        candidates = []
        if not data["system"]["wan"]:
            candidates.append(("wan", "No IPv4 default WAN route detected"))
        temp = data["temperature_c"]
        if temp is not None and temp >= self.thresholds["temperature_c"]:
            candidates.append(("temperature", f"High router temperature: {temp:.1f} °C"))
        mem = data["memory"]["percent"]
        if mem >= self.thresholds["memory_percent"]:
            candidates.append(("memory", f"High memory usage: {mem:.1f}%"))
        disk = data["storage"]["percent"]
        if disk >= self.thresholds["disk_percent"]:
            candidates.append(("disk", f"High root filesystem usage: {disk:.1f}%"))
        import time
        now = time.time()
        messages = []
        for key, message in candidates:
            if now - self.last_alert.get(key, 0) >= cooldown_seconds:
                self.last_alert[key] = now
                messages.append(message)
        return messages

class AdvancedEventMonitor:
    """Detect WAN route transitions and DHCP lease arrivals/departures."""
    def __init__(self):
        self._wan = None
        self._clients = None
        self._vpn = None

    def check(self) -> list[str]:
        from modules.router import snapshot
        from modules.advanced import vpn_status
        data = snapshot()
        messages = []
        wan = data["system"].get("wan")
        clients = {(c.get("mac", "").lower(), c.get("ip", "")): c.get("hostname", "unknown")
                   for c in data.get("clients", [])}
        if self._wan is not None and wan != self._wan:
            messages.append("WAN route restored on " + wan if wan else "WAN default route lost")
        self._wan = wan
        if self._clients is not None:
            added, removed = set(clients) - self._clients, self._clients - set(clients)
            for mac, ip in sorted(added)[:10]:
                messages.append(f"DHCP client connected: {clients[(mac, ip)]} ({ip}, {mac})")
            for mac, ip in sorted(removed)[:10]:
                messages.append(f"DHCP lease disappeared: {ip} ({mac})")
            if len(added) > 10: messages.append(f"{len(added)-10} additional DHCP leases added")
            if len(removed) > 10: messages.append(f"{len(removed)-10} additional DHCP leases removed")
        self._clients = set(clients)
        vpn = tuple(vpn_status())
        if self._vpn is not None and vpn != self._vpn:
            messages.append("VPN state changed: " + "; ".join(vpn))
        self._vpn = vpn
        return messages
