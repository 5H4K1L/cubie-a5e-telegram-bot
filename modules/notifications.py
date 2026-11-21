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
