"""Environment-backed configuration. Never commit real secrets."""
from __future__ import annotations
import os
from dataclasses import dataclass
from pathlib import Path

def _bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    return default if value is None else value.strip().lower() in {"1", "true", "yes", "on"}

@dataclass(frozen=True)
class Config:
    telegram_token: str
    owner_id: int
    timezone: str = "Asia/Dhaka"
    wan_interface: str | None = None
    database_path: str = "/etc/cubie-a5e-telegram-bot/traffic.sqlite3"
    sample_interval: int = 60
    alert_interval: int = 300
    daily_report_time: str = "08:00"
    monthly_report_time: str = "08:05"
    ai_enabled: bool = False
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash"
    ai_daily_time: str = "08:15"
    ai_weekly_day: int = 0
    ai_weekly_time: str = "08:20"
    ai_monthly_day: int = 1
    ai_monthly_time: str = "08:25"
    temperature_alert_c: float = 80.0
    disk_alert_percent: float = 90.0
    memory_alert_percent: float = 90.0
    log_level: str = "INFO"

    @classmethod
    def load(cls) -> "Config":
        token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
        owner = os.getenv("TELEGRAM_OWNER_ID", "").strip()
        if not token:
            raise ValueError("TELEGRAM_BOT_TOKEN is required")
        if not owner.isdigit():
            raise ValueError("TELEGRAM_OWNER_ID must be your numeric Telegram user ID")
        return cls(
            telegram_token=token,
            owner_id=int(owner),
            timezone=os.getenv("TIMEZONE", "Asia/Dhaka"),
            wan_interface=os.getenv("WAN_INTERFACE") or None,
            database_path=os.getenv("TRAFFIC_DB", "/etc/cubie-a5e-telegram-bot/traffic.sqlite3"),
            sample_interval=max(30, int(os.getenv("SAMPLE_INTERVAL", "60"))),
            alert_interval=max(60, int(os.getenv("ALERT_INTERVAL", "300"))),
            daily_report_time=os.getenv("DAILY_REPORT_TIME", "08:00"),
            monthly_report_time=os.getenv("MONTHLY_REPORT_TIME", "08:05"),
            ai_enabled=_bool("AI_ENABLED"),
            gemini_api_key=os.getenv("GEMINI_API_KEY") or None,
            gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
            ai_daily_time=os.getenv("AI_DAILY_TIME", "08:15"),
            ai_weekly_day=int(os.getenv("AI_WEEKLY_DAY", "0")),
            ai_weekly_time=os.getenv("AI_WEEKLY_TIME", "08:20"),
            ai_monthly_day=int(os.getenv("AI_MONTHLY_DAY", "1")),
            ai_monthly_time=os.getenv("AI_MONTHLY_TIME", "08:25"),
            temperature_alert_c=float(os.getenv("TEMPERATURE_ALERT_C", "80")),
            disk_alert_percent=float(os.getenv("DISK_ALERT_PERCENT", "90")),
            memory_alert_percent=float(os.getenv("MEMORY_ALERT_PERCENT", "90")),
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        )
