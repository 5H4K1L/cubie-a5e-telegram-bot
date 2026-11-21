"""Telegram command handlers. Every command is restricted to the configured owner."""
from __future__ import annotations
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from modules.router import snapshot, human_bytes, human_duration, system_info
from modules.traffic.accounting import TrafficAccounting, format_report

LOG = logging.getLogger(__name__)

def owner_only(func):
    async def wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE):
        owner_id = context.application.bot_data["config"].owner_id
        user = update.effective_user
        if not user or user.id != owner_id:
            if update.effective_message:
                await update.effective_message.reply_text("Unauthorized.")
            return
        return await func(update, context)
    wrapped.__name__ = func.__name__
    return wrapped

def traffic(context):
    cfg = context.application.bot_data["config"]
    return TrafficAccounting(cfg.database_path, cfg.timezone)

async def send(update: Update, text: str):
    if update.effective_message:
        await update.effective_message.reply_text(text, disable_web_page_preview=True)

@owner_only
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send(update, "Cubie A5E Router Bot is online. Use /help to see available commands.")

@owner_only
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send(update, (
        "Cubie A5E Router Bot\n\n"
        "/status — router overview\n/cpu — load averages\n/memory — RAM usage\n"
        "/storage — root filesystem usage\n/temp — temperature sensors\n/uptime — uptime\n"
        "/network — interfaces and WAN\n/clients — DHCP leases\n/system — firmware and board details\n"
        "/traffic — WAN usage overview\n/traffic_today — yesterday's usage\n"
        "/traffic_month — previous month\n/traffic_mtd — current month to date\n"
        "/ai — on-demand read-only AI analysis\n/traffic_reset — clear local usage history (confirmation required)\n/reboot — request router reboot (confirmation required)\n"
    ))

@owner_only
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    d = snapshot()
    m, s = d["memory"], d["storage"]
    temp = "unavailable" if d["temperature_c"] is None else f'{d["temperature_c"]:.1f} °C'
    await send(update, (
        f'🛜 {d["system"]["hostname"]}\n'
        f'WAN: {d["system"]["wan"] or "not detected"}\n'
        f'Uptime: {human_duration(d["uptime_seconds"])}\n'
        f'Load (1/5/15m): {", ".join(f"{x:.2f}" for x in d["load_average"])}\n'
        f'RAM: {human_bytes(m["used"])} / {human_bytes(m["total"])} ({m["percent"]:.1f}%)\n'
        f'Root storage: {human_bytes(s["used"])} / {human_bytes(s["total"])} ({s["percent"]:.1f}%)\n'
        f'Temperature: {temp}\n'
        f'DHCP leases: {len(d["clients"])}'
    ))

@owner_only
async def cpu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    d = snapshot()
    await send(update, "Load averages (1/5/15 min): " + ", ".join(f"{x:.2f}" for x in d["load_average"]))

@owner_only
async def memory_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    m = snapshot()["memory"]
    await send(update, f'RAM: {human_bytes(m["used"])} used / {human_bytes(m["total"])} total\nAvailable: {human_bytes(m["available"])}\nUsage: {m["percent"]:.1f}%')

@owner_only
async def storage_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    s = snapshot()["storage"]
    await send(update, f'Root filesystem: {human_bytes(s["used"])} used / {human_bytes(s["total"])} total\nFree: {human_bytes(s["free"])}\nUsage: {s["percent"]:.1f}%')

@owner_only
async def temp_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    temp = snapshot()["temperature_c"]
    await send(update, "Temperature: unavailable" if temp is None else f"Highest thermal-zone reading: {temp:.1f} °C")

@owner_only
async def uptime_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send(update, "Uptime: " + human_duration(snapshot()["uptime_seconds"]))

@owner_only
async def network_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    d = snapshot()
    lines = [f'Default WAN: {d["system"]["wan"] or "not detected"}']
    for item in d["interfaces"]:
        lines.append(f'{item["name"]}: {item["state"]} | RX {human_bytes(item.get("rx_bytes", 0))} | TX {human_bytes(item.get("tx_bytes", 0))}')
    await send(update, "\n".join(lines))

