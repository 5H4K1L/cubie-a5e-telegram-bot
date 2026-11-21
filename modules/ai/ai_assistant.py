"""Read-only AI analysis of aggregate router metrics."""
from __future__ import annotations
from modules.router import snapshot

SYSTEM_PROMPT = (
    "You are a cautious network operations assistant. Analyze only the supplied aggregate "
    "router metrics. Do not claim to have changed anything. Never ask for passwords, keys, "
    "tokens, Wi-Fi credentials, full configurations, or client identities. Give concise, "
    "practical, read-only observations. State uncertainty and avoid unsupported diagnoses."
)

def sanitized_telemetry() -> dict:
    data = snapshot()
    mem, disk = data["memory"], data["storage"]
    return {
        "hostname": data["system"]["hostname"],
        "kernel": data["system"]["kernel"],
        "architecture": data["system"]["architecture"],
        "wan_interface": data["system"]["wan"],
        "uptime_seconds": round(data["uptime_seconds"]),
        "load_average": list(data["load_average"]),
        "memory": {"total_bytes": mem["total"], "used_bytes": mem["used"], "used_percent": round(mem["percent"], 1)},
        "root_storage": {"total_bytes": disk["total"], "used_bytes": disk["used"], "used_percent": round(disk["percent"], 1)},
        "temperature_c": data["temperature_c"],
        "interface_count": len(data["interfaces"]),
        "connected_dhcp_lease_count": len(data["clients"]),
    }

class AIAssistant:
    def __init__(self, client):
        self.client = client

    def report(self, period: str) -> str:
        telemetry = sanitized_telemetry()
        return self.client.generate(
            SYSTEM_PROMPT + f"\nPrepare an English {period} router health report. Include observations, "
            "possible risks, and read-only recommendations. Do not invent historical metrics.",
            telemetry,
        )
