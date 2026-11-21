# WAN traffic accounting

The traffic module reads Linux interface byte counters from `/sys/class/net/<interface>/statistics/` and stores timestamped snapshots and deltas in SQLite.

- WAN RX bytes are download; WAN TX bytes are upload.
- Set `WAN_INTERFACE` to the actual WAN device. If unset, the IPv4 default-route interface is detected with `ip`.
- Database default: `/etc/cubie-a5e-telegram-bot/traffic.sqlite3`.
- Timezone default: `Asia/Dhaka`.
- Sample regularly (recommended: every 60 seconds). The default maximum accepted interval is 300 seconds.
- Counter decreases, interface changes, non-monotonic timestamps, and long gaps are marked invalid and make affected reports incomplete.
- Sample intervals crossing a calendar boundary are prorated. This assumes traffic was approximately uniform during that short interval.
- History begins at the first baseline sample. Pre-installation traffic cannot be reconstructed.
- These are router interface counters, not ISP billing totals.

## Local smoke test

Use Python 3.9+ and run:

```sh
python3 -m unittest discover -s tests -v
python3 -m modules.traffic.accounting --sample
python3 -m modules.traffic.accounting --daily
python3 -m modules.traffic.accounting --monthly
python3 -m modules.traffic.accounting --mtd
```

Set an explicit interface if needed:

```sh
WAN_INTERFACE=pppoe-wan python3 -m modules.traffic.accounting --sample
```

Find the actual interface with `ip -4 route show default`; names vary by configuration.

## Scheduler integration

The bot scheduler should call `TrafficAccounting.sample_interface()` regularly, then call `daily_report()` and `monthly_report()` at configured local report times. Usage totals must be delivered even when Gemini is disabled or unavailable. `format_report(report)` creates a Telegram-friendly factual report.

Keep the SQLite database local and back it up before upgrades. `reset_baseline()` deletes all local traffic history; any future Telegram command exposing it must be owner-only and require explicit confirmation.