@owner_only
async def clients_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clients = snapshot()["clients"]
    if not clients:
        await send(update, "No DHCP leases found. Static-IP clients and some Wi-Fi clients may not appear.")
        return
    lines = [f'DHCP leases: {len(clients)}']
    for item in clients[:60]:
        lines.append(f'{item["hostname"]} — {item["ip"]} — {item["mac"]}')
    if len(clients) > 60:
        lines.append(f"...and {len(clients)-60} more")
    await send(update, "\n".join(lines))

@owner_only
async def system_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    d = system_info()
    await send(update, f'Hostname: {d["hostname"]}\nKernel: {d["kernel"]}\nArchitecture: {d["architecture"]}\nWAN: {d["wan"] or "unknown"}\n\n{d["release"][:1000]}')

@owner_only
async def traffic_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cfg = context.application.bot_data["config"]
    a = traffic(context)
    try:
        result = a.sample_interface(cfg.wan_interface)
        await send(update, f"Current WAN sample recorded ({result.get('reason') or ('baseline' if result.get('baseline') else 'OK')}).\n\n" + format_report(a.month_to_date_report()))
    except Exception as exc:
        LOG.exception("Traffic sampling failed")
        await send(update, f"Traffic sampling error: {exc}")

@owner_only
async def traffic_today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send(update, format_report(traffic(context).daily_report()))

@owner_only
async def traffic_month(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send(update, format_report(traffic(context).monthly_report()))

@owner_only
async def traffic_mtd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send(update, format_report(traffic(context).month_to_date_report()))

@owner_only
async def ai_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    assistant = context.application.bot_data.get("ai")
    if assistant is None:
        await send(update, "AI is disabled or not configured. Normal bot functions remain available.")
        return
    await send(update, "Generating a read-only router health analysis…")
    try:
        report = await asyncio_to_thread(assistant.report, "on-demand")
        await send(update, report[:3900])
    except Exception:
        LOG.exception("On-demand Gemini analysis failed")
        await send(update, "Gemini analysis is temporarily unavailable. Router monitoring remains active.")

def asyncio_to_thread(func, *args):
    import asyncio
    return asyncio.to_thread(func, *args)

@owner_only
async def traffic_reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("Confirm reset", callback_data="admin:traffic-reset:confirm"),
        InlineKeyboardButton("Cancel", callback_data="admin:traffic-reset:cancel"),
    ]])
    await update.effective_message.reply_text(
        "Delete all locally collected WAN usage history? This cannot be undone. "
        "Reports will be incomplete until enough new samples are collected.",
        reply_markup=keyboard,
    )

@owner_only
async def reboot_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("Confirm reboot", callback_data="admin:reboot:confirm"),
        InlineKeyboardButton("Cancel", callback_data="admin:reboot:cancel"),
    ]])
    await update.effective_message.reply_text("Reboot the router now? Internet connectivity will be interrupted.", reply_markup=keyboard)

async def confirmation_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not query.from_user or query.from_user.id != context.application.bot_data["config"].owner_id:
        await query.edit_message_text("Unauthorized.")
        return
    if query.data == "admin:traffic-reset:cancel":
        await query.edit_message_text("Traffic history reset cancelled.")
        return
    if query.data == "admin:traffic-reset:confirm":
        traffic(context).reset_baseline()
        await query.edit_message_text("Local WAN traffic history cleared. The next sample establishes a new baseline.")
        return
    if query.data == "admin:reboot:cancel":
        await query.edit_message_text("Reboot cancelled.")
        return
    if query.data == "admin:reboot:confirm":
        await query.edit_message_text("Reboot requested. The router may become temporarily unreachable.")
        import subprocess
        try:
            subprocess.Popen(["/sbin/reboot"], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, close_fds=True)
        except OSError:
            LOG.exception("Could not invoke reboot")
            await context.bot.send_message(chat_id=query.from_user.id, text="Could not execute /sbin/reboot. Check router permissions.")
