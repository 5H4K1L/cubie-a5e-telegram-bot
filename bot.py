"""Cubie A5E Telegram bot entry point."""
from __future__ import annotations
import asyncio
import logging
from datetime import time as wall_time
from pathlib import Path
from zoneinfo import ZoneInfo
from telegram.ext import Application, ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
from dotenv import load_dotenv
from config import Config
from modules import router
from modules.handlers import (
    start, help_command, status, cpu, memory_command, storage_command, temp_command,
    uptime_command, network_command, clients_command, system_command, traffic_command,
    traffic_today, traffic_month, traffic_mtd, ai_command, reboot_command, traffic_reset_command, confirmation_callback,
)
from modules.traffic.accounting import TrafficAccounting, format_report
from modules.notifications import AlertMonitor

LOG = logging.getLogger("cubie_bot")

def parse_hhmm(value: str) -> wall_time:
    hour, minute = (int(x) for x in value.split(":", 1))
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError(f"Invalid time: {value}")
    return wall_time(hour, minute)

async def safe_send(context, message: str):
    application = context if isinstance(context, Application) else context.application
    cfg = application.bot_data["config"]
    try:
        await application.bot.send_message(chat_id=cfg.owner_id, text=message[:3900])
    except Exception:
        LOG.exception("Could not send scheduled notification")

async def sample_traffic(context: ContextTypes.DEFAULT_TYPE):
    cfg = context.application.bot_data["config"]
    try:
        await asyncio.to_thread(TrafficAccounting(cfg.database_path, cfg.timezone).sample_interface, cfg.wan_interface)
    except Exception:
        LOG.exception("Scheduled WAN sample failed")

async def alert_check(context: ContextTypes.DEFAULT_TYPE):
    monitor = context.application.bot_data["alert_monitor"]
    for message in monitor.check():
        await safe_send(context, "⚠️ Router alert\n" + message)

async def advanced_alert_check(context: ContextTypes.DEFAULT_TYPE):\n    monitor = context.application.bot_data["advanced_monitor"]\n    for message in monitor.check():\n        await safe_send(context, "🔔 Network/VPN event\\n" + message)\n\nasync def daily_usage(context: ContextTypes.DEFAULT_TYPE):
    cfg = context.application.bot_data["config"]
    report = await asyncio.to_thread(TrafficAccounting(cfg.database_path, cfg.timezone).daily_report)
    await safe_send(context, format_report(report))

async def monthly_usage(context: ContextTypes.DEFAULT_TYPE):
    cfg = context.application.bot_data["config"]
    report = await asyncio.to_thread(TrafficAccounting(cfg.database_path, cfg.timezone).monthly_report)
    await safe_send(context, format_report(report))

async def ai_report(context: ContextTypes.DEFAULT_TYPE, period: str):
    assistant = context.application.bot_data.get("ai")
    if assistant is None:
        return
    try:
        report = await asyncio.to_thread(assistant.report, period)
        await safe_send(context, f"🤖 Gemini {period} router report\n\n{report}")
    except Exception:
        LOG.exception("Scheduled Gemini report failed")
        await safe_send(context, f"Gemini {period} report unavailable; normal router monitoring is unaffected.")

async def ai_daily(context: ContextTypes.DEFAULT_TYPE):
    await ai_report(context, "daily")

async def ai_weekly(context: ContextTypes.DEFAULT_TYPE):
    await ai_report(context, "weekly")

async def ai_monthly(context: ContextTypes.DEFAULT_TYPE):
    await ai_report(context, "monthly")

async def post_init(application: Application):
    cfg = application.bot_data["config"]
    tz = ZoneInfo(cfg.timezone)
    jobs = application.job_queue
    if jobs is None:
        raise RuntimeError("Install python-telegram-bot[job-queue] to enable scheduled reports")
    jobs.run_repeating(sample_traffic, interval=cfg.sample_interval, first=5, name="wan-sampling")
    jobs.run_repeating(alert_check, interval=cfg.alert_interval, first=30, name="alert-monitor")\n    jobs.run_repeating(advanced_alert_check, interval=cfg.alert_interval, first=45, name="advanced-alert-monitor")
    jobs.run_daily(daily_usage, time=parse_hhmm(cfg.daily_report_time).replace(tzinfo=tz), name="daily-traffic-report")
    jobs.run_monthly(monthly_usage, when=parse_hhmm(cfg.monthly_report_time).replace(tzinfo=tz), day=1, name="monthly-traffic-report")
    if application.bot_data.get("ai") is not None:
        jobs.run_daily(ai_daily, time=parse_hhmm(cfg.ai_daily_time).replace(tzinfo=tz), name="ai-daily")
        jobs.run_daily(ai_weekly, time=parse_hhmm(cfg.ai_weekly_time).replace(tzinfo=tz), name="ai-weekly", days=(cfg.ai_weekly_day,))
        jobs.run_monthly(ai_monthly, when=parse_hhmm(cfg.ai_monthly_time).replace(tzinfo=tz), day=cfg.ai_monthly_day, name="ai-monthly")
    LOG.info("Bot initialized; scheduled jobs registered")
    await safe_send(application, "✅ Cubie A5E Router Bot started. WAN sampling and monitoring are active.")

def build_ai(cfg: Config):
    if not cfg.ai_enabled:
        return None
    if not cfg.gemini_api_key:
        LOG.warning("AI_ENABLED is true but GEMINI_API_KEY is missing; AI disabled")
        return None
    try:
        from modules.ai.gemini_client import GeminiClient
        from modules.ai.ai_assistant import AIAssistant
        return AIAssistant(GeminiClient(cfg.gemini_api_key, cfg.gemini_model))
    except Exception:
        LOG.exception("Could not initialize Gemini; continuing without AI")
        return None

def main():
    # procd may start the process with / as its working directory.
    # Resolve .env relative to this source file so the service always loads it.
    load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env")
    cfg = Config.load()
    logging.basicConfig(level=getattr(logging, cfg.log_level, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    application = (ApplicationBuilder().token(cfg.telegram_token).post_init(post_init).build())
    application.bot_data["config"] = cfg
    application.bot_data["ai"] = build_ai(cfg)
    application.bot_data["alert_monitor"] = AlertMonitor(
        cfg.temperature_alert_c, cfg.memory_alert_percent, cfg.disk_alert_percent)
    handlers = [
        ("start", start), ("help", help_command), ("status", status), ("cpu", cpu),
        ("memory", memory_command), ("storage", storage_command), ("temp", temp_command),
        ("uptime", uptime_command), ("network", network_command), ("clients", clients_command),
        ("system", system_command), ("traffic", traffic_command), ("traffic_today", traffic_today),
        ("traffic_month", traffic_month), ("traffic_mtd", traffic_mtd), ("ai", ai_command),
        ("reboot", reboot_command), ("traffic_reset", traffic_reset_command),\n        ("dashboard", dashboard_command), ("vpn", vpn_command), ("control", control_command), ("analytics", analytics_command),
    ]
    for command, callback in handlers:
        application.add_handler(CommandHandler(command, callback))
    application.add_handler(CallbackQueryHandler(confirmation_callback, pattern=r"^admin:(reboot|traffic-reset):"))\n    application.add_handler(CallbackQueryHandler(advanced_callback, pattern=r"^(dash:|svc:)"))
    application.run_polling(allowed_updates=["message", "callback_query"])

if __name__ == "__main__":
    main()
